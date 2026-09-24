# Conditional forwarding boundary

`Roles-configuredBoundary.conf` checks three implemented forwarding entrypoints
with the actual `RolesHarness`, `Roles` and linked `Permissions` code. It does
not replace the original setup-and-forwarding rule or certify a deployment.

For an arbitrary role, target, payload, caller, value, operation and revert
option, the premise is:

1. The target differs from the configured special multisend parser address.
2. Its target clearance is `Function`.
3. The function grant selected by the actual `bytes4(data)` getter is zero.

Each entrypoint must then revert without an attempted CALL, STATICCALL,
CALLCODE, creation, destruction, SSTORE or TSTORE. The only permitted
DELEGATECALL target is the linked actual Permissions library; its body and
outgoing effects remain analyzed. Persistent ghosts retain observations when
execution reverts. The configuration disables storage splitting for the raw
storage hooks. Dynamic and typed unresolved external calls explicitly use
`HAVOC_ALL`; resolved owned bodies are retained. The final call-resolution
reports must confirm those summary choices.

The six outcome assertions and eighteen advanced sanity instances are checked
separately. Preconditions occur directly in each rule so sanity transformations
can remove them. There are no calldata length bounds or extra caller/role
membership preconditions. Non-reverting setup is not assumed to have run here:
the state predicate is an explicit antecedent needing separate establishment.

The configuration lemmas establish the library updates from arbitrary storage.
They do not by themselves establish this predicate after the public owner-gated
wrapper sequence. Calldata correspondence, wrapper composition, deployment
bytecode/library binding, initialization, ordinary transitions and sticky
invalidation across all configuration writers remain separate obligations.
The two empty inherited module execution bodies, multisend parsing and all
other entrypoints are outside this three-entrypoint lemma and remain in the
repository-wide closure inventory.

`check-configured-boundary.py` checks the terminal typed result tree, exact
premise/assertion sanity instances, source/dependency contents, compiler and
configuration, call-resolution summaries and retained artifact hashes. It also
requires compiling mutations that call an arbitrary target and then revert,
or write storage before the real permission check rejects. Each mutation must
have a counterexample to the persistent effect assertion with `lastReverted`
still true. Mutation sanity checks are unnecessary for such a concrete
counterexample; the original proof retains advanced sanity checks.

This checks proof-service evidence under the compiler, Certora EVM/storage/hash
model, solver and report/checker trust boundary. It is not an independent proof
kernel, gas theorem, assumption approval or semantic closure certificate. The
checker always reports `semanticClosureCertified: false`. Report retrieval can
fail after submission; acceptance uses the terminal server report, never the
CLI exit code alone. Historical and unsuccessful diagnostics stay retained.

The retained final job `082ee9fed45347319b98ee00b115674e` verifies all three
rules and marks all eighteen sanity instances green. Inspection of the sanity
counterexamples still finds arithmetic imprecision and three loop-unwinding
assertions. Those valuations are not accepted as the independent witnesses.
Four native witness tests instead exercise all three entrypoints: one satisfies
all premises and reaches rejection, and three independently negate each premise
while retaining the others and successfully reaching the receiver. These twelve
concrete cases establish feasibility, premise necessity and non-tautology; they
do not replace the universal main assertions. The witness avatar is an explicitly
constructed possible environment within `HAVOC_ALL`, not a model of a deployed
Safe. No bound, predicate or input domain of the main theorem was weakened.

The native mutation controls also pass, and the original implementation fails
both effect-expectation controls as required. Symbolic mutation counterexamples
retain their byte-prefix arithmetic warnings; the feasible native controls
independently demonstrate the same fault classes. They do not claim to replay
every value in the symbolic models. Exact compiler input/output archives,
Foundry commands and results are in `native-replay/`; restore their compiler
sources in an isolated directory and use the retained `foundry.toml` with a local
solc 0.8.30 executable to reproduce the recorded offline commands.
