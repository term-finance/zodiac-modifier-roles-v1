# Certora proof inventory

One row per lemma. The lemma is the primary key; the value is the rule (or rules)
that establish it. Where several rules share a lemma they are alternative routes to
the same claim — a different entry point, a worse-case configuration, or the guard
half of an end-to-end statement — and the lemma is proved only if all of them verify.

**Status: all 59 rules verify**, across all six confs, with `rule_sanity: basic` clean —
no rule passes on an unreachable body. Rules marked *(witness)* discharge non-vacuity rather
than stating a bound: some are `satisfy` rules, the rest reachability `assert`s over a
`@withrevert` call. See [Reproducing](#reproducing) for the commands, and
[Explicitly not proved](#explicitly-not-proved) for what these results do and do not cover.

---

## What the proofs add up to

The 41 lemmas below support four conclusions. None of them is stated by any single rule — each
is a composition, and each names the lemmas it rests on so that weakening one is visible rather
than silent.

**1. The Governor's authority over the Delay is exactly one function.** Every call the Governor
completes through the Roles module is `setTxNonce(uint256)` on the Delay, with `value == 0` and
`Operation.Call`, on all four execution entry points (1.1); it can reach no other Roles entry
point at all, because everything else is `onlyOwner` (1.2); and the intended call really is
reachable, so the bound is not achieved by nothing working (1.3).

**2. That bound survives the loss of either gate.** SetTxNonceGuard alone gives it with *no
assumption whatsoever* about the role configuration — including an explicitly worst-case one,
blanket `Clearance.Target` with `ExecutionOptions.Both` on an arbitrary address (2.1, 2.2). The
role configuration alone gives it with no guard installed (3.1), with one gap at the multisend
address (3.3) that the guard closes (2.3). The two gates are therefore redundant rather than
merely layered: either one failing leaves the containment standing, and the pair covers the one
place a single gate does not.

**3. The containment cannot be widened from inside.** Every piece of Roles configuration the
bounds in 1–2 depend on — guard, multisend, avatar, target, owner, the module ring,
`defaultRoles`, role membership, target clearance — moves only for `owner` (6.2), and ownership
itself moves only through `transferOwnership` or `renounceOwnership` and only for the current
owner (6.3), so the rule cannot be sidestepped by first becoming the owner. On the Delay side the
module ring moves only under `enableModule`/`disableModule` and only for `owner` (5.2), queue
entries can be left only by an address already in that ring (5.3), and the guard slot is
owner-only too (5.5). Composing 1.1 with 5.2 gives the claim the integration exists to secure:
**the Governor can never enable a module on the Delay** — and 5.6 closes the indirect route,
since an execution forwarded through the avatar and back does not become a module grant. The
initialization escape hatch is shut on both contracts: `setUp` is spent (5.1, 6.1), which
discharges as a lemma what the assumptions table previously carried unproved.

**4. The pause veto holds the queue without freezing the cancellation.** Only the `pauser` may
pause and only an `ADMIN_ROLE` holder may unpause (4.3–4.6); `ADMIN_ROLE` membership is fixed at
deployment and AccessControl's inherited `grantRole`, `revokeRole` and `renounceRole` are all
dead (4.10–4.14), so the party being paused cannot acquire the power to unpause itself. The
`pauser` can be replaced, but only by an `ADMIN_ROLE` holder (4.8, 4.9). While paused,
`executeNextTx` reverts with nothing reaching the target (4.15) — and in that *same* state the
DelayOwnerSafe can still bump `txNonce` past the pending entry (4.18, 4.19), which does not clear
the pause (4.20). The whole thing is reversible (4.16, 4.21).

Taken together: the Governor is confined to a single function call against the Delay by two
independently sufficient gates, it cannot reach the configuration that confines it, it cannot
acquire a module slot on the Delay by any route in scene, and an independent pauser can stop
execution without losing the owner's ability to cancel. The remaining routes to change any of
this run through the Ownerless Safe and the DelayOwnerSafe acting under their own quorums and
the Delay's cooldown — in the open, and subject to the same veto.

### Coverage, and the shape of the evidence

- **59 rules, 41 lemmas, 6 confs.** The Delay and Roles scenes are the real mastercopies, not
  models; the two harnesses ([`DelayHarness`](harness/DelayHarness.sol),
  [`RolesHarness`](harness/RolesHarness.sol)) add view getters over internal storage and no logic.
- **The containment lemmas are stated four times each**, once per execution entry point, so a
  future divergence between `exec` and `execAndReturnData`, or between the named-role and
  default-role paths, cannot hide behind a single rule.
- **The integrity lemmas are parametric** (4.7, 4.9, 4.12–4.14, 5.2–5.5, 6.2, 6.3): they quantify
  over every state-changing entry point and every caller, and 5.2–5.5 and 6.2–6.3 assume nothing
  about the pre-state at all. They hold from any storage the Prover can construct, which is what
  makes them survive somebody later adding an entry point.
- **Non-vacuity is discharged explicitly**, not assumed: a witness rule per bound, plus
  `rule_sanity: basic` on all six confs.

### Where the boundary is

Two kinds of residue, both enumerated below rather than left implicit.

*Deployment facts* the rules depend on but do not establish — who the owners are, that the
Delay's `target` is not its `owner`, that the Ownerless Safe and the DelayOwnerSafe are distinct
addresses. These are checked in the verification plan, not here.

*Bounded-scope assumptions* where the Prover needs a finite model — hashing length bounds, loop
unrolling, single-entry multisend batches. These limit the range of a claim rather than its
validity.

And one thing that is not residue but design: **none of this constrains the owners themselves.**
An Ownerless Safe quorum can rewrite the Roles configuration, and a DelayOwnerSafe quorum can
enable a module on the Delay. Every lemma here says only that nothing *else* can.

---

Roles exposes **four** execution entry points — the 2x2 of {caller-named `role`,
`defaultRoles[msg.sender]`} x {`exec`, `execAndReturnData`} ([`Roles.sol:314`](../contracts/Roles.sol#L314),
[`:337`](../contracts/Roles.sol#L337), [`:357`](../contracts/Roles.sol#L357),
[`:380`](../contracts/Roles.sol#L380)). Each of the three bounding lemmas below (1.1, 2.1, 3.1)
is carried by four rules, one per entry point, asserted separately so a future divergence
between the `exec` and `execAndReturnData` paths — or between the named-role and default-role
paths — cannot hide.

Sources:

| Conf | Spec | Scene | Rules | Lemmas |
| --- | --- | --- | --- | --- |
| [`confs/Roles-setTxNonceGuardAndRoleConfig.conf`](confs/Roles-setTxNonceGuardAndRoleConfig.conf) | [`specs/Roles/setTxNonceGuardAndRoleConfig.spec`](specs/Roles/setTxNonceGuardAndRoleConfig.spec) | Roles + SetTxNonceGuard + role clearance and membership pins | 6 | 1.1–1.3 |
| [`confs/Roles-setTxNonceGuardSufficient.conf`](confs/Roles-setTxNonceGuardSufficient.conf) | [`specs/Roles/setTxNonceGuardSufficient.spec`](specs/Roles/setTxNonceGuardSufficient.spec) | Roles + SetTxNonceGuard, role configuration unconstrained | 7 | 2.1–2.4 |
| [`confs/Roles-setTxNonceRoleConfigSufficient.conf`](confs/Roles-setTxNonceRoleConfigSufficient.conf) | [`specs/Roles/setTxNonceRoleConfigSufficient.spec`](specs/Roles/setTxNonceRoleConfigSufficient.spec) | Roles + setTxNonce role config, `guard() == 0` | 7 | 3.1–3.3 |
| [`confs/Delay-pauseGuardSufficient.conf`](confs/Delay-pauseGuardSufficient.conf) | [`specs/Delay/pauseGuardSufficient.spec`](specs/Delay/pauseGuardSufficient.spec) | Delay + PauseGuard installed via `Guardable.setGuard` | 26 | 4.1–4.21 |
| [`confs/Delay-moduleIntegrity.conf`](confs/Delay-moduleIntegrity.conf) | [`specs/Delay/moduleIntegrity.spec`](specs/Delay/moduleIntegrity.spec) | Delay via `DelayHarness`, `target` linked to `ReenteringAvatar` | 9 | 5.1–5.6 |
| [`confs/Roles-configIntegrity.conf`](confs/Roles-configIntegrity.conf) | [`specs/Roles/configIntegrity.spec`](specs/Roles/configIntegrity.spec) | Roles + SetTxNonceGuard, configuration unconstrained | 4 | 6.1–6.3 |
| | | **total** | **59** | **41** |

---

### A Prover constraint the specs work around

`RolesHarness` exposes the per-function scope config two ways: `functionScopeConfigForData`
(`bytes` blob) and `functionScopeConfigForSelector` (`uint32` selector). They read the same slot —
the `bytes` form does `bytes4(data)` on entry — but **the setup predicates shared by the
containment rules must use the selector form.**

Calling the `bytes` form in a `require` makes the *other* requires in the same predicate stop
binding. The four containment rules of Properties 1 and 3 then report counterexamples in which
`to`, `value`, `operation` and the selector are simultaneously unconstrained — not one conjunct
broken, but the permission gate behaving as though it verified nothing.

That is not possible for a sound `require`: adding one can only remove states. It was isolated by
bisecting Property 1's spec, whose preconditions are a strict superset of Property 2's yet which
failed the same four conclusions until the `bytes`-form call was removed; Property 2, which never
calls either getter, passed throughout. Both properties verify once the call is gone (Property 1)
or restated through the selector form (Property 3).

The contracts are not implicated — the same counterexample appears against the audited
`Permissions.sol` and against this repo's later one, and the deployed bytecode is unchanged by any
of it. Treat it as a harness/CVL interaction. The `bytes` form is still used in a `require` inside
Property 1's witness rule 1.3, which verifies — that rule constrains one concrete configuration
rather than sharing a predicate with the containment rules, and does not exhibit the behaviour. The
rule to follow is that no predicate feeding a containment rule may call it.

---

## Property 1 — SetTxNonceGuard *and* the setTxNonce role configuration

Spec: `specs/Roles/setTxNonceGuardAndRoleConfig.spec`

The configuration half of this scene pins role 1's **clearance on the Delay and the Governor's
membership**, but deliberately **not** the per-function scope (`scopeAllowFunction`). Stating that
last pin tripped the CVL constraint described above, and the four containment rules verify without
it — so what 1.1 establishes is strictly stronger than "both gates fully pinned". The function-scope
pin is load-bearing only where no guard is installed, which is Property 3.

| # | Lemma proved | Rule(s) |
| --- | --- | --- |
| 1.1 | With the guard installed and role 1 pinned as above, every call the Governor completes through the Roles module is `setTxNonce(uint256)` on the Delay, with `value == 0` and `Operation.Call` — on **all four** execution entry points. | `governorExecTransactionWithRoleLimitedToDelaySetTxNonce`, `governorExecTransactionFromModuleLimitedToDelaySetTxNonce`, `governorExecTransactionWithRoleReturnDataLimitedToDelaySetTxNonce`, `governorExecTransactionFromModuleReturnDataLimitedToDelaySetTxNonce` |
| 1.2 | The Governor cannot successfully call any Roles entry point other than the four execution entry points — everything else is `onlyOwner`, and `setUp` is spent once the module is set up. | `governorSucceedsOnlyThroughRolesExecEntryPoints` |
| 1.3 | The bound above is non-vacuous: the intended `setTxNonce` call really is reachable under the same wiring and configuration. | `governorCanStillCallDelaySetTxNonce` (witness) |

---

## Property 2 — SetTxNonceGuard alone is sufficient

Spec: `specs/Roles/setTxNonceGuardSufficient.spec`. No `require` touches `roles[]` storage, so the
Prover may pick the most permissive role configuration that exists.

| # | Lemma proved | Rule(s) |
| --- | --- | --- |
| 2.1 | With SetTxNonceGuard installed and pinned to the Delay, and **no assumption at all** about the role configuration, every completed execution is `setTxNonce(uint256)` on the Delay with `value == 0` and `Operation.Call` — on **all four** execution entry points. | `setTxNonceGuardLimitsExecTransactionWithRoleToDelaySetTxNonce`, `setTxNonceGuardLimitsExecTransactionFromModuleToDelaySetTxNonce`, `setTxNonceGuardLimitsExecTransactionWithRoleReturnDataToDelaySetTxNonce`, `setTxNonceGuardLimitsExecTransactionFromModuleReturnDataToDelaySetTxNonce` |
| 2.2 | The same bound holds under an explicitly worst-case configuration: caller is an enabled module, a member of the role it names, and that role holds blanket `Clearance.Target` with `ExecutionOptions.Both` on an arbitrary address. | `setTxNonceGuardLimitsToDelaySetTxNonceUnderMaximallyPermissiveRoles` |
| 2.3 | The multisend branch — the one place the role layer does not bound the outer `to` — is closed by the guard: a transaction addressed to the configured multisend always reverts. | `setTxNonceGuardRejectsMultisendTarget` |
| 2.4 | The guard is what does the bounding, not an artefact of the scene: with `guard() == 0` and the same permissive configuration, a non-Delay call succeeds. | `withoutSetTxNonceGuardPermissiveRolesAllowNonDelayCall` (witness) |

---

## Property 3 — the setTxNonce role configuration alone is sufficient

Spec: `specs/Roles/setTxNonceRoleConfigSufficient.spec`. `guard() == 0` throughout, so
`Permissions.check` is the only gate.

| # | Lemma proved | Rule(s) |
| --- | --- | --- |
| 3.1 | With no guard installed, the runbook role configuration (`scopeTarget` → `Clearance.Function` on the Delay, `scopeAllowFunction(setTxNonce, Options.None)`, `assignRoles(governor, [1])`) admits only `setTxNonce(uint256)` on the Delay with `value == 0` and `Operation.Call`, **provided `to != multisend()`** — on **all four** execution entry points. | `roleConfigLimitsExecTransactionWithRoleToDelaySetTxNonce`, `roleConfigLimitsExecTransactionFromModuleToDelaySetTxNonce`, `roleConfigLimitsExecTransactionWithRoleReturnDataToDelaySetTxNonce`, `roleConfigLimitsExecTransactionFromModuleReturnDataToDelaySetTxNonce` |
| 3.2 | A caller that is not a member of the named role can execute nothing at all, whatever it sends — the `assignRoles` half of the configuration, isolated from the scoping half. | `nonMemberExecTransactionWithRoleAlwaysReverts` |
| 3.2a | Inside the multisend branch, a **single-entry** batch is still bounded: if it completes, that entry is `setTxNonce` on the Delay with `value == 0` and `Operation.Call`. `checkMultisendTransaction` forwards each entry to the same `checkTransaction` the direct path uses ([`Permissions.sol:236`](../contracts/Permissions.sol#L236)). **Scope: one entry only** — the conf's `loop_iter: 1` with `optimistic_loop` means longer batches are assumed away, not checked; the rule requires the single-entry shape explicitly rather than relying on that assumption. | `roleConfigLimitsSingleEntryMultisendToDelaySetTxNonce` |
| 3.3 | The `to != multisend()` caveat in 3.1 is real and not merely conservative: without the guard, a transaction addressed to the configured multisend completes even though `to` is not the Delay, because `Permissions.check` takes the batch branch before consulting clearance for `to`. | `withoutSetTxNonceGuardMultisendTargetEscapesRoleConfig` (witness) |

> 3.3 read together with 2.3 is the argument for keeping SetTxNonceGuard even though the
> role configuration is correct: the same call reverts once the guard is installed.

---

## Property 4 — PauseGuard on the Delay

Spec: `specs/Delay/pauseGuardSufficient.spec`. The scene is the real Delay mastercopy,
not a model.

### 4a. Installability

| # | Lemma proved | Rule(s) |
| --- | --- | --- |
| 4.1 | The Delay's owner can install PauseGuard with `Guardable.setGuard`, and the Delay's `guard` slot then holds it. | `setGuardInstallsPauseGuard` |
| 4.2 | PauseGuard answers `supportsInterface` for `IGuard` (`0xe6d7a83a`) and ERC-165 (`0x01ffc9a7`) — the only thing `Guardable.setGuard` probes. | `pauseGuardAnswersIGuardInterfaceId` |

### 4b. Who may pause

| # | Lemma proved | Rule(s) |
| --- | --- | --- |
| 4.3 | Only the `pauser` can pause: every other caller reverts, and holding `ADMIN_ROLE` does not confer the right. | `pauseRevertsForAnyoneButThePauser`, `adminAloneCannotPause` |
| 4.4 | The `pauser` always can: from an unpaused state `pause()` succeeds and sets the flag. (Also the non-vacuity witness for 4.3.) | `pauseSucceedsForThePauser` |

### 4c. Who may unpause

| # | Lemma proved | Rule(s) |
| --- | --- | --- |
| 4.5 | Unpausing requires `ADMIN_ROLE`: callers without it revert, and being the `pauser` is not sufficient — the pause/unpause asymmetry the design depends on. | `unpauseRevertsWithoutAdminRole`, `pauserAloneCannotUnpause` |
| 4.6 | `ADMIN_ROLE` is sufficient: from a paused state the holder unpauses and the flag is cleared. (Also the non-vacuity witness for 4.5.) | `unpauseSucceedsForAdminRole` |
| 4.7 | No other entry point on either contract can move the `paused` flag. | `pausedOnlyChangesThroughPauseOrUnpause` (parametric) |

### 4d. Role and membership integrity

| # | Lemma proved | Rule(s) |
| --- | --- | --- |
| 4.8 | Replacing the pauser requires `ADMIN_ROLE`; a holder can do it, the new account is recorded, and the outgoing pauser is displaced (never two pausers at once). | `setPauserRevertsWithoutAdminRole`, `setPauserSetsThePauser` |
| 4.9 | `setPauser` is the only entry point that can change the `pauser`. | `pauserOnlyChangesThroughSetPauser` (parametric) |
| 4.10 | AccessControl's inherited `grantRole` and `revokeRole` are dead for every role and every caller, because `DEFAULT_ADMIN_ROLE` administers both roles and nobody holds it. | `inheritedGrantAndRevokeAlwaysRevert` |
| 4.11 | `renounceRole` is disabled, so no holder can drop a role — the last admin cannot strand the guard. | `renounceRoleAlwaysReverts` |
| 4.12 | `ADMIN_ROLE` membership is fixed at deployment: no entry point changes it. | `adminRoleNeverChanges` (parametric) |
| 4.13 | `DEFAULT_ADMIN_ROLE`, unheld in the pre-state, stays unheld — the induction step that freezes `ADMIN_ROLE`. (Base case is the constructor, which grants it to nobody; assumed, not proved.) | `defaultAdminRoleNeverGranted` (parametric) |
| 4.14 | The role-admin wiring cannot be re-pointed: `_setRoleAdmin` is never reached, so `getRoleAdmin` of both roles is invariant. | `roleAdminWiringNeverChanges` (parametric) |

### 4e. Pausing blocks execution

| # | Lemma proved | Rule(s) |
| --- | --- | --- |
| 4.15 | While PauseGuard is paused, `Delay.executeNextTx` reverts and nothing reaches the Delay's target, for any transaction arguments and any queue state — stated end to end, and again on the guard half called directly. | `pausedBlocksExecuteNextTx`, `checkTransactionRevertsWhilePaused` |
| 4.16 | The pause is reversible: after an `ADMIN_ROLE` holder unpauses, a queue entry can execute again, and the unpaused guard rejects nothing on its own — stated end to end, and again on the guard half called directly. | `unpauseReopensExecuteNextTx` (witness), `checkTransactionAcceptsWhileNotPaused` |
| 4.17 | The guard is what does the blocking: with no guard installed, `executeNextTx` forwards to the target with no check at all. | `withoutPauseGuardExecuteNextTxForwardsUnchecked` (witness) |

### 4f. A pause does not disarm the owner

| # | Lemma proved | Rule(s) |
| --- | --- | --- |
| 4.18 | While PauseGuard is installed **and paused**, the Delay's owner (the DelayOwnerSafe) can still call `setTxNonce` and the new nonce lands — `setTxNonce` is `onlyOwner`, never reaches `Module.exec`, and so never consults the guard. | `ownerCanSetTxNonceWhilePaused` |
| 4.19 | Both halves of the veto hold in the **same** state: with an entry queued and the guard paused, `executeNextTx` reverts with nothing reaching the target, *and* in that same state the owner can bump `txNonce` past the pending entry. A pause holds the queue without freezing the cancellation. | `pausedBlocksExecuteNextTxWhileOwnerCanStillSetTxNonce` |
| 4.20 | The other order: **after** the owner's `setTxNonce` succeeds during a pause, the pause is still standing (`setTxNonce` does not clear it) and `executeNextTx` still reverts with nothing reaching the target — with the queue left deliberately non-empty, so the revert is not the empty-queue check. Bumping `txNonce` is not a way to slip the next entry past a paused guard. | `executeNextTxStillBlockedAfterSetTxNonceDuringPause` |
| 4.21 | That block really is the pause: from the same bump-during-pause state, once the admin unpauses, an entry can execute. | `executeNextTxAfterSetTxNonceReopensOnUnpause` (witness) |

> Both routes in the scenario — the 9/9 Safe's own signed transaction, and
> `Governor → Roles → Module.exec → IAvatar(target).execTransactionFromModule` where `target`
> *is* the DelayOwnerSafe — arrive at `Delay.setTxNonce` as an ordinary external call whose
> `msg.sender` is `owner()`. The Delay cannot distinguish them, so `e.msg.sender == owner()`
> covers both. What happens upstream of the Safe on the second route is Property 1's scene;
> that a paused PauseGuard cannot interfere with it is immediate, since PauseGuard is installed
> on the Delay and SetTxNonceGuard on the Roles module, and neither reads the other's storage.
>
> On 4.20's "still fails **due to the pause**": `setTxNonce` moves `txNonce`, so a later
> `executeNextTx` could in principle revert on the empty-queue check
> ([`Delay.sol:206`](../certora/helpers/Delay.sol#L206)) rather than on the guard. 4.20
> requires `nonce < queueNonce()` — strict, where `setTxNonce` itself only needs `<=` — which
> leaves something still queued, and 4.21 exhibits that same state executing once unpaused.
> Together they pin the revert on the pause rather than on the state `setTxNonce` left behind.


---

## Property 5 — the Delay's module ring, owner and guard

Spec: `specs/Delay/moduleIntegrity.spec`. The scene is the real Delay mastercopy,
inherited unmodified by [`harness/DelayHarness.sol`](harness/DelayHarness.sol), which adds one
view getter and no logic. `target` is linked to
[`helpers/ReenteringAvatar.sol`](helpers/ReenteringAvatar.sol) rather than `DummyAvatar`.

This is the property covering the attack the integration exists to rule out: an unauthorized
party gets an address into the Delay's module ring, that address queues, and after the cooldown
anyone executes it against the avatar. Everything downstream — cooldown, veto, pause — is moot
once a hostile module is enabled, because the queue entry it writes is indistinguishable from a
legitimate one.

> **The claim that matters here is a composition, and neither half states it.** Property 1 proves
> that with both gates in place, the only call the Governor can make the DelayOwnerSafe emit is
> `Delay.setTxNonce`. Lemma 5.2 proves that the Delay's module ring moves only for `owner`, which
> is that same DelayOwnerSafe. Together — and only together — they give:
>
> **the Governor can never enable a module on the Delay.**
>
> Weakening either half gives that up silently, which is why it is written here rather than left
> to a reader to assemble.

| # | Lemma proved | Rule(s) |
| --- | --- | --- |
| 5.1 | `setUp` is spent: given a module ring that has been set up, the `public` and otherwise unmodified `setUp` ([`Delay.sol:76`](../certora/helpers/Delay.sol#L76)) always reverts. It is protected only by `__Ownable_init()`'s `initializer` ([`Delay.sol:87`](../certora/helpers/Delay.sol#L87)) and by `setupModules()` requiring an empty sentinel slot ([`Delay.sol:106`](../certora/helpers/Delay.sol#L106)); a second `setUp` would run `transferOwnership` **and** reset the ring, which is every bound below at once. | `setUpAlwaysRevertsAfterDeployment` |
| 5.2 | Over every state-changing entry point and every caller — `executeNextTx` included, whose avatar tries `enableModule` on the way through — the module ring moves only under `enableModule` or `disableModule`, and only for `owner`. **This is the formalization of the goal "no party other than the DelayOwnerSafe threshold can add a module to the Delay".** | `modulesOnlyChangeThroughOwnerEnableOrDisable` (parametric), `ownerCanEnableModule` (witness, reachability only — see below) |
| 5.3 | The second half of the same attack: only an address already in the ring can leave a queue entry behind. Over every entry point, both `queueNonce` and `txHash[n]` move only for a caller whose raw ring entry is non-zero — the predicate `moduleOnly` actually reads (`@gnosis.pm/zodiac` 1.0.1 `core/Modifier.sol:58-61`), not `isModuleEnabled`, which diverges at the self-linked sentinel. | `queueOnlyGrowsThroughEnabledModules` (parametric), `enabledModuleCanQueue` (witness) |
| 5.4 | Ownership cannot be seized, so 5.2 cannot be sidestepped by first becoming the owner: `owner` moves only through `transferOwnership` or `renounceOwnership`, and only for the current owner. | `ownerOnlyChangesThroughOwnableTransfer` (parametric) |
| 5.5 | The guard over execution is owner-only too, so nothing can detach PauseGuard on its way past. | `guardOnlyChangesThroughOwnerSetGuard` (parametric) |
| 5.6 | An execution is not a module grant. With an avatar that answers every forwarded queue entry by calling `enableModule` straight back on the Delay, `executeNextTx` completes and the attacker is still not in the ring: the return path's `msg.sender` is the avatar, not `owner`. | `executeNextTxCannotEnableModuleThroughTheAvatar`, `avatarEnableModuleAttemptIsReachable` (witness) |

> On 5.6's scene, and why it is not `DummyAvatar`. `DummyAvatar.execTransactionFromModule`
> returns `true` and calls nothing ([`DummyAvatar.sol:19`](../certora/helpers/DummyAvatar.sol#L19)) —
> deliberate for the specs it serves, but under it *every* claim about what the avatar's call can
> do back to the Delay holds vacuously. `ReenteringAvatar` tries `enableModule` on every forward
> and records that it tried, and `avatarEnableModuleAttemptIsReachable` is what shows the path was
> exercised rather than assumed away.
>
> The attempt is swallowed with `try`/`catch` and the avatar reports success regardless. Without
> that, the `enableModule` revert would propagate through `Module.exec` and roll the whole
> transaction back, leaving no post-state in which to observe that the attempt was made and
> refused — the same vacuity one layer down.

> **On `setUp`, and why 5.2–5.5 exclude it.** `setUp` is the one entry point that can legitimately
> rewrite the ring and the owner, so leaving it in `f` would make it a counterexample to every
> claim here. Pinning the pre-state instead — requiring the ring already set up — is worse than
> useless: in that state `setUp` *always* reverts, and a parametric `f(e, args)` without
> `@withrevert` prunes reverting paths, so the `setUp` instance passes with an unreachable body.
> Vacuous, not proved.
>
> So 5.2–5.5 filter `setUp` out of `f` and assume nothing about the pre-state, which makes them
> strictly stronger: they hold from any storage. 5.1 states the `setUp` case directly, as a revert
> claim where the revert is asserted rather than assumed away. The two together cover every entry
> point of the deployed contract. The witness rules and 5.6 still require the ring set up, because
> they are about behaviour in the deployed configuration rather than about every reachable state.
>
> **The one exception is 5.2's `target() != owner()`.** Its `msg.sender == owner` assertion reads the
> *outermost* caller, which is stronger than "only the owner can change the ring" and equivalent to it
> only while no nested caller can be the owner. With `target == owner`, `executeNextTx` forwards to an
> avatar that is itself the owner, its `enableModule` legitimately succeeds, and the ring moves under
> an outer caller who is not the owner — a counterexample to the assertion but not to the property.
> Ruling that wiring out is what makes the two readings coincide.

---

## Property 6 — Roles configuration integrity

Spec: `specs/Roles/configIntegrity.spec`.

Properties 1–3 all bound the Governor *given* a configuration, and every part of that
configuration is mutable storage. If the Governor could reach any of it, those bounds would hold
right up until the Governor chose to remove them. This property closes that loop.

| # | Lemma proved | Rule(s) |
| --- | --- | --- |
| 6.1 | `setUp` is spent: given a module ring that has been set up, `Roles.setUp` ([`Roles.sol:44`](../contracts/Roles.sol#L44)) always reverts. This is the lemma that **discharges** what the assumptions table below used to carry unproved for 1.1–1.3. | `setUpAlwaysRevertsAfterDeployment` |
| 6.2 | Over every state-changing entry point and every caller: if any of `guard`, `multisend`, `avatar`, `target`, `owner`, the module ring, `defaultRoles`, role membership or target clearance moved, the caller was `owner`. The Governor is an enabled module and never the owner, so **the Governor can never widen its own scope.** | `rolesConfigOnlyChangesThroughOwner` (parametric), `ownerCanStillReconfigure` (witness) |
| 6.3 | Ownership moves only through `transferOwnership` or `renounceOwnership`, and only for the current owner — so 6.2 cannot be sidestepped by first becoming the owner. | `ownerOnlyChangesThroughOwnableTransfer` (parametric) |

> 6.2 is the general form of 1.2. `governorSucceedsOnlyThroughRolesExecEntryPoints` says it for
> the Governor and for that scene's wiring; 6.2 says it for every caller and every piece of
> configuration at once, which is the form that survives someone later adding an entry point.
>
> 6.2 and 6.3 exclude `setUp` from `f` and assume nothing about the pre-state, for the reason
> spelled out under Property 5; 6.1 carries that entry point on its own.

---

## Explicitly not proved

Carried over from the "Deliberately NOT claimed" sections of each spec, so the table above
is not read as broader than it is.

| Not claimed | Where it would have gone |
| --- | --- |
| That either guard survives its own removal. `Roles.setGuard` and `Delay.setGuard` are `onlyOwner`; an owner calling `setGuard(0)` is outside the guard specs. Property 3 is what covers the Roles side of that world. | Properties 1, 2, 4 |
| That the `setTxNonce` which arrives is *accepted*. `Delay.setTxNonce` is `onlyOwner` and has its own `require`s; a rejection returns `success == false` through the Safe. Property 1 bounds what is attempted, not what lands. | Property 1 |
| Anything about the 9/9 Safe's own signed transactions. Both guards sit on module paths; Safe owners retain every power they had. | Properties 1, 2, 4 |
| That the Roles configuration stays as configured. Every `require` in Property 3 describes mutable storage the Roles owner can change in one call — that asymmetry with the immutable guard is the point, not an oversight. | Property 3 |
| Any `ExecutionOptions` other than `None` on the scoped function. Raising it to `Send` or `Both` would break the `value == 0` / `Operation.Call` halves, and the rules would fail — correctly. | Property 3 |
| Multisend batches of **two or more entries**. 3.2a covers one entry and says so; `loop_iter: 1` with `optimistic_loop` is what bounds it. Raising `loop_iter` extends it to bounded batch lengths, never to arbitrary ones. | Property 3 |
| Multisend blobs of **at most 100 bytes**. `checkMultisendTransaction`'s loop starts at `i = 100`, so such a blob never enters it: `check()` returns having verified role **membership only** — no target, function or parameter scoping — while the outer transaction still fires at `multisend()`. Open in the guard-less scene; the guard closes it (2.3). | Property 3 |
| Who holds PauseGuard's roles. Membership is unconstrained apart from the holder under test, so the rules hold for any admin and pauser, including Safes. | Property 4 |
| Anything about queueing on the Delay. `execTransactionFromModule` / `…ReturnData` never reach `Module.exec`. | Property 4 |
| That the DelayOwnerSafe's signed transactions are unguarded in general. Lemmas 4.18/4.19 hold because PauseGuard is installed on the **Delay**, via the Zodiac Modifier's `Guardable.setGuard`. If the same PauseGuard were *also* installed as the Safe's own transaction guard, a pause would block that route too — a deployment constraint the rules depend on, not one they prove. | Property 4 |
| That an entry skipped via `setTxNonce` can never execute later. 4.18/4.19 show `txNonce` moves; they say nothing about the hash check a later `executeNextTx` runs against the new `txNonce`. | Property 4 |
| Anything about branch 1 (Term DAO as the Delay's avatar). It is not in scene, so `Delay-owner Safe != Term DAO` is not proved. | Property 1 |
| Transactions whose `data` exceeds ~971 bytes on either Delay spec: `optimistic_hashing` with `hashing_length_bound 1024` bounds the hashed payload. | Properties 4, 5 |
| `compValues` entries longer than the same 1024-byte bound on Property 6's conf. `compressCompValue` hashes a symbolic-length `bytes calldata` ([`Permissions.sol:1080`](../contracts/Permissions.sol#L1080)), which is unbounded hashing; without `optimistic_hashing` the Prover leaves keccak injectivity unenforced and manufactures counterexamples in which a `role.compValues` slot aliases the `_owner` slot. Turning it on is what makes 6.2 and 6.3 provable at all — at the cost of assuming no hashed `compValue` exceeds 1024 bytes. | Property 6 |
| `scopeParameterAsOneOf` with `compValues.length != 2`. The function reverts below 2 ([`Permissions.sol:685`](../contracts/Permissions.sol#L685)) while `optimistic_loop` assumes the loop exited after `loop_iter` unrollings, so `loop_iter: 1` left every non-reverting path pruned and that instance of 6.2/6.3 **vacuous** — a sanity failure, not a pass. Property 6's conf therefore raises `loop_iter` to 2, which pins the length at exactly 2. Ownership and configuration ownership do not depend on the array's length, but the claim is bounded. | Property 6 |
| Who the Delay's owner is. `owner` is left unconstrained, so Property 5 holds for any owner. That it is the DelayOwnerSafe, and not something the Governor can reach, is a deployment fact checked in the verification plan. | Property 5 |
| That the owner will not enable a hostile module itself. A 5-of-11 quorum that wants to hand the Delay over can; 5.2 says only that nothing else can. | Property 5 |
| That the avatar can do no harm anywhere else. `ReenteringAvatar` models one return path — back into the Delay's own owner-only surface. What a real avatar does with the rest of a queue entry is the entry's business, and is what the cooldown is for. | Property 5 |
| That `enableModule` leaves the ring in the expected shape. 5.2's witness asserts only that the owner's call does not revert. The post-state is not observable in this scene: the Prover scalarizes the constant-key `modules[SENTINEL_MODULES]` that `Modifier`'s own code writes — visible in counterexamples as a scalar going `SENTINEL` → `m` across the call — while every getter reachable from CVL takes the key as a parameter and reads the storage wordmap, which never sees that write. Asserting the ring afterwards, via `isModuleEnabled`, via `moduleEntry`, or via a dedicated constant-key harness getter, fails on a model where `enableModule` reports success and the ring reads unchanged. The write demonstrably happens; the storage view cannot see it. Worth raising with Certora rather than working around further. | Property 5 |
| That the Delay's avatar is not also its owner. 5.2 and 5.6 both require `target() != owner()`: wire a Delay so that the contract it forwards to is the contract that owns it, and the return path arrives at `enableModule` with `msg.sender == owner`, so an execution really could enable a module. In the deployment those are the Ownerless Safe `0xb8A1dF43…aEC03` and the DelayOwnerSafe, two distinct addresses — a deployment constraint the rules depend on, checked in the verification plan, not proved here. | Property 5 |
| That `renounceOwnership` will not be called. It is on the mastercopy and cannot be removed — the Delay is a minimal proxy to immutable code. If the owner ever called it, `owner` would become zero and `enableModule`, `setGuard`, `setTxNonce`, `setTxCooldown` and `setTxExpiration` would be frozen for good. 5.4 and 6.3 admit it as an owner-only route; nothing here prevents it. | Properties 5, 6 |
| That the Roles configuration is *correct*. What the owner has configured is Property 3's subject; Property 6 says only that nobody else can move it. | Property 6 |
| That the Roles owner will not widen the Governor's scope itself. That owner is the Ownerless Safe, reachable only by queueing through the Delay — a 5-of-11 signature plus a 1-day cooldown, in the open. That asymmetry is the design, not something Property 6 establishes. | Property 6 |
| The Roles-side equivalent of 5.6. `target` is linked to `DummyAvatar` in Property 6's scene, which calls nothing, so the avatar's return path is not explored there. On that side the avatar is the DelayOwnerSafe, and what the Governor can make it emit is Property 1. | Property 6 |

## Assumptions read off source rather than checked by the Prover

| Assumption | Source | Used by |
| --- | --- | --- |
| `Module.exec` calls `IGuard(guard).checkTransaction(...)`, i.e. the address in the Delay's `guard` slot. | `@gnosis.pm/zodiac` 1.0.1 `core/Module.sol:43-77` | 4.15, 4.16 |
| `Module.exec` forwards to `IAvatar(target).execTransactionFromModule(...)`, so an avatar linked at `target` is on the path a queue entry actually takes. | same, `core/Module.sol:66-72` | 5.6 |
| That call is plain and external with no `try/catch`, so a revert inside `checkTransaction` reverts `executeNextTx`. | same | 4.15 |
| The Roles module has been set up, i.e. `moduleEntry(SENTINEL_MODULES()) == SENTINEL_MODULES()` on chain. The consequence that used to be read off source alongside it — *so `setUp` is not callable by anyone* — is now proved: 6.1 for Roles, 5.1 for the Delay. What remains assumed is only the deployment fact, which the verification plan checks. 5.2–5.5 and 6.2–6.3 no longer need it: they exclude `setUp` from `f` and hold from any pre-state. | `Roles.sol:56-59`, `Delay.sol:106-112` | 1.1–1.3, 5.1, 5.6, 6.1, and the witness rules of 5.2, 5.3 and 6.2 |
| PauseGuard's constructor grants `DEFAULT_ADMIN_ROLE` to nobody — the base case for 4.13. | `PauseGuard` constructor | 4.12, 4.13 |

---

## Reproducing

CI runs all six confs on every push ([`.github/workflows/formal-verification.yaml`](../../../.github/workflows/formal-verification.yaml)),
one matrix job per conf, with `--wait_for_results all` so a failing rule fails the build.

Locally, `certoraRun` takes **one** conf per invocation (it rejects multiple), and by default
submits without waiting. Prerequisites: `CERTORAKEY` exported, and solc 0.8.6 selected — the
confs pin no `solc` key, so they use whatever is on `PATH`:

```bash
pip3 install -r ../requirements.txt && solc-select install 0.8.6 && solc-select use 0.8.6
```

All four Roles rulesets, submitted back to back:

```bash
cd packages/evm && for c in Roles-setTxNonceGuardAndRoleConfig Roles-setTxNonceGuardSufficient Roles-setTxNonceRoleConfigSufficient Roles-configIntegrity; do certoraRun "./certora/confs/$c.conf" --msg "$c - $(git rev-parse --short HEAD)"; done
```

Both Delay rulesets:

```bash
cd packages/evm && for c in Delay-pauseGuardSufficient Delay-moduleIntegrity; do certoraRun "./certora/confs/$c.conf" --msg "$c - $(git rev-parse --short HEAD)"; done
```

A single lemma's rules, via `--rule` (space-separated list, wildcards allowed) — here 4.18–4.21:

```bash
cd packages/evm && certoraRun ./certora/confs/Delay-pauseGuardSufficient.conf --rule '*SetTxNonce*' --msg "section 7 - pause vs owner setTxNonce"
```

`rule_sanity: basic` is set inside all six confs, so it does not need passing on the command line. It is
what catches a rule that passes because its body is unreachable: a red **rule not vacuous** node is a
failure, however green the rule's own assertions look.
