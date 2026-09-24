#!/usr/bin/env python3
"""Run configuration lemmas and implementation mutations locally without credentials."""
import argparse
from datetime import datetime, timezone
import gzip
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

repo = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("checker", Path(__file__).with_name("check-delay-configuration.py"))
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--solc", type=Path, required=True)
    parser.add_argument("--solver", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    tools = {}
    for name, executable in [("forge", shutil.which("forge")), ("halmos", shutil.which("halmos")), ("solc", args.solc), ("solver", args.solver)]:
        path = Path(executable).resolve()
        tools[name] = {"path": str(path), "sha256": checker.sha(path),
                       "version": subprocess.check_output([str(path), "--version"], text=True).strip()}
    receipt = {"startedAt": datetime.now(timezone.utc).isoformat(), "tools": tools, "runs": {},
               "semanticClosureCertified": False, "repositoryInputs": {name: checker.sha(repo / name) for name in
                [checker.SOURCE, "certora/lemmas/check-delay-configuration.py", "certora/lemmas/run-delay-configuration.py"]}}
    env = {key: value for key, value in os.environ.items() if key in {
        "PATH", "HOME", "TMPDIR", "LANG", "LC_ALL", "USER", "LOGNAME", "SHELL", "TERM"
    }}
    for name in ["original", *checker.MUTATIONS]:
        evidence = output / name
        evidence.mkdir()
        with tempfile.TemporaryDirectory(prefix="term-delay-lemma-") as temporary:
            work = Path(temporary)
            for path in [checker.SOURCE, "contracts/Permissions.sol"]:
                target = work / path
                target.parent.mkdir(parents=True, exist_ok=True)
                content = (repo / path).read_text()
                if name != "original" and path == "contracts/Permissions.sol":
                    content = checker.mutation(content, name)
                target.write_text(content)
            (work / "node_modules").symlink_to((repo / "node_modules").resolve(), target_is_directory=True)
            config = '[profile.default]\nsrc = "certora/lemmas"\ntest = "certora/lemmas"\nsolc = ' + json.dumps(tools["solc"]["path"]) + '\nevm_version = "paris"\noptimizer = true\noptimizer_runs = 1\ndynamic_test_linking = false\nremappings = ["@gnosis.pm/=node_modules/@gnosis.pm/", "@openzeppelin/=node_modules/@openzeppelin/"]\n'
            (work / "foundry.toml").write_text(config)
            (evidence / "foundry.toml").write_text(config)
            with (evidence / "build.log").open("w") as log:
                subprocess.run([tools["forge"]["path"], "build", "--build-info", "--extra-output", "storageLayout"], cwd=work, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
            builds = list((work / "out/build-info").glob("*.json"))
            assert len(builds) == 1
            (evidence / "compiler.json.gz").write_bytes(gzip.compress(builds[0].read_bytes(), mtime=0))
            command = [tools["halmos"]["path"], "--root", str(work), "--contract", "DelayConfigurationLemma",
                       "--storage-layout", "generic", "--solver-command", tools["solver"]["path"],
                       "--solver-timeout-assertion", "120s", "--solver-timeout-branching", "100ms", "--loop", "16",
                       "--json-output", str(evidence / "result.json"), "--dump-smt-queries", "--dump-smt-directory", str(evidence / "smt"), "--statistics", "--no-status"]
            with (evidence / "halmos.log").open("w") as log:
                result = subprocess.run(command, cwd=work, env=env, stdout=log, stderr=subprocess.STDOUT)
            receipt["runs"][name] = {"command": command, "exitCode": result.returncode}
            print(name + ": " + str(result.returncode), flush=True)
    receipt["completedAt"] = datetime.now(timezone.utc).isoformat()
    receipt["artifacts"] = {p.relative_to(output).as_posix(): checker.sha(p) for p in sorted(output.rglob("*")) if p.is_file()}
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    assessment = checker.assess(output, repo)
    (output / "assessment.json").write_text(json.dumps(assessment, indent=2) + "\n")
    print(json.dumps(assessment, indent=2))
    return 0 if assessment["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
