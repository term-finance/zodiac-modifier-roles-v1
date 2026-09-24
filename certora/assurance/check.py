#!/usr/bin/env python3
"""Inventory CVL proof contexts and generate independent boundary diagnostics.

This is an accounting/freshness checker, not a CVL parser or a proof kernel.
Semantic closure is deliberately not inferred from imports or a passing guard.
"""
import argparse
import fnmatch
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys

SCHEMA = 1
CERTIFICATE_LIFETIME = {
    "mode": "configuration-bound",
    "state": "unissued",
    "invalidate_on": ["code-or-immutables", "facet-or-proxy-routing", "registry-or-admission",
                      "roles-or-authorities", "initializer-or-unknown-writer", "storage-layout",
                      "external-model", "proof-context-or-toolchain", "incomplete-history-or-reorg"],
    "reactivate_on_restored_snapshot": False,
    "reissue_requires": "independent base, binding and semantic evidence checks",
}
OBLIGATIONS = {
    "roots": "All selectors, fallback/receive, constructors, initialization and upgrade transitions are accounted for.",
    "calls": "Compiler/bytecode call inventory and per-instance resolution reports cover typed, dynamic, library and delegate calls.",
    "targets": "Every possible receiver/selector/code/storage-context tuple is included or soundly modeled; target invariants are inductive.",
    "writers": "Every writer of relevant ordinary, namespaced and transient storage, including other facets and callbacks, is covered.",
    "models": "Each external summary refines the real environment conservatively, including reentrancy, revert and return-data behavior.",
    "scope": "Each functional rule's explored executions are included in the closure proof; filters, bounds and assumptions are justified.",
    "bindings": "Source/compiler/deployed code and mutable proxy, diamond, registry and role bindings match the claimed deployment scope.",
    "results": "Exact rule/method instances, call-resolution evidence, sanity results and tool versions are retained; no timeout or skipped instance passes.",
    "adequacy": "Requirements entailment, input partitions, frame conditions, witnesses and mutation results address specification strength separately.",
}
SKIP = {".git", "node_modules", ".venv", "venv", "artifacts", "cache", "out", "coverage", ".certora_internal", ".claude", ".agents"}
TOKENS = re.compile(r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[A-Za-z_$][\w$]*|\d+|=>|[^\s]')


def tokens(text):
    return [(m.group(), m.start()) for m in TOKENS.finditer(text) if not m.group().startswith(("//", "/*"))]


def read_conf(path):
    # Accept the repository's JSON-with-comments/trailing-commas dialect. Fail
    # on other JSON5 syntax instead of silently changing its interpretation.
    ts = tokens(path.read_text())
    return json.loads(" ".join(t for i, (t, _) in enumerate(ts)
                               if not (t == "," and i + 1 < len(ts) and ts[i + 1][0] in ("}", "]"))))


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def files(root):
    for base, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in SKIP and not d.startswith(".certora"))
        for name in sorted(names):
            p = Path(base) / name
            parts = p.relative_to(root).parts
            if any(parts[i:i + 2] == ("certora", "assurance") for i in range(len(parts) - 1)):
                continue
            if p.is_symlink() and p.suffix in (".sol", ".vy", ".spec", ".conf"):
                raise ValueError("symlinked verification input needs explicit handling: " + str(p))
            if not p.is_symlink():
                yield p


def safe_path(root, name):
    p = (root / name).resolve()
    if not p.is_relative_to(root.resolve()):
        raise ValueError("path escapes repository: " + name)
    return p


def spec_info(path):
    text = path.read_text()
    ts = tokens(text)
    imports, declarations, uses, hazards = [], [], [], []
    depth = 0
    for i, (t, pos) in enumerate(ts):
        next_t = ts[i + 1][0] if i + 1 < len(ts) else ""
        line = text.count("\n", 0, pos) + 1
        if depth == 0 and t == "import" and next_t[:1] in ('"', "'"):
            imports.append(next_t[1:-1])
        if depth == 0 and t in ("rule", "invariant") and (i == 0 or ts[i - 1][0] != "use"):
            declarations.append({"kind": t, "name": next_t, "line": line})
        if depth == 0 and t == "use" and next_t in ("rule", "invariant"):
            uses.append({"kind": next_t, "name": ts[i + 2][0], "line": line})
        if t in ("require", "requireInvariant", "filtered", "hook"):
            hazards.append({"kind": t, "line": line})
        if t == "=>":
            hazards.append({"kind": "summary-or-implication", "line": line, "next": next_t})
        if t == "assert" and next_t == "true":
            hazards.append({"kind": "trivial-assertion", "line": line})
        if t == "{":
            depth += 1
        elif t == "}":
            depth -= 1
    return {"sha256": sha(path), "imports": imports, "declarations": declarations, "uses": uses, "review_sites": hazards}


def inventory(root):
    root = root.resolve()
    paths = list(files(root))
    confs = sorted(p for p in paths if p.suffix == ".conf" and "certora" in p.parts)
    specs = sorted(p for p in paths if p.suffix == ".spec")
    modules = {p.relative_to(root).as_posix(): spec_info(p) for p in specs}
    inputs = {p.relative_to(root).as_posix(): sha(p) for p in paths
              if p.suffix in (".sol", ".vy", ".spec", ".conf") or p.name in
              ("requirements.txt", "package.json", "yarn.lock", "package-lock.json", "pnpm-lock.yaml", ".gitmodules",
               "foundry.toml", "hardhat.config.ts", ".tool-versions", "run-certora.sh")
              or ".github/workflows" in p.relative_to(root).as_posix()}
    inputs["$assurance_checker"] = sha(Path(__file__))
    contexts, owners = {}, {s: [] for s in modules}
    for path in confs:
        c = read_conf(path)
        if not isinstance(c.get("verify"), str) or ":" not in c["verify"]:
            raise ValueError(f"unsupported verification configuration: {path}")
        name = path.relative_to(root).as_posix()
        workdir = path.parent.parent.parent
        contract, spec = c["verify"].split(":", 1)
        root_spec = safe_path(root, (workdir.relative_to(root) / spec).as_posix()).relative_to(root).as_posix()
        reached, pending, errors, edges = set(), [root_spec], [], []
        while pending:
            src = pending.pop()
            if src in reached:
                continue
            reached.add(src)
            if src not in modules:
                errors.append("missing spec: " + src)
                continue
            for target in modules[src]["imports"]:
                # CVL imports are relative to the importing spec.
                dst = safe_path(root, (Path(src).parent / target).as_posix()).relative_to(root).as_posix()
                edges.append([src, dst])
                pending.append(dst)
        for src in reached & modules.keys():
            owners[src].append(name)
        declared = [{"module": src, **d} for src in sorted(reached & modules.keys()) for d in modules[src]["declarations"]]
        # Imports expose definitions; they do not run every imported rule.
        # These lexical entry names must be reconciled with the prover's actual
        # rule/method expansion before any semantic completeness claim.
        entry = modules.get(root_spec, {})
        requested = sorted({d["name"] for d in entry.get("declarations", []) + entry.get("uses", [])})
        selection = c.get("rule", ["*"])
        if isinstance(selection, str):
            selection = [selection]
        selected = [r for r in requested if any(fnmatch.fnmatchcase(r, pattern) for pattern in selection)]
        scene = []
        for item in c.get("files", []):
            file, _, explicit = item.partition(":")
            source = safe_path(root, (workdir.relative_to(root) / file).as_posix())
            if not source.exists():
                errors.append("missing scene source: " + str(source.relative_to(root)))
                continue
            ts = [t for t, _ in tokens(source.read_text())]
            definitions = [ts[i + 1] for i, t in enumerate(ts[:-1]) if t in ("contract", "library") and (i == 0 or ts[i - 1] != "abstract")]
            if explicit:
                definitions = [explicit] if explicit in definitions else []
            if len(definitions) != 1:
                errors.append("scene file needs an explicit unique contract: " + item)
            scene.extend(definitions)
        if contract not in scene:
            errors.append("verify target is not a declared scene contract: " + contract)
        context = {"workdir": workdir.relative_to(root).as_posix(), "config": c, "root_spec": root_spec,
                   "import_closure": sorted(reached), "import_edges": sorted(edges), "rule_candidates": declared,
                   "requested_entries": selected, "scene_contracts": sorted(set(scene)), "errors": errors}
        context["fingerprint"] = digest({"inputs": inputs, "context": context})
        contexts[name] = context
    for src in modules:
        modules[src]["contexts"] = owners[src]
        modules[src]["disposition"] = "referenced-module" if owners[src] else "unreferenced-requires-disposition"
    return {"schema": SCHEMA, "inputs": inputs, "modules": modules, "contexts": contexts,
            "limits": "Lexical inventory and source freshness only; semantic call closure and rule expansion require compiler/prover evidence."}


def companion(context):
    aliases = [f"using {name} as closureScene{i};" for i, name in enumerate(context["scene_contracts"])]
    domain = " || ".join(f"addr == closureScene{i}" for i in range(len(aliases))) or "false"
    text = "\n".join(aliases) + "\n\npersistent ghost bool dependencyEscaped;\n\n"
    text += "// Dynamic selectors need a separate trap; typed unknown receivers are\n// also observed by the opcode hooks. Call-resolution reports remain required.\n"
    text += "methods {\n    unresolved external in _._ => DISPATCH [] default ASSERT_FALSE;\n}\n\n"
    for op in ("CALL", "STATICCALL", "DELEGATECALL", "CALLCODE"):
        args = "uint g, address addr, " + ("uint value, " if op in ("CALL", "CALLCODE") else "")
        args += "uint argsOffset, uint argsLength, uint retOffset, uint retLength"
        condition = "true" if op == "CALLCODE" else f"!({domain})"
        text += f"hook {op}({args}) uint rc {{\n    dependencyEscaped = dependencyEscaped || {condition};\n}}\n\n"
    for op, args, ret in (("CREATE1", "uint value, uint offset, uint length", " address result"),
                          ("CREATE2", "uint value, uint offset, uint length, bytes32 salt", " address result"),
                          ("SELFDESTRUCT", "address addr", "")):
        text += f"hook {op}({args}){ret} {{\n    dependencyEscaped = true;\n}}\n\n"
    text += """// Persistent state retains observations on paths that subsequently revert.
// No functional-spec imports, preconditions, or method filters apply here.
rule dependencyClosureBoundary(method f) {
    env e;
    calldataarg args;
    dependencyEscaped = false;
    f@withrevert(e, args);
    assert !dependencyEscaped, "Call, creation or destruction escaped the declared scene";
}

rule dependencyClosureReachable(method f) {
    env e;
    calldataarg args;
    f@withrevert(e, args);
    satisfy !lastReverted;
}
"""
    return text


def generated(context, conf_name):
    base = Path(conf_name).stem
    # Copy only scene/compiler settings. Do not inherit proof shortcuts or
    # functional rule/method restrictions into the independent diagnostic.
    allowed = {"files", "link", "packages", "solc", "solc_map", "solc_optimize", "solc_via_ir", "solc_evm_version"}
    conf = {k: v for k, v in context["config"].items() if k in allowed}
    conf.update({"verify": context["config"]["verify"].split(":")[0] + f":certora/assurance/specs/{base}.spec",
                 "optimistic_loop": False, "loop_iter": context["config"].get("loop_iter", "2"), "rule_sanity": "basic",
                 "rule": ["dependencyClosureBoundary", "dependencyClosureReachable"]})
    return {f"specs/{base}.spec": companion(context), f"confs/{base}.conf": json.dumps(conf, indent=2) + "\n"}


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def refresh(root, data):
    save(root / "certora/assurance/inventory.json", data)
    target = root / "certora/assurance/check.py"
    if target.resolve() != Path(__file__).resolve():
        shutil.copyfile(__file__, target)
    for name, context in data["contexts"].items():
        directory = root / context["workdir"] / "certora/assurance"
        for relative, text in generated(context, name).items():
            out = directory / relative
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(text)
        record = directory / "obligations" / (Path(name).stem + ".json")
        if not record.exists():
            save(record, {"schema": SCHEMA, "context": name, "fingerprint": context["fingerprint"],
                          "certificate_lifetime": CERTIFICATE_LIFETIME,
                          "status": "unproved", "obligations": {k: {"claim": v, "status": "open", "evidence": []}
                                                                      for k, v in OBLIGATIONS.items()}})


def check(root, data, inventory_only=False):
    errors = []
    stored = root / "certora/assurance/inventory.json"
    checker = root / "certora/assurance/check.py"
    if not checker.exists() or sha(checker) != sha(Path(__file__)):
        errors.append("repository accounting checker missing or differs from the invoked checker")
    if not stored.exists() or json.loads(stored.read_text()) != data:
        errors.append("inventory missing or stale; regenerate and review the changed proof scope")
    for name, context in data["contexts"].items():
        directory = root / context["workdir"] / "certora/assurance"
        for relative, expected in generated(context, name).items():
            p = directory / relative
            if not p.exists() or p.read_text() != expected:
                errors.append(name + ": boundary diagnostic missing or stale: " + relative)
        p = directory / "obligations" / (Path(name).stem + ".json")
        if not p.exists():
            errors.append(name + ": missing closure obligations")
            continue
        record = json.loads(p.read_text())
        if record.get("context") != name or record.get("fingerprint") != context["fingerprint"]:
            errors.append(name + ": stale proof context (refresh does not re-approve evidence)")
        if set(record.get("obligations", {})) != set(OBLIGATIONS):
            errors.append(name + ": missing or unknown proof obligations")
        if record.get("certificate_lifetime") != CERTIFICATE_LIFETIME:
            errors.append(name + ": missing or unsupported certificate lifetime policy")
        errors.extend(name + ": " + e for e in context["errors"])
        if not inventory_only:
            # No untrusted status string is accepted as a proof. A verifier
            # integration must independently replay/check the semantic evidence
            # before this accounting checker can acquire a certification mode.
            errors.append(name + ": semantic closure is NOT CERTIFIED; replayable evidence checker is required")
        if record.get("status") != "unproved" or any(o.get("status") not in ("open", "blocked") for o in record.get("obligations", {}).values()):
            errors.append(name + ": unsupported proof claim; this tool cannot certify semantic closure")
    if not inventory_only:
        errors.extend(s + ": unreferenced CVL module requires a disposition" for s, m in data["modules"].items() if not m["contexts"])
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("refresh", "check"))
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--inventory-only", action="store_true", help="check accounting only; NEVER certifies semantic closure")
    args = parser.parse_args()
    root = args.repo.resolve()
    data = inventory(root)
    if args.action == "refresh":
        refresh(root, data)
        print(f"Registered {len(data['modules'])} CVL modules / {len(data['contexts'])} contexts. No proofs certified.")
        return 0
    errors = check(root, data, args.inventory_only)
    for error in errors:
        print(error, file=sys.stderr)
    print(f"{'FAIL' if errors else 'PASS (ACCOUNTING ONLY)'}: {len(data['modules'])} modules, {len(data['contexts'])} contexts; 0 semantic closure certificates.")
    return 1 if errors else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, IndexError) as exc:
        print("assurance check failed: " + str(exc), file=sys.stderr)
        sys.exit(2)
