# New Governance Plan — Target State

Expected storage state after the migration.

**Topology**

```
Branch 1   Proposer Safe 0xe9dDBBD914063BC703D468e25d0B75148A480cC5  --module-->  Delay 0x80Ce5a0de8B1604e3122BEE73360dC3b987F891A (+ PauseGuard)  --module-->  Term DAO 0xA5Ca93f1fa4dBB6E8141f6Bb22d74a79E07Fa2A1
Branch 2   NewGovernor                --module-->  NewRoles (+ SetTxNonceGuard)  --target-->  DelayOwnerSafe (2/4)  --owner-->  Delay 0x80Ce5a0de8B1604e3122BEE73360dC3b987F891A

Pause      pauser  --pause-->                  PauseGuard
           admin   --unpause / setPauser-->    PauseGuard
```

**Placeholders** — contracts that do not exist yet: `NewRoles`, `SetTxNonceGuard`, `DelayOwnerSafe`, `NewGovernor`, `PauseGuard`.

**Retired** — `0xfCCD42fc5C46810F395adfB29739AFF402913dd3` (old Governor) and `0xF3BD578bDa56176Bbf8529B5C945193cF54DB1f5` (old Roles) hold no role in the target state.

Rows in **bold** change from current state.

---

## 1. Delay — `0x80Ce5a0de8B1604e3122BEE73360dC3b987F891A`

EIP-1167 proxy → mastercopy `0xd54895B1121A2eE3f37b502F507631FA1331BED6` (Delay v1.0.0/1.0.1, `@gnosis.pm/zodiac@1.0.1` + OZ-upgradeable 4.x). Reused as-is; two slots change.

| Slot | Variable | Type | Declared in | Value |
|---|---|---|---|---|
| 0.0 | `_initialized` | bool | Initializable | `true` |
| 0.1 | `_initializing` | bool | Initializable | `false` |
| 1–50 | `__gap` | uint256[50] | ContextUpgradeable | zero |
| **51** | **`_owner`** | address | OwnableUpgradeable | **`DelayOwnerSafe`** ← was `0xF3BD578bDa56176Bbf8529B5C945193cF54DB1f5` (old Roles module) |
| 52–100 | `__gap` | uint256[49] | OwnableUpgradeable | zero |
| **101** | **`guard`** | address | Guardable | **`PauseGuard`** ← was `0x0` |
| 102 | `avatar` | address | Module | `0xA5Ca93f1fa4dBB6E8141f6Bb22d74a79E07Fa2A1` (Term DAO) — read by nothing |
| 103 | `target` | address | Module | `0xA5Ca93f1fa4dBB6E8141f6Bb22d74a79E07Fa2A1` (Term DAO) |
| 104 | `modules` | mapping(address⇒address) | Modifier | `0xe9dDBBD914063BC703D468e25d0B75148A480cC5` |
| 105 | `txCooldown` | uint256 | Delay | `604800` (7 days) |
| 106 | `txExpiration` | uint256 | Delay | `172800` (2 days) |
| 107 | `txNonce` | uint256 | Delay | `8` |
| 108 | `queueNonce` | uint256 | Delay | `8` → queue empty |
| 109 | `txHash` | mapping(uint256⇒bytes32) | Delay | 8 historical entries (below) |
| 110 | `txCreatedAt` | mapping(uint256⇒uint256) | Delay | 8 historical entries (below) |

`modules` (slot 104) — `0xe9dDBBD914063BC703D468e25d0B75148A480cC5`, i.e. the 2-of-4 proposer Safe remains the sole enabled module.

Queue history — all 8 slots consumed (`txNonce == queueNonce`):

| n | txHash | txCreatedAt (UTC) |
|---|---|---|
| 0–5 | `0xca920c2ec5e98328…` ×6 | 2025-04-17 15:23 → 2025-04-22 00:32 |
| 6 | `0x120e9bce7cc8846d…` | 2026-08-27 20:10 |
| 7 | `0xa47f6208c028cb8f…` | 2026-08-27 20:10 |
| 8 | `0x0` | `0` — unwritten |

---

## 2. NewRoles — new address

Full deployment. Term fork **without** `callTargetFunctionWithRole`, **with** the `execTransactionFromModule` / `execTransactionFromModuleReturnData` overrides. Permissions library linked at `0xa3849D0da1511c51ee327827fF372c647fb8CFC3` (unchanged — `Permissions.sol` is untouched, so the slot layout below is identical to the current mod).

| Slot | Variable | Type | Declared in | Value |
|---|---|---|---|---|
| 0.0 | `_initialized` | bool | Initializable | `true` |
| 0.1 | `_initializing` | bool | Initializable | `false` |
| 1–50 | `__gap` | uint256[50] | ContextUpgradeable | zero |
| 51 | `_owner` | address | OwnableUpgradeable | `0xA5Ca93f1fa4dBB6E8141f6Bb22d74a79E07Fa2A1` (Term DAO) |
| 52–100 | `__gap` | uint256[49] | OwnableUpgradeable | zero |
| **101** | **`guard`** | address | Guardable | **`SetTxNonceGuard`** ← was `0x0` |
| 102 | `avatar` | address | Module | `0xA5Ca93f1fa4dBB6E8141f6Bb22d74a79E07Fa2A1` (Term DAO) — read by nothing |
| **103** | **`target`** | address | Module | **`DelayOwnerSafe`** ← was `0xA5Ca93f1fa4dBB6E8141f6Bb22d74a79E07Fa2A1` |
| **104** | **`modules`** | mapping(address⇒address) | Modifier | `NewGovernor` |
| **105** | **`multisend`** | address | Roles | **`MultiSendCallOnly`** ← was `0x0` |
| **106** | **`defaultRoles`** | mapping(address⇒uint16) | Roles | **`NewGovernor` ⇒ `1`** — live state in this build |
| 107 | `roles` | mapping(uint16⇒Role) | Roles | role 1 only (below) |

`modules` (slot 104) — `NewGovernor`, i.e. the new Governor is the sole enabled module.

`roles[1]` — base `keccak256(abi.encode(uint16(1), uint256(107)))` = `0xa7756872…df15`:

| Field | Slot | Key | Value |
|---|---|---|---|
| `members` | base+0 | `NewGovernor` | `1` — member |
| `targets` | base+1 | Delay `0x80Ce5a0de8B1604e3122BEE73360dC3b987F891A` | `0x02` → Clearance.Function, ExecutionOptions.None |
| `functions` | base+2 | Delay ‖ `0x46ba2307` | `0x2000…0` → options None, wildcarded, length 0 |
| `compValues` | base+3 | Delay ‖ `0x46ba2307` ‖ `00` | `0x0` — none |
| `compValuesOneOf` | base+4 | same | length 0 — none |

Role 1 grants exactly one capability: `Delay.setTxNonce(uint256)` with no parameter constraint.

---

## 3. SetTxNonceGuard — new address

| Item | Value |
|---|---|
| Storage | **none** — the contract declares no state variables |
| `delay` | `0x80Ce5a0de8B1604e3122BEE73360dC3b987F891A` — `immutable`, held in bytecode, not storage |
| `supportsInterface(0xe6d7a83a)` | `true` — required by `Guardable.setGuard` |
| `supportsInterface(0x01ffc9a7)` | `true` |

---

## 4. DelayOwnerSafe — new 2/4 Safe

Safe v1.4.1, deployed against the **same singleton as the Term DAO** `0xA5Ca93f1fa4dBB6E8141f6Bb22d74a79E07Fa2A1` — copy that Safe's slot 0 verbatim rather than picking from a deployment list, since v1.4.1 ships two distinct singletons (`Safe` and `SafeL2`) at different addresses.

| Slot | Variable | Type | Declared in | Value |
|---|---|---|---|---|
| 0 | `singleton` | address | SafeStorage | Safe v1.4.1 mastercopy — **identical to `0xA5Ca93f1fa4dBB6E8141f6Bb22d74a79E07Fa2A1` slot 0** |
| 1 | `modules` | mapping(address⇒address) | SafeStorage | `NewRoles` |
| 2 | `owners` | mapping(address⇒address) | SafeStorage | 4 signers — the same set as the Proposer Safe (below) |
| 3 | `ownerCount` | uint256 | SafeStorage | `4` |
| 4 | `threshold` | uint256 | SafeStorage | `2` |
| 5 | `nonce` | uint256 | SafeStorage | `0` |
| 6 | `_deprecatedDomainSeparator` | bytes32 | SafeStorage | `0` |
| 7 | `signedMessages` | mapping(bytes32⇒uint256) | SafeStorage | empty |
| 8 | `approvedHashes` | mapping(address⇒mapping(bytes32⇒uint256)) | SafeStorage | empty |

### Signers

The same 4 signers as the Proposer Safe `0xe9dDBBD914063BC703D468e25d0B75148A480cC5` — the Delay's enabled module — in its owner-ring order, with the same threshold of 2:

| # | Signer |
|---|---|
| 1 | `0x12c624C8BB9EAb191055f8f11Fb3C02c04c52c07` |
| 2 | `0x39060471dE4Da1e9f0ebbd3ADf36B905a830d248` |
| 3 | `0x98E061AC25B5ccE88bf315C52f488fD7Ca46dd19` |
| 4 | `0x3dfcB8CA9D086fD90e949743F06199dB5aBDD102` |

---

## 5. Term DAO — `0xA5Ca93f1fa4dBB6E8141f6Bb22d74a79E07Fa2A1`

Unchanged. Remains the Delay's `avatar`/`target` and the owner of `NewRoles`.

| Slot | Variable | Value |
|---|---|---|
| 0 | `singleton` | Safe v1.4.1 mastercopy — the value `DelayOwnerSafe` must match |
| 1 | `modules` | contains Delay `0x80Ce5a0de8B1604e3122BEE73360dC3b987F891A` — unchanged |
| 3 | `ownerCount` | not inspected |
| 4 | `threshold` | not inspected |

---

## 6. NewGovernor — new address

Fresh deployment. OpenZeppelin Governor v5.0.2, non-upgradeable, ~23,342 bytes. Identical to `0xfCCD42fc5C46810F395adfB29739AFF402913dd3` in every respect except `votingPeriod`, which drops from 7 days to 5. A redeploy is the only way to change it: `GovernorSettings` is not inherited, so `votingPeriod` is a constant override compiled into bytecode with no setter.

All mappings are empty at deploy — no proposal, vote or nonce history carries over from the old Governor.

### Storage — ends at slot 7

| Slot | Variable | Type | Declared in | Value |
|---|---|---|---|---|
| 0 | `_nameFallback` | string | EIP712 | empty — name fits the ShortString immutable path |
| 1 | `_versionFallback` | string | EIP712 | empty |
| 2 | `_nonces` | mapping(address⇒uint256) | Nonces | mapping root — empty |
| 3 | `_name` | string | Governor | `"TermFinanceGovernor"` (len 19, inline) |
| 4 | `_proposals` | mapping(uint256⇒ProposalCore) | Governor | mapping root — empty |
| 5–6 | `_governanceCall` | Bytes32Deque | Governor | `_begin == _end == 0` — empty |
| 7 | `_proposalVotes` | mapping(uint256⇒ProposalVote) | GovernorCountingSimple | mapping root — empty |
| 8+ | — | — | — | unallocated; all read zero |

### Not in storage

| Value | Where |
|---|---|
| `_token = 0xC3d21f79C3120A4fFda7A535f8005a7c297799bF` (TERM) | immutable in GovernorVotes |
| `_cachedDomainSeparator`, `_cachedChainId`, `_hashedName`, `_hashedVersion`, `_name`, `_version` | immutable in EIP712 |
| `votingDelay`, `votingPeriod`, `proposalThreshold`, `quorumNumerator`, `quorumDenominator` | constant overrides in bytecode — GovernorSettings and GovernorVotesQuorumFraction are not inherited |

### Effective configuration

| Parameter | Value |
|---|---|
| `votingDelay()` | `0` |
| **`votingPeriod()`** | **`432000` (5 days)** ← was `604800` (7 days) |
| `proposalThreshold()` | `1000e18` (1,000 TERM) |
| `quorumNumerator()` / `quorumDenominator()` | `1` / `100` |
| `quorum(past)` | `1e24` (1,000,000 TERM of for+abstain) |
| `COUNTING_MODE()` | `support=bravo&quorum=for,abstain` |
| `CLOCK_MODE()` / `clock()` | `mode=timestamp&from=default` / read-time timestamp |
| `timelock()` | absent — no timelock extension |
| ETH / TERM balance | `0` / `0` |

### Proposal payload

| Field | Value |
|---|---|
| `target` | `NewRoles` |
| `value` | `0` |
| `calldata` | `execTransactionWithRole(0x80Ce5a0de8B1604e3122BEE73360dC3b987F891A, 0, setTxNonce(n), Call, 1, true)` |

### Veto timing

`votingDelay() == 0`, so voting opens at proposal creation and `state()` reaches `Succeeded` at creation + 5 days. There is no timelock, so `execute()` is callable from that moment. The Delay's cooldown is 7 days from the moment a transaction is queued.

| Event | Time |
|---|---|
| Proposer Safe queues tx `n` in the Delay | `t0` |
| Veto proposal created | `tp` |
| Proposal executable | `tp + 432000` |
| Delay tx `n` executable by anyone (`executeNextTx`) | `t0 + 604800` |
| Delay tx `n` expires | `t0 + 777600` |

Execution window for the veto is `[tp + 5d, t0 + 7d)`, i.e. **two days when `tp == t0`**. The window shrinks one-for-one with proposal-creation latency: a proposal raised 6 hours after the queueing has 42 hours, and one raised more than 48 hours late has none at all.

---

## 7. PauseGuard — new address

Installed on the **Delay** (slot 101). While paused, every `executeNextTx` reverts.

| Item | Value |
|---|---|
| `paused` | `false` at deployment |
| `pauser` | holder of the pauser role — to be specified; replaced by `admin` via `setPauser` |
| `admin` | holder of the admin role — to be specified; no function changes it |
| `supportsInterface(0xe6d7a83a)` | `true` — required by `Guardable.setGuard` |
| `supportsInterface(0x01ffc9a7)` | `true` |

Storage layout is whatever you implement; the three values above are the required state.

| Function | Callable by | Effect |
|---|---|---|
| `pause()` | `pauser` | `paused = true` |
| `unpause()` | `admin` | `paused = false` |
| `setPauser(address)` | `admin` | replaces `pauser` |
| `checkTransaction(…)` | the Delay, from `executeNextTx` | reverts while `paused` |
| `checkAfterExecution(…)` | the Delay, from `executeNextTx` | no-op |

**Scope.** `executeNextTx` is the only Delay entry point that reaches `Module.exec`, so this guard sees executions and never queueing — `execTransactionFromModule` and `execTransactionFromModuleReturnData` write the queue and return without calling `exec`. Queueing therefore stays open while paused. The Delay's owner functions (`setTxNonce`, `setGuard`, `setTxCooldown`, …) do not go through `exec` either, so the pause does not block them.

**Whole-queue hold.** The pause blocks the queue as a whole, not a single entry. A reverted `executeNextTx` rolls back its `txNonce++`, so the head entry stays at the head. Cooldown and expiration keep running while paused: `executeNextTx` rejects any entry past `t0 + 604800 + 172800` ("Transaction expired"), so an entry whose expiration passes during the pause can never execute.

| Ends the hold on entry `n` | Who | When | Result |
|---|---|---|---|
| `setTxNonce(n+1)` | `NewGovernor` via `NewRoles`, or `DelayOwnerSafe` (2/4) directly | any time before the entry executes — not blocked by the pause | entry `n` and every entry before it are skipped |
| `skipExpired()` | permissionless | after the entry expires, `t0 + 604800 + 172800` | expired entries are skipped |
| `unpause()` | `admin` | any time | every unexpired entry past its cooldown is executable by anyone again, immediately |

So a pause holds the queue for as long as it lasts; an entry still held when it expires (9 days from queueing) is dead, and one that has not expired can execute as soon as `admin` unpauses unless it is skipped first.

---

## 8. Proposer Safe — `0xe9dDBBD914063BC703D468e25d0B75148A480cC5`

Safe v1.4.1, 2-of-4. Remains the Delay's sole enabled module. One slot changes: the fallback handler is cleared.

| Slot | Variable | Value |
|---|---|---|
| 0 | `singleton` | `0x41675C099F32341bf84BFc5382aF534df5C7461a` (`Safe` v1.4.1) |
| 1 | `modules` | empty ring: `0x1 → 0x1` |
| 3 | `ownerCount` | `4` |
| 4 | `threshold` | `2` |
| 5 | `nonce` | `7` at time of reading — advances with each transaction the Proposer Safe signs |
| `keccak256("guard_manager.guard.address")` | guard | `0x0` |
| **`keccak256("fallback_manager.handler.address")`** | **fallback handler** | **`0x0000000000000000000000000000000000000000`** ← was `0xfd0732Dc9E303f09fCEf3a7388Ad10A83459Ec99` (CompatibilityFallbackHandler v1.4.1) |

Fallback handler slot: `0x6c9a6c4a39284e37ed1cf53d337577d14212a4870fb976a4366c693b939918d5`.

**Task.** The Proposer Safe executes a transaction to itself calling `setFallbackHandler(0x0000000000000000000000000000000000000000)` (2 of 4 signatures). It emits `ChangedFallbackHandler(0x0000000000000000000000000000000000000000)`.

