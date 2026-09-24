#!/usr/bin/env python3
"""Check retained conditional forwarding results; never issue a closure certificate."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re
import zipfile

SPEC = "certora/specs/delayConfiguredBoundary.spec"
CONF = "certora/confs/Roles-configuredBoundary.conf"
RULES = {"directConfiguredRejection", "safeConfiguredRejection", "returnDataConfiguredRejection"}
GETTERS = {"clearanceOf(uint16,address)", "functionScopeConfigForData(uint16,address,bytes)", "multisend()"}
MUTATIONS = {
    "call-before-revert": "        assembly {\n            pop(call(gas(), to, 0, add(data, 0x20), mload(data), 0, 0))\n            revert(0, 0)\n        }\n",
    "write-before-rejection": "        assembly {\n            sstore(0, 1)\n        }\n",
}


def walk(node, child_key="children"):
    yield node
    for child in node.get(child_key, []):
        yield from walk(child, child_key)


def expected_sanity(spec):
    result, rule = {}, None
    for line, text in enumerate(spec.splitlines(), 1):
        match = re.match(r"rule (\w+)\(", text)
        if match:
            rule = match[1]
            result[rule] = {"rule_not_vacuous"}
        elif rule and text.startswith("    require "):
            result[rule].add("require_not_redundant_" + str(line) + "_4")
        elif rule and text.startswith("    assert "):
            result[rule].add("assertion_not_tautological_" + str(line) + "_4")
    if set(result) != RULES or any(len(names) != 6 for names in result.values()):
        raise ValueError("review the changed rule/premise/assertion universe")
    return result


def check_tree(progress, sanity, negative=False, native_witnesses=False):
    errors = []
    if progress.get("jobEnded") is not True or progress.get("jobStatus") != "SUCCEEDED":
        errors.append("job is not terminal and completed")
    if progress.get("cloudErrorMessages"):
        errors.append("cloud errors are present")
    tree = json.loads(progress.get("verificationProgress", "{}"))
    roots = tree.get("rules", [])
    names = [node.get("name") for node in roots]
    expected = {"directConfiguredRejection"} if negative else RULES
    if set(names) != expected | {"envfreeFuncsStaticCheck"} or len(names) != len(expected) + 1:
        errors.append("missing, extra or duplicate root instance")
    for root in roots:
        name = root.get("name")
        if name == "envfreeFuncsStaticCheck":
            children = root.get("children", [])
            if {n.get("name") for n in children} != GETTERS or len(children) != len(GETTERS):
                errors.append("envfree method universe differs")
        if not negative and name in RULES:
            children = [n for n in root.get("children", []) if n.get("nodeType") == "SANITY"]
            if {n.get("name") for n in children} != sanity[name] or len(children) != len(sanity[name]):
                errors.append(name + ": missing, extra or duplicate sanity instance")
        for node in walk(root):
            running = node.get("isRunning")
            notices = node.get("errors", [])
            reviewed = all(
                (notice.get("severity") == "info" and notice.get("message") == "The rule contains only reverting paths.") or
                (negative and notice.get("severity") == "warning" and re.fullmatch(
                    r"Detected one overflow in counter example 0: delayConfiguredBoundary\.spec:\d+:5 : Unsigned overflow: Sub\(0x4 CANON\d+:bv256\) : \[4, \d+\] -> -\d+ \(width = 256\)",
                    notice.get("message", ""))) or
                (native_witnesses and node.get("nodeType") == "SANITY" and
                 notice.get("severity") == "warning" and re.match(
                     r"Detected (one|\d+) (overflow|overflows|imprecision) in counter example 0[.:]",
                     notice.get("message", "")))
                for notice in notices)
            if not reviewed or (running is not False and running is not None):
                errors.append(str(name) + ": error or unfinished result")
            want = "VIOLATED" if negative and name == "directConfiguredRejection" else "VERIFIED"
            if node.get("status") != want:
                errors.append(str(name) + ": unexpected result " + str(node.get("status")))
    return errors, roots


def read_outputs(folder, roots):
    names = {name for root in roots for node in walk(root) for name in node.get("output", [])}
    if any(not re.fullmatch(r"rule_output_\d+\.json", name) for name in names):
        raise ValueError("unexpected result path")
    return {name: json.loads(gzip.decompress((folder / (name + ".gz")).read_bytes())) for name in names}


def check_sources(folder, repo, mutation=None):
    errors = []
    with zipfile.ZipFile(folder / "submitted-inputs.zip") as archive:
        meta = json.loads(archive.read(".certora_metadata.json"))
        if meta.get("CLI_version") != "8.19.2":
            errors.append("unexpected Certora CLI")
        verify = json.loads(archive.read(".certora_verify.json"))
        if verify.get("primary_contract") != "RolesHarness" or verify.get("specfile") != SPEC or verify.get("importFilesToOrigRelpaths"):
            errors.append("unexpected spec target or imports")
        config = json.loads(archive.read(".certora_sources/certora/confs/Roles-delayProtection.conf"))
        expected_config = json.loads((repo / CONF).read_text())
        if mutation:
            expected_config["rule"] = ["directConfiguredRejection"]
            expected_config["rule_sanity"] = "none"
        config.pop("msg", None)
        expected_config.pop("msg", None)
        if config != expected_config:
            errors.append("submitted proof configuration differs")
        if archive.read(".certora_sources/" + SPEC) != (repo / SPEC).read_bytes():
            errors.append("submitted specification differs")
        build = json.loads(archive.read(".certora_build.json"))
        paths = set()
        primaries = set()
        for scene in build.values():
            primaries.add(scene["primary_contract"])
            for path in scene["srclist"].values():
                if path.endswith(".sol") and not path.startswith("#"):
                    paths.add(path)
            for contract in scene["contracts"]:
                if contract["compilerVersion"] != "0.8.30":
                    errors.append("unexpected compiler")
                params = contract["compilerParameters"]
                if params.get("optimizerOn") is not True or params.get("optimizerRuns") != 1 or params.get("viaIR") is not False:
                    errors.append("unexpected compiler semantics")
        if primaries != {"RolesHarness", "Permissions"}:
            errors.append("unexpected compiler scene")
        if not {"contracts/Roles.sol", "contracts/Permissions.sol", "certora/harness/RolesHarness.sol"}.issubset(paths):
            errors.append("missing actual implementation in compiler closure")
        for name in paths:
            path = (repo / name).resolve()
            if not path.is_file():
                errors.append("source unavailable: " + name)
                continue
            expected = path.read_text()
            if mutation and name == "contracts/Roles.sol":
                marker = "    ) external moduleOnly returns (bool success) {\n"
                if expected.count(marker) != 1:
                    raise ValueError("mutation is not unique")
                expected = expected.replace(marker, marker + MUTATIONS[mutation])
            if archive.read(".certora_sources/" + name).decode() != expected:
                errors.append("compiler source differs: " + name)
    return errors


def check_manifest(folder):
    manifest = json.loads((folder / "manifest.json").read_text())["filesSha256"]
    actual = {p.name for p in folder.iterdir() if p.is_file() and p.name != "manifest.json"}
    if set(manifest) != actual:
        raise ValueError("incomplete artifact manifest")
    for name, digest in manifest.items():
        path = (folder / name).resolve()
        if not path.is_relative_to(folder.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError("changed artifact: " + name)


def check_witness(outputs, mutation):
    matched = []
    for output in outputs.values():
        if (output.get("assertMessage") or "").startswith("rejection must precede boundary calls"):
            trace = list(walk(output.get("callTrace", {}), "childrenList"))
            messages = [n.get("message", {}) for n in trace]
            texts = [m.get("text", "") for m in messages]
            reverted = any(m.get("text", "").startswith("lastReverted ↪") and
                           any(a.get("value") == "true" for a in m.get("arguments", [])) for m in messages)
            if mutation == "call-before-revert":
                reverted |= "Revert" in texts and "assert lastReverted" in texts
            observed = any(m.get("text", "").startswith("Ghost assignment: attemptedEffect") and
                           any(a.get("value") == "true" for a in m.get("arguments", [])) for m in messages)
            opcode = "CALL" if mutation == "call-before-revert" else "ALL_SSTORE"
            hooked = any("Apply hook " + opcode + "(" in text for text in texts)
            if reverted and observed and hooked:
                matched.append(output)
    return [] if matched else ["no matching pre-revert effect counterexample"]


def check_native(folder, repo):
    errors = []
    receipt = json.loads((folder / "receipt.json").read_text())
    tool = receipt.get("forge", {})
    if "forge Version: 1.8.3" not in tool.get("version", "") or not re.fullmatch(r"[a-f0-9]{64}", tool.get("sha256", "")):
        errors.append("unbound native EVM tool")
    with zipfile.ZipFile(folder.parent / "original/submitted-inputs.zip") as archive:
        build = json.loads(archive.read(".certora_build.json"))
    expected_sources = {name for scene in build.values() for name in scene["srclist"].values()
                        if name.endswith(".sol") and not name.startswith("#")}
    expected_sources.add("certora/lemmas/BoundaryMutationReplay.t.sol")
    manifest = json.loads((folder / "manifest.json").read_text())["filesSha256"]
    actual = {p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file() and p.name != "manifest.json"}
    if set(manifest) != actual:
        errors.append("incomplete native replay manifest")
    for name, digest in manifest.items():
        path = (folder / name).resolve()
        if not path.is_relative_to(folder.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            errors.append("changed native replay artifact")
    contract = "certora/lemmas/BoundaryMutationReplay.t.sol:BoundaryMutationReplay"
    witness_contract = "certora/lemmas/BoundaryMutationReplay.t.sol:BoundaryFeasibilityWitnesses"
    witness_methods = {"test_allPremisesHaveFeasibleRejection()", "test_clearancePremiseIsNecessary()",
                       "test_deniedGrantPremiseIsNecessary()", "test_multisendPremiseIsNecessary()"}
    tests = {"call-before-revert": "test_observeCallBeforeRollback()",
             "write-before-rejection": "test_observeWriteBeforeRollback()"}
    for group in ["original", *MUTATIONS]:
        compiler = json.loads(gzip.decompress((folder / group / "compiler.json.gz").read_bytes()))
        settings = compiler["input"]["settings"]
        if compiler.get("solcVersion") != "0.8.30" or settings.get("evmVersion") != "paris" or settings.get("optimizer") != {"enabled": True, "runs": 1} or settings.get("viaIR", False) is not False:
            errors.append("native compiler semantics differ")
        if set(compiler["input"]["sources"]) != expected_sources:
            errors.append("native compiler source closure differs")
        for name, source in compiler["input"]["sources"].items():
            expected = (repo / name).read_text()
            if group != "original" and name == "contracts/Roles.sol":
                marker = "    ) external moduleOnly returns (bool success) {\n"
                if expected.count(marker) != 1:
                    raise ValueError("native mutation is not unique")
                expected = expected.replace(marker, marker + MUTATIONS[group])
            if source.get("content") != expected:
                errors.append("native source differs: " + name)
        results = json.loads((folder / group / "result.json").read_text())
        if set(results) != ({contract, witness_contract} if group == "original" else {contract}):
            errors.append("unexpected native test contract")
        if group == "original":
            witnesses = results.get(witness_contract, {}).get("test_results", {})
            if set(witnesses) != witness_methods or any(row.get("status") != "Success" for row in witnesses.values()):
                errors.append("missing or failed independent feasibility/premise witness")
        rows = results.get(contract, {}).get("test_results", {})
        names = set(tests.values()) if group == "original" else {tests[group]}
        if set(rows) != names:
            errors.append("native test instance universe differs")
        for name, result in rows.items():
            if result.get("status") != ("Failure" if group == "original" else "Success"):
                errors.append("native effect observation differs")
            if group == "original" and name == tests["call-before-revert"] and "was called 0 times" not in (result.get("reason") or ""):
                errors.append("original call control failed for the wrong reason")
    return errors


def assess(directory, repo):
    errors, groups = [], {}
    native_errors = []
    try:
        native_errors = check_native(directory / "native-replay", repo)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        native_errors.append("native replays: " + str(exc))
    errors += native_errors
    sanity = expected_sanity((repo / SPEC).read_text())
    for group in ["original", *MUTATIONS]:
        folder = directory / group
        group_errors = []
        try:
            check_manifest(folder)
            group_errors += check_sources(folder, repo, None if group == "original" else group)
            progress = json.loads((folder / "progress.json").read_text())
            found, roots = check_tree(progress, sanity, group != "original", not native_errors)
            group_errors += found
            outputs = read_outputs(folder, roots)
            if group != "original":
                group_errors += check_witness(outputs, group)
            else:
                for output in outputs.values():
                    for warning in output.get("callResolutionWarnings", []):
                        if "HAVOC_ALL" not in warning.get("summary", ""):
                            group_errors.append("unreviewed external summary in retained result")
                for root in roots:
                    if root.get("name") not in RULES:
                        continue
                    if not root.get("output"):
                        group_errors.append("missing functional rule output")
                    for name in root.get("output", []):
                        output = outputs[name]
                        if "callResolution" not in output or "callResolutionWarnings" not in output:
                            group_errors.append("missing call resolution evidence")
                        for warning in output.get("callResolutionWarnings", []):
                            if "HAVOC_ALL" not in warning.get("summary", "") or warning.get("isInCounterExample") is not False:
                                group_errors.append("unreviewed external summary or call witness")
        except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile) as exc:
            group_errors.append(str(exc))
        groups[group] = {"accepted": not group_errors, "errors": group_errors}
        errors += [group + ": " + error for error in group_errors]
    return {"accepted": not errors, "semanticClosureCertified": False, "groups": groups,
            "sanityWitnessBasis": "Independent native witnesses for feasibility and each premise across all three forwarders. Automatic sanity counterexamples include arithmetic imprecision and loop-unwinding assertions and are not accepted as the independent witnesses.",
            "errors": errors, "scope": "Conditional single-call rejection and boundary observation for three implemented forwarders. No configuration composition, deployment binding or history certificate."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    result = assess(args.evidence.resolve(), Path(__file__).resolve().parents[2])
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["accepted"] else 1)
