#!/usr/bin/env python3
"""Reject incomplete, misleading or mismatched retained proof records."""
from copy import deepcopy
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("checker", HERE / "check-configured-boundary.py")
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)
REPO = HERE.parents[1]
EVIDENCE = REPO / "certora/assurance/evidence/delay-protection-2026-09-24/configured-boundary"
WITNESS = "certora/lemmas/BoundaryMutationReplay.t.sol:BoundaryFeasibilityWitnesses"


def modify_json(path, mutation, compressed=False):
    value = json.loads(gzip.decompress(path.read_bytes()) if compressed else path.read_text())
    mutation(value)
    raw = (json.dumps(value, indent=2) + "\n").encode()
    path.write_bytes(gzip.compress(raw, mtime=0) if compressed else raw)


def modify_tree(folder, mutation):
    def change(progress):
        tree = json.loads(progress["verificationProgress"])
        mutation(tree)
        progress["verificationProgress"] = json.dumps(tree)
    modify_json(folder / "original/progress.json", change)


def native(folder, mutation):
    modify_json(folder / "native-replay/original/result.json", mutation)


def output(folder, mutation):
    for path in (folder / "original").glob("rule_output_*.gz"):
        data = json.loads(gzip.decompress(path.read_bytes()))
        if data.get("callResolutionWarnings"):
            modify_json(path, mutation, True)
            return
    raise AssertionError("expected a real call-resolution record")


def rehash(folder):
    for group in ["original", *checker.MUTATIONS, "native-replay"]:
        base = folder / group
        files = base.rglob("*") if group == "native-replay" else base.iterdir()
        manifest = {p.relative_to(base).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in files if p.is_file() and p.name != "manifest.json"}
        (base / "manifest.json").write_text(json.dumps({"filesSha256": manifest}))


controls = {
    "unfinished job": lambda p: modify_json(p / "original/progress.json", lambda j: j.update(jobEnded=False)),
    "failed job": lambda p: modify_json(p / "original/progress.json", lambda j: j.update(jobStatus="FAILED")),
    "missing root": lambda p: modify_tree(p, lambda j: j["rules"].pop()),
    "duplicate root": lambda p: modify_tree(p, lambda j: j["rules"].append(deepcopy(j["rules"][0]))),
    "solver error": lambda p: modify_tree(p, lambda j: j["rules"][0].update(status="ERROR")),
    "boolean status": lambda p: modify_tree(p, lambda j: j["rules"][0].update(status=True)),
    "missing sanity": lambda p: modify_tree(p, lambda j: j["rules"][0]["children"].pop()),
    "running sanity": lambda p: modify_tree(p, lambda j: j["rules"][0]["children"][0].update(status="RUNNING")),
    "sanity failure": lambda p: modify_tree(p, lambda j: j["rules"][0]["children"][0].update(status="SANITY_FAILED")),
    "unreviewed main warning": lambda p: modify_tree(p, lambda j: j["rules"][0].update(errors=[{"severity": "warning", "message": "unreviewed model assumption"}])),
    "sanity error": lambda p: modify_tree(p, lambda j: j["rules"][0]["children"][0].update(errors=[{"severity": "error", "message": "solver failed"}])),
    "missing native witness": lambda p: native(p, lambda j: j[WITNESS]["test_results"].pop("test_deniedGrantPremiseIsNecessary()")),
    "failed native witness": lambda p: native(p, lambda j: j[WITNESS]["test_results"]["test_deniedGrantPremiseIsNecessary()"].update(status="Failure")),
    "unreviewed summary": lambda p: output(p, lambda j: j["callResolutionWarnings"][0].update(summary="AUTO havoc")),
    "missing native source": lambda p: modify_json(p / "native-replay/original/compiler.json.gz", lambda j: j["input"]["sources"].pop("certora/lemmas/BoundaryMutationReplay.t.sol"), True),
    "wrong compiler": lambda p: modify_json(p / "native-replay/original/compiler.json.gz", lambda j: j.update(solcVersion="0.8.6"), True),
    "missing mutation output": lambda p: (p / "call-before-revert/progress.json").unlink(),
}

assert checker.assess(EVIDENCE, REPO)["accepted"], "baseline evidence must pass first"
for name, mutate in controls.items():
    with tempfile.TemporaryDirectory(prefix="term-boundary-check-") as temp:
        folder = Path(temp) / "evidence"
        shutil.copytree(EVIDENCE, folder)
        mutate(folder)
        rehash(folder)
        result = checker.assess(folder, REPO)
        assert not result["accepted"], "unsound acceptance: " + name
print(str(len(controls)) + " incomplete, misleading or stale proof variants rejected after rehashing.")
