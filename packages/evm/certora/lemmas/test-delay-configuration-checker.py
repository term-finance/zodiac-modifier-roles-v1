#!/usr/bin/env python3
"""Exercise fail-closed evidence handling using damaged real proof artifacts."""
from copy import deepcopy
import gzip
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile

spec = importlib.util.spec_from_file_location("checker", Path(__file__).with_name("check-delay-configuration.py"))
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)
repo = Path(__file__).resolve().parents[2]
evidence = repo / "certora/assurance/evidence/delay-configuration-2026-09-24"
assert checker.assess(evidence, repo)["accepted"]
original = json.loads((evidence / "original/result.json").read_text())


def rows(data):
    return data["test_results"][checker.CONTRACT]


mutations = [
    lambda data: rows(data).pop(),
    lambda data: rows(data).append(deepcopy(rows(data)[0])),
    lambda data: rows(data)[0].update(exitcode=2),
    lambda data: rows(data)[0].update(exitcode=True),
    lambda data: rows(data)[0].update(num_bounded_loops=1),
    lambda data: rows(data)[0].pop("num_bounded_loops"),
    lambda data: rows(data)[0].update(num_paths=[13, 0, 0]),
    lambda data: rows(data)[0].update(num_paths=[13, 7, 1]),
    lambda data: rows(data)[0].update(models=[{"is_valid": True}], num_models=1),
    lambda data: rows(data)[0].pop("models"),
]
for mutate in mutations:
    damaged = deepcopy(original)
    mutate(damaged)
    assert checker.result_errors(damaged), "damaged result was accepted"
negative = json.loads((evidence / "missing-revocation/result.json").read_text())
for row in rows(negative):
    for model in row["models"]:
        model["is_valid"] = False
assert checker.result_errors(negative, True), "unvalidated mutant counterexample was accepted"

for kind in ["wrong-source", "wrong-compiler", "wrong-fork", "missing-mutant"]:
    with tempfile.TemporaryDirectory(prefix="delay-evidence-negative-") as temporary:
        target = Path(temporary) / "evidence"
        shutil.copytree(evidence, target)
        receipt = json.loads((target / "receipt.json").read_text())
        if kind == "missing-mutant":
            receipt["runs"].pop("missing-revocation")
        else:
            path = target / "original/compiler.json.gz"
            compiler = json.loads(gzip.decompress(path.read_bytes()))
            if kind == "wrong-source":
                compiler["input"]["sources"]["contracts/Permissions.sol"]["content"] += "\n"
            elif kind == "wrong-compiler":
                compiler["solcVersion"] = "0.8.6"
            else:
                compiler["input"]["settings"]["evmVersion"] = "prague"
            path.write_bytes(gzip.compress(json.dumps(compiler).encode(), mtime=0))
            receipt["artifacts"]["original/compiler.json.gz"] = checker.sha(path)
        (target / "receipt.json").write_text(json.dumps(receipt))
        assert not checker.assess(target, repo)["accepted"], kind + " was accepted"
print("15 damaged, incomplete, stale or unvalidated evidence variants rejected.")
