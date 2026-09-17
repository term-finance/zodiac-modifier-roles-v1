# Certora proof inventory

One row per lemma. The lemma is the primary key; the value is the rule (or rules)
that establish it. Where several rules share a lemma they are alternative routes to
the same claim — a different entry point, a worse-case configuration, or the guard
half of an end-to-end statement — and the lemma is proved only if all of them verify.

**Status: 45 of 46 rules verify; `roleConfigLimitsSingleEntryMultisendToDelaySetTxNonce` (3.2a) is newly added and not yet run.** Rules marked *(witness)* are
`satisfy` rules discharging non-vacuity, not bounds. See [Reproducing](#reproducing) for
the commands, and [Explicitly not proved](#explicitly-not-proved) for what these results
do and do not cover.

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
| [`confs/Roles-setTxNonceGuardAndRoleConfig.conf`](confs/Roles-setTxNonceGuardAndRoleConfig.conf) | [`specs/Roles/setTxNonceGuardAndRoleConfig.spec`](specs/Roles/setTxNonceGuardAndRoleConfig.spec) | Roles + SetTxNonceGuard + setTxNonce role config (both gates) | 6 | 1.1–1.3 |
| [`confs/Roles-setTxNonceGuardSufficient.conf`](confs/Roles-setTxNonceGuardSufficient.conf) | [`specs/Roles/setTxNonceGuardSufficient.spec`](specs/Roles/setTxNonceGuardSufficient.spec) | Roles + SetTxNonceGuard, role configuration unconstrained | 7 | 2.1–2.4 |
| [`confs/Roles-setTxNonceRoleConfigSufficient.conf`](confs/Roles-setTxNonceRoleConfigSufficient.conf) | [`specs/Roles/setTxNonceRoleConfigSufficient.spec`](specs/Roles/setTxNonceRoleConfigSufficient.spec) | Roles + setTxNonce role config, `guard() == 0` | 7 | 3.1–3.3 |
| [`confs/Delay-pauseGuardSufficient.conf`](confs/Delay-pauseGuardSufficient.conf) | [`specs/Delay/pauseGuardSufficient.spec`](specs/Delay/pauseGuardSufficient.spec) | Delay + PauseGuard installed via `Guardable.setGuard` | 26 | 4.1–4.21 |
| | | **total** | **46** | **32** |

---

## Property 1 — SetTxNonceGuard *and* the setTxNonce role configuration

Spec: `specs/Roles/setTxNonceGuardAndRoleConfig.spec`

| # | Lemma proved | Rule(s) |
| --- | --- | --- |
| 1.1 | With both gates active, every call the Governor completes through the Roles module is `setTxNonce(uint256)` on the Delay, with `value == 0` and `Operation.Call` — on **all four** execution entry points. | `governorExecTransactionWithRoleLimitedToDelaySetTxNonce`, `governorExecTransactionFromModuleLimitedToDelaySetTxNonce`, `governorExecTransactionWithRoleReturnDataLimitedToDelaySetTxNonce`, `governorExecTransactionFromModuleReturnDataLimitedToDelaySetTxNonce` |
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
| Transactions whose `data` exceeds ~971 bytes on the Delay spec: `optimistic_hashing` with `hashing_length_bound 1024` bounds the hashed payload. | Property 4 |

## Assumptions read off source rather than checked by the Prover

| Assumption | Source | Used by |
| --- | --- | --- |
| `Module.exec` calls `IGuard(guard).checkTransaction(...)`, i.e. the address in the Delay's `guard` slot. | `@gnosis.pm/zodiac` 1.0.1 `core/Module.sol:43-77` | 4.15, 4.16 |
| That call is plain and external with no `try/catch`, so a revert inside `checkTransaction` reverts `executeNextTx`. | same | 4.15 |
| The Roles module has been set up (`moduleEntry(SENTINEL_MODULES()) == SENTINEL_MODULES()`), so `setUp` is not callable by anyone. | `Roles.sol:56-59` | 1.1, 1.2, 1.3 |
| PauseGuard's constructor grants `DEFAULT_ADMIN_ROLE` to nobody — the base case for 4.13. | `PauseGuard` constructor | 4.12, 4.13 |

---

## Reproducing

CI runs all four confs on every push ([`.github/workflows/formal-verification.yaml`](../../../.github/workflows/formal-verification.yaml)),
one matrix job per conf, with `--wait_for_results all` so a failing rule fails the build.

Locally, `certoraRun` takes **one** conf per invocation (it rejects multiple), and by default
submits without waiting. Prerequisites: `CERTORAKEY` exported, and solc 0.8.6 selected — the
confs pin no `solc` key, so they use whatever is on `PATH`:

```bash
pip3 install -r ../requirements.txt && solc-select install 0.8.6 && solc-select use 0.8.6
```

All three Roles rulesets, submitted back to back:

```bash
cd packages/evm && for c in Roles-setTxNonceGuardAndRoleConfig Roles-setTxNonceGuardSufficient Roles-setTxNonceRoleConfigSufficient; do certoraRun "./certora/confs/$c.conf" --msg "$c - $(git rev-parse --short HEAD)"; done
```

The Delay ruleset:

```bash
cd packages/evm && certoraRun ./certora/confs/Delay-pauseGuardSufficient.conf --msg "Delay PauseGuard - $(git rev-parse --short HEAD)"
```

A single lemma's rules, via `--rule` (space-separated list, wildcards allowed) — here 4.18–4.21:

```bash
cd packages/evm && certoraRun ./certora/confs/Delay-pauseGuardSufficient.conf --rule '*SetTxNonce*' --msg "section 7 - pause vs owner setTxNonce"
```

`rule_sanity: basic` is set inside all four confs, so it does not need passing on the command line.
