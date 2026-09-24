# Permission proof results — 24 September 2026

The [conditional boundary assessment](configured-boundary/acceptance.json)
accepts three single-call forwarding rules, with bound sources, eighteen sanity
statuses, independent native witnesses and two mutation controls. It explicitly
does **not** certify complete semantic closure. See the
[theorem and limitations](../../../lemmas/CONFIGURED_BOUNDARY.md).

The separate configuration lemmas prove the actual library transition and packed
key representation. Composing those results through the public setup sequence,
binding deployed code/configuration, and proving configuration-history validity
remain open. The canonical unsplit `Roles-delayProtection.conf` is unchanged.

| Retained attempt | Finding and disposition |
| --- | --- |
| `exact-byte-default-arithmetic` | The unsplit theorem still reports error 27672571, an integer/bit-vector type error. No theorem accepted. |
| `configured-rejection` | The main assertions and automatic sanity statuses are green. Auxiliary unresolved-call traps supply some sanity witnesses and typed calls retain default summaries. Superseded, not accepted as the final boundary lemma. |
| `unqualified-effects-diagnostic` | The effect hook detects the real Permissions delegatecall. The actual library must be included in the owned boundary. |
| `helper-premises-diagnostic` | Helper-contained premises remain in the sanity transformation; the final report has sanity failures. |
| `unconditional-write-diagnostic` | A write immediately followed by unconditional revert was removed during compilation. This is not a killed write mutation. |
| `explicit-premises-default-typed-diagnostic` | Explicit premises fix sanity enumeration; typed external calls still use default summaries. Superseded by the conservative context. |
| `call-before-revert-mutation`, `explicit-premises-call-diagnostic`, `explicit-premises-write-diagnostic` | Earlier effect controls; retained separately from the final controls. |
| `configured-boundary` | Actual owned code, explicit premises, conservative typed/dynamic unknown calls, terminal proof outputs, independent native witnesses and validated effect observations. Accepted only for the documented conditional lemma. |

Each job directory retains exact submitted inputs, rule/call-resolution outputs,
terminal status or the recorded collection state, and artifact hashes. A job's
`assessment.json` is the collector's diagnostic report and always refuses
automatic acceptance. The separate checked `configured-boundary/acceptance.json`
records the narrower accepted claim. Green automatic sanity alone is insufficient:
its loop-unwinding and imprecise valuations remain visible alongside the genuine
native feasibility/premise witnesses.
