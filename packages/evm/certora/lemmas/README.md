# Permission configuration lemmas

Two executed Halmos lemmas support the Delay permission proof. They do not issue
a dependency-closure certificate or establish deployed permissions.

`DelayConfiguration.t.sol` invokes the actual `Permissions` implementation. It
proves:

- The packed function key equals the 160-bit target followed by the 32-bit
  selector and 64 zero bits, for every address and selector.
- From arbitrary existing storage, at an arbitrary 256-bit Role base slot,
  `scopeTarget`, `scopeRevokeFunction(denied)` and
  `scopeAllowFunction(permitted, None)` establish target clearance `Function`
  and target options `None`, and leave a nonzero grant for
  the permitted selector. If the selectors differ, the denied grant is zero.
  Every other target/selector function grant is unchanged.

There are no `assume` statements or excluded scalar inputs. Zero addresses,
equal selectors, address aliases and arbitrary dormant grants are included.
Symbolic storage is an overapproximation of possible starting grants; this is a
transition theorem, not an initialization or historical-reachability proof.
The proof does not cover owner authorization, calldata conversion, forwarding,
multisend, Safe/Delay behavior or later configuration changes.

The retained compiler inputs bind solc 0.8.30, Paris, optimizer runs 1, no IR
pipeline, and the exact three-source import closure. Halmos 0.3.3, Foundry 1.8.3
and Z3 4.12.6 identities are recorded. Compilation, symbolic EVM execution,
storage/hash abstractions and solver simplification remain trusted. No gas or
deployed-bytecode equivalence theorem is claimed. No truncation or blocked path
is accepted. Solver queries are retained when the symbolic executor emits them;
the original two lemmas simplify without emitting separate SMT query files.

The [retained evidence](../assurance/evidence/delay-configuration-2026-09-24/assessment.json)
also contains three compiling implementation mutants: omitted revocation,
erased selector bits, and target-wide clearance. Each has a validated assertion
counterexample. Compile failures and solver errors do not count as killed mutants.
This is adequacy evidence for those three faults, not all possible specification
omissions. Fifteen damaged-result variants exercise the acceptance checker.

Run from `packages/evm`, with the locked dependencies installed:

```sh
python3 certora/lemmas/run-delay-configuration.py /path/to/new/evidence \
  --solc /path/to/solc-0.8.30 --solver /path/to/z3-4.12.6
python3 certora/lemmas/check-delay-configuration.py /path/to/new/evidence
python3 certora/lemmas/test-delay-configuration-checker.py
```

The policy CI job checks the retained evidence and checker regressions after
dependency installation. It does not rerun Halmos. Changed sources, compiler
semantics, incomplete method results or missing mutation evidence are rejected.
A separate successful forwarding proof and its composition/deployment bindings
are still required before claiming the complete permission theorem.
