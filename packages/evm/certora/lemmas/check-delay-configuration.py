#!/usr/bin/env python3
"""Validate the retained configuration lemmas, without issuing a closure certificate."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

SOURCE = "certora/lemmas/DelayConfiguration.t.sol"
CONTRACT = SOURCE + ":DelayConfigurationLemma"
METHODS = {
    "check_configurationClearsDeniedSelector(uint256,uint16,address,bytes4,bytes4,address,bytes4)",
    "check_packedKeyHasExactRepresentation(address,bytes4)",
}
SOURCES = {SOURCE, "contracts/Permissions.sol",
           "node_modules/@gnosis.pm/safe-contracts/contracts/common/Enum.sol"}
MUTATIONS = {
    "missing-revocation": (
        "role.functions[keyForFunctions(targetAddress, functionSig)] = 0;", ""),
    "selector-erased": (
        "return bytes32(abi.encodePacked(targetAddress, functionSig));",
        "return bytes32(abi.encodePacked(targetAddress, bytes4(0)));"),
    "target-wide-clearance": (
        "Clearance.Function,\n            ExecutionOptions.None",
        "Clearance.Target,\n            ExecutionOptions.None"),
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mutation(source, name):
    before, after = MUTATIONS[name]
    if source.count(before) != 1:
        raise ValueError("mutation is not uniquely applicable: " + name)
    return source.replace(before, after, 1)


def result_errors(data, negative=False):
    errors = []
    if type(data.get("exitcode")) is not int or data["exitcode"] != int(negative):
        errors.append("unexpected process result")
    results = data.get("test_results", {})
    if set(results) != {CONTRACT}:
        errors.append("wrong contract universe")
    rows = results.get(CONTRACT, [])
    names = [row.get("name") for row in rows]
    if set(names) != METHODS or len(names) != len(METHODS):
        errors.append("missing, extra or duplicate method instance")
    refuted = False
    for row in rows:
        label = str(row.get("name"))
        paths = row.get("num_paths")
        if not (isinstance(paths, list) and len(paths) == 3 and
                all(type(n) is int and n >= 0 for n in paths) and
                paths[0] > 0 and (negative or paths[1] > 0) and paths[2] == 0):
            errors.append(label + ": vacuous, blocked or unreported paths")
        if type(row.get("num_bounded_loops")) is not int or row["num_bounded_loops"] != 0:
            errors.append(label + ": incomplete loop exploration")
        models = row.get("models")
        if not isinstance(models, list) or type(row.get("num_models")) is not int or row["num_models"] != len(models):
            errors.append(label + ": missing model evidence")
            continue
        status = row.get("exitcode")
        if type(status) is not int or status not in ({0, 1} if negative else {0}):
            errors.append(label + ": assertion error or unresolved solver result")
        elif status == 1:
            valid = any(model.get("is_valid") is True for model in models)
            refuted |= valid
            if not valid:
                errors.append(label + ": no validated assertion counterexample")
        elif models:
            errors.append(label + ": passing instance has counterexamples")
    if negative and not refuted:
        errors.append("mutant was not refuted")
    return errors


def assess(directory, repo):
    errors, groups = [], {}
    receipt = json.loads((directory / "receipt.json").read_text())
    if set(receipt.get("runs", {})) != {"original", *MUTATIONS}:
        errors.append("missing original or mutation run")
    artifacts = receipt.get("artifacts", {})
    actual = {p.relative_to(directory).as_posix() for p in directory.rglob("*")
              if p.is_file() and p.name not in {"receipt.json", "assessment.json"}}
    if set(artifacts) != actual:
        errors.append("artifact manifest is incomplete")
    for name, digest in artifacts.items():
        path = (directory / name).resolve()
        if not path.is_relative_to(directory.resolve()) or not path.is_file() or sha(path) != digest:
            errors.append("artifact changed or unavailable: " + name)
    if receipt.get("semanticClosureCertified") is not False:
        errors.append("these lemmas cannot issue a semantic closure certificate")
    for name in [SOURCE, "certora/lemmas/check-delay-configuration.py", "certora/lemmas/run-delay-configuration.py"]:
        if receipt.get("repositoryInputs", {}).get(name) != sha(repo / name):
            errors.append("proof or checker source changed: " + name)
    expected_tools = {"halmos": "halmos 0.3.3", "solc": "0.8.30+", "solver": "Z3 version 4.12.6", "forge": "forge Version: 1.8.3"}
    for name, version in expected_tools.items():
        tool = receipt.get("tools", {}).get(name, {})
        if version not in tool.get("version", "") or len(tool.get("sha256", "")) != 64:
            errors.append("unbound or unexpected tool: " + name)
    for name in ["original", *MUTATIONS]:
        folder = directory / name
        required = {name + "/" + filename for filename in ["compiler.json.gz", "result.json", "halmos.log", "build.log"]}
        if not required.issubset(artifacts):
            errors.append("missing evidence: " + name)
            continue
        compiler = json.loads(gzip.decompress((folder / "compiler.json.gz").read_bytes()))
        inputs = compiler["input"]
        settings = inputs["settings"]
        if compiler.get("solcVersion") != "0.8.30" or settings.get("optimizer") != {"enabled": True, "runs": 1} or settings.get("evmVersion") != "paris" or settings.get("viaIR") is not False:
            errors.append(name + ": unexpected compilation semantics")
        if set(inputs["sources"]) != SOURCES:
            errors.append(name + ": unexpected compiler source closure")
        for path, source in inputs["sources"].items():
            if path not in SOURCES:
                continue
            expected = (repo / path).read_text()
            if name != "original" and path == "contracts/Permissions.sol":
                expected = mutation(expected, name)
            if source.get("content") != expected:
                errors.append(name + ": source mismatch: " + path)
        methods = compiler["output"]["contracts"][SOURCE]["DelayConfigurationLemma"]["evm"]["methodIdentifiers"]
        if set(methods) != METHODS:
            errors.append(name + ": compiled method universe changed")
        data = json.loads((folder / "result.json").read_text())
        group_errors = result_errors(data, name != "original")
        errors.extend(name + ": " + error for error in group_errors)
        groups[name] = {"accepted": not group_errors, "instances": len(data.get("test_results", {}).get(CONTRACT, []))}
        log = (folder / "halmos.log").read_text().lower()
        if any(marker in log for marker in ["[warn]", "[error]", "traceback", "incomplete loop", "unknown call"]):
            errors.append(name + ": unresolved execution warning")
    return {"accepted": not errors, "groups": groups, "errors": errors,
            "semanticClosureCertified": False,
            "scope": "Library key representation and permission-configuration transition, with arbitrary existing grants and a frame condition. No deployed binding or forwarding theorem."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    assessment = assess(args.evidence.resolve(), Path(__file__).resolve().parents[2])
    print(json.dumps(assessment, indent=2))
    raise SystemExit(0 if assessment["accepted"] else 1)
