# CVL assurance records

The inventory registers **seven CVL modules and seven proof contexts**, including
all six pre-existing configurations and the new veto-only Delay policy rule.
Every context has an independent boundary diagnostic and all nine semantic
obligation families. **None has a semantic dependency-closure certificate.**

```sh
python3 certora/assurance/check.py check --inventory-only
python3 certora/assurance/check.py check
```

The first command checks inventory, companion generation and context freshness.
The second must fail while semantic closure remains unproved. Run functional and
companion Certora configurations from `packages/evm`.

The historical boundary jobs completed but failed their acceptance criteria.
Their method universe includes eleven compiled `Permissions` library methods
that were not directly instantiated. Missing instances, unresolved calls and
bounds require explicit dispositions. The retained historical harness predates
two new pure selector getters, so its context bindings are marked stale; no old
result is promoted to a proof of the current harness.

The new [Delay rule](../../packages/evm/certora/specs/Roles/delayProtection.spec)
checks that after successful target scoping, explicit selector revocation and a
veto-only grant, a different selector cannot pass any of the three implemented
forwarding entrypoints. It quantifies over target, role, payload, caller, value,
operation and revert option, with these explicit limits:

- The target differs from the special multisend address; deployment checks bind
  multisend to zero and the actual Delay to a nonzero address.
- The tested selector differs from the intentionally permitted veto selector.
- Plain CVL configuration calls describe a **successful authorized setup**.
  They filter reverting setup; this is not a proof that any caller can configure
  permissions or that an arbitrary starting state is historically reachable.
- The property covers the resulting configuration. It does not establish
  arbitrary-history preservation across subsequent owner or governance changes,
  Safe signature security, Delay correctness, or a full deployment theorem.
- Exact bitwise and byte-memory options are enabled; packed-key aliasing
  counterexamples remained with bitwise precision alone and did not replay in
  the retained native EVM test. They remain unaccepted diagnostics. There are no
  unbounded `mathint` calculations in this rule. See the [Certora option
  documentation](https://docs.certora.com/en/latest/docs/prover/cli/options.html#precise-bitwise-ops).
- Loop optimism is disabled and unresolved external calls fail an assertion.
  Advanced sanity, exact instances and terminal prover results must pass before
  the theorem is accepted. Compilation or job completion alone is insufficient.

The first submitted draft failed advanced sanity because explicit owner/value
preconditions duplicated conditions already imposed by successful setup. Later
unaccepted drafts exposed packed-key aliasing under the memory model, including
a draft with exact bitwise operations. The native replay distinguishes the
observed alias from the compiled EVM behavior; it does not itself prove the rule.
These outcomes are retained; the current proof result is recorded under
`packages/evm/certora/assurance/evidence/delay-protection-2026-09-22/`.

[Deployment fix PR #3450](https://github.com/term-finance/term-finance-web3-infra/pull/3450)
binds actual runtime/library code, exhaustively scans proposer role IDs, tests
all Delay ABI selectors, executes the actual chain-cd assertions on local forks,
checks the 86,399/86,400-second boundary and preserves immediate veto. Its
9-of-9 owner bypass and separate Arbitrum diamond 2-of-2 authority remain explicit
trust boundaries. The fix is proposed, not deployed.

[Core PR #1837](https://github.com/term-finance/term-finance/pull/1837) contains the
cross-repository census, partial controller proofs, refuted unrestricted closure
candidates and the formal-verification skill. Dependency closure does not prove
that every intended requirement was specified; adequacy, non-vacuity, frame
conditions, mutation controls and temporal properties remain separate obligations.

The exact byte-memory attempts under both CLI 7.31.0 and CLI 8.19.2 report prover
error **27672571** for the main rule. They are retained under
`byte-memory-731-error` and `precise-policy`, respectively. **The new policy
theorem is unproved**, and its CI job must remain blocking until all main and
advanced-sanity instances pass. The six legacy jobs keep CLI 7.31.0. Job-level
`SUCCEEDED` means the service completed, not that a theorem passed; read the
exact rule statuses and `functionalPolicyTheoremAccepted` in each assessment.

The [native replay](../../packages/evm/certora/assurance/evidence/delay-protection-2026-09-22/native-packed-key/README.md)
extracts the original contracts and dependencies from the retained submitted
archive and reproduces the empty/two-byte payload cases under solc 0.8.30. It
checks only the reported packed-key alias. It is neither a universal permission
proof nor a replacement for the failing solver job.

Two further attempts are retained with exact submitted inputs: splitting the same
theorem into three forwarding rules still produced error 27672571
(`split-forwarders-error`, job `67f2a1be659a4f1eacb7b4dfd1507cc1`). Exact overlap
inlining without exact SMT byte maps produced three violated assertions
(`exact-inlining-diagnostic`, job `8077cd2558594e04b531d9b8489fcfa2`). Those new
counterexamples require triage; neither attempt is accepted. The canonical spec
and exact-memory configuration are preserved, with no case removed.

The approved configuration-bound lifetime policy is now recorded for all seven
contexts: code, role, registry, model, context or incomplete-history changes
invalidate a certificate permanently; a matching restored snapshot cannot revive
it. All certificates remain unissued while semantic obligations are open.

A separate bytecode-level Halmos lemma proves packed-key injectivity for arbitrary
address/selector pairs using the actual `Permissions.keyForFunctions` body. See
`symbolic-packed-key` for its compiler inputs and six explored paths. This is a
supporting lemma, not acceptance of the still-failing CVL permission theorem.
