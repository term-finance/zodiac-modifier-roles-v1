# New Governance Plan — Ownerless Safe `0xb8A1dF43c1c88b13937C0c5CEBbAd15830cAeC03` — Target State

Expected storage state after the migration.

**Topology**

```
Branch 1   Proposer Safe 0xd5E12854A3Dba99deF295A7635D3Ba16427d2A28 (5/11)  --module-->  Delay 0x0C19d8A404079d71E5CA3e32fE3f758Ab543ACdf (+ PauseGuard)  --module-->  Ownerless Safe 0xb8A1dF43c1c88b13937C0c5CEBbAd15830cAeC03
Branch 2   Governor 0x2B715634134220ffeEE9458b4e34E41A41418607              --module-->  NewRoles (+ SetTxNonceGuard)  --target-->  DelayOwnerSafe (5/11)  --owner-->  Delay 0x0C19d8A404079d71E5CA3e32fE3f758Ab543ACdf

Pause      PauseSafe (1/10)                              --pause-->                  PauseGuard
           Admin Safe 0x73d1C7dc9CEb14660Cf1E9BB29F80ECF9E97D774  --unpause / setPauser-->    PauseGuard
```

**Existing contracts**

| Contract | Address | Target state |
|---|---|---|
| Ownerless Safe | `0xb8A1dF43c1c88b13937C0c5CEBbAd15830cAeC03` | kept — loses Roles as a module |
| Delay | `0x0C19d8A404079d71E5CA3e32fE3f758Ab543ACdf` | kept — new owner, new guard |
| Proposer Safe | `0xd5E12854A3Dba99deF295A7635D3Ba16427d2A28` | kept — **fallback handler cleared** |
| Roles | `0x405b47354CF06A25DE1DDb35EC65F03939E2e8D2` | **retired** — replaced by `NewRoles` |
| Governor (22 hr voting period) | `0x2B715634134220ffeEE9458b4e34E41A41418607` | kept as-is — reconnected to `NewRoles` |
| Admin Safe | `0x73d1C7dc9CEb14660Cf1E9BB29F80ECF9E97D774` | kept — becomes `PauseGuard` admin |

**Placeholders** — contracts that do not exist yet: `NewRoles`, `SetTxNonceGuard`, `DelayOwnerSafe`, `PauseGuard`, `PauseSafe`.

`SetTxNonceGuard` cannot be shared with the Term DAO plan: it holds its Delay as an immutable. `PauseGuard` has no per-Delay state, so one instance installed on two Delays would pause both together.

**Retired** — `0x405b47354CF06A25DE1DDb35EC65F03939E2e8D2` (old Roles) holds no role in the target state: it is removed from the Ownerless Safe's modules and is no longer the Delay's owner.

**Governor** — `0x2B715634134220ffeEE9458b4e34E41A41418607` is not replaced. It is currently disconnected from the old Roles as a precautionary measure and is re-enabled only on `NewRoles`.

Rows in **bold** change from current state.

---

## 1. Delay — `0x0C19d8A404079d71E5CA3e32fE3f758Ab543ACdf`

EIP-1167 proxy → mastercopy `0xd54895B1121A2eE3f37b502F507631FA1331BED6` (Delay v1.0.0/1.0.1, `@gnosis.pm/zodiac@1.0.1` + OZ-upgradeable 4.x) — the same mastercopy as the Term DAO Delay `0x80Ce5a0de8B1604e3122BEE73360dC3b987F891A`. Reused as-is; two slots change.

| Slot | Variable | Type | Declared in | Value |
|---|---|---|---|---|
| 0.0 | `_initialized` | bool | Initializable | `true` |
| 0.1 | `_initializing` | bool | Initializable | `false` |
| 1–50 | `__gap` | uint256[50] | ContextUpgradeable | zero |
| **51** | **`_owner`** | address | OwnableUpgradeable | **`DelayOwnerSafe`** ← was `0x405b47354CF06A25DE1DDb35EC65F03939E2e8D2` (old Roles) |
| 52–100 | `__gap` | uint256[49] | OwnableUpgradeable | zero |
| **101** | **`guard`** | address | Guardable | **`PauseGuard`** ← was `0x0` |
| 102 | `avatar` | address | Module | `0xb8A1dF43c1c88b13937C0c5CEBbAd15830cAeC03` (Ownerless Safe) — read by nothing |
| 103 | `target` | address | Module | `0xb8A1dF43c1c88b13937C0c5CEBbAd15830cAeC03` (Ownerless Safe) |
| 104 | `modules` | mapping(address⇒address) | Modifier | devops safe 0xd5E12854A3Dba99deF295A7635D3Ba16427d2A28 |
| 105 | `txCooldown` | uint256 | Delay | `86400` (1 day) |
| 106 | `txExpiration` | uint256 | Delay | `86400` (1 day) |
| 107 | `txNonce` | uint256 | Delay | `203` |
| 108 | `queueNonce` | uint256 | Delay | `203` → queue empty |
| 109 | `txHash` | mapping(uint256⇒bytes32) | Delay | 203 historical entries (below) |
| 110 | `txCreatedAt` | mapping(uint256⇒uint256) | Delay | 203 historical entries (below) |

`modules` (slot 104) — `0xd5E12854A3Dba99deF295A7635D3Ba16427d2A28`, i.e. the 5-of-11 proposer Safe (Safe v1.3.0) remains the sole enabled module.

Queue history — all 203 slots consumed (`txNonce == queueNonce`):

| n | txHash | txCreatedAt (UTC) |
|---|---|---|
| 0 | `0xc4f9d186684c46dc…` | 2023-11-07 03:13 |
| 0–202 | 199 distinct hashes; 4 hashes appear twice | 2 in 2023, 46 in 2024, 65 in 2025, 90 in 2026 |
| 202 | `0xdde740722404c666…` | 2026-08-25 15:20 |
| 203 | `0x0` | `0` — unwritten |

---

## 2. NewRoles — new address

Full deployment replacing `0x405b47354CF06A25DE1DDb35EC65F03939E2e8D2`. Term fork **without** `callTargetFunctionWithRole`, **with** the `execTransactionFromModule` / `execTransactionFromModuleReturnData` overrides. Permissions library linked at `0xA4af47637C32482820960f680b1e52a11c705087` (the library `0x405b47354CF06A25DE1DDb35EC65F03939E2e8D2` links; `Permissions.sol` is untouched, so the slot layout below is the standard Roles v1 layout).

| Slot | Variable | Type | Declared in | Value |
|---|---|---|---|---|
| 0.0 | `_initialized` | bool | Initializable | `true` |
| 0.1 | `_initializing` | bool | Initializable | `false` |
| 1–50 | `__gap` | uint256[50] | ContextUpgradeable | zero |
| 51 | `_owner` | address | OwnableUpgradeable | `0xb8A1dF43c1c88b13937C0c5CEBbAd15830cAeC03` (Ownerless Safe) |
| 52–100 | `__gap` | uint256[49] | OwnableUpgradeable | zero |
| 101 | `guard` | address | Guardable | `SetTxNonceGuard` |
| 102 | `avatar` | address | Module | `0xb8A1dF43c1c88b13937C0c5CEBbAd15830cAeC03` (Ownerless Safe) — read by nothing |
| 103 | `target` | address | Module | `DelayOwnerSafe` |
| 104 | `modules` | mapping(address⇒address) | Modifier | Governor 0x2B715634134220ffeEE9458b4e34E41A41418607 (22 hr vote period)|
| 105 | `multisend` | address | Roles | `MultiSendCallOnly` |
| 106 | `defaultRoles` | mapping(address⇒uint16) | Roles | Governor `0x2B715634134220ffeEE9458b4e34E41A41418607` ⇒ `1` |
| 107 | `roles` | mapping(uint16⇒Role) | Roles | role 1 only (below) |

`modules` (slot 104) — `0x2B715634134220ffeEE9458b4e34E41A41418607`, i.e. the existing Governor is the sole enabled module.

`roles[1]` — base `keccak256(abi.encode(uint16(1), uint256(107)))` = `0xa7756872…df15`:

| Field | Slot | Key | Value |
|---|---|---|---|
| `members` | base+0 | Governor `0x2B715634134220ffeEE9458b4e34E41A41418607` | `1` — member |
| `targets` | base+1 | Delay `0x0C19d8A404079d71E5CA3e32fE3f758Ab543ACdf` | `0x0000000000000000000000000000000000000000000000000000000000000002` → Clearance.Function (2), ExecutionOptions.None(0) |
| `functions` | base+2 | Delay ‖ `0x46ba2307` | `0x2000000000000000000000000000000000000000000000000000000000000000` → options None, wildcarded, length 0 |
| `compValues` | base+3 | Delay ‖ `0x46ba2307` ‖ `00` | `0x0` — none |
| `compValuesOneOf` | base+4 | same | length 0 — none |

Role 1 grants exactly one capability: `Delay.setTxNonce(uint256)` with no parameter constraint.

---

## 3. SetTxNonceGuard — new address

| Item | Value |
|---|---|
| Storage | **none** — the contract declares no state variables |
| `delay` | `0x0C19d8A404079d71E5CA3e32fE3f758Ab543ACdf` — `immutable`, held in bytecode, not storage |
| `supportsInterface(0xe6d7a83a)` | `true` — required by `Guardable.setGuard` |
| `supportsInterface(0x01ffc9a7)` | `true` |

---

## 4. DelayOwnerSafe — new 5/11 Safe

Safe v1.3.0, deployed against the **same singleton as the Ownerless Safe** `0xb8A1dF43c1c88b13937C0c5CEBbAd15830cAeC03` — copy that Safe's slot 0 verbatim rather than picking from a deployment list, since v1.3.0 ships two distinct singletons (`GnosisSafe` and `GnosisSafeL2`) at different addresses.

| Slot | Variable | Type | Declared in | Value |
|---|---|---|---|---|
| 0 | `singleton` | address | SafeStorage | `0xd9Db270c1B5E3Bd161E8c8503c55cEABeE709552` (`GnosisSafe` v1.3.0) — **identical to `0xb8A1dF43c1c88b13937C0c5CEBbAd15830cAeC03` slot 0** |
| 1 | `modules` | mapping(address⇒address) | SafeStorage | New Roles Modifier |
| 2 | `owners` | mapping(address⇒address) | SafeStorage | ring of 11 signers — the same set as the Proposer Safe (below) |
| 3 | `ownerCount` | uint256 | SafeStorage | `11` |
| 4 | `threshold` | uint256 | SafeStorage | `5` |
| 5 | `nonce` | uint256 | SafeStorage | `0` |
| 6 | `_deprecatedDomainSeparator` | bytes32 | SafeStorage | `0` |
| 7 | `signedMessages` | mapping(bytes32⇒uint256) | SafeStorage | empty |
| 8 | `approvedHashes` | mapping(address⇒mapping(bytes32⇒uint256)) | SafeStorage | empty |

### Signers

The same 11 signers as the Proposer Safe `0xd5E12854A3Dba99deF295A7635D3Ba16427d2A28`, in its owner-ring order, with threshold 5:

| # | Signer |
|---|---|
| 1 | `0xF6A745f9B38FFcd17Ee8909AC89151D788F95282` |
| 2 | `0xC43d527E3544A3d199Ce28E87994384D89d90e6E` |
| 3 | `0x8EF485fD38b7B29a827938C9F00300eaBf8E1710` |
| 4 | `0xbfFcAdCd5549cC378693108BcD4435776A6fa795` |
| 5 | `0xB680373c50E9E877DA7dCF9efcc0dFB234452ad3` |
| 6 | `0x6eb0c274EC4B1d51152e45BAED22f883B2A3Bc60` |
| 7 | `0xE82183cfAE1C24f044315c318FD97bE7e47b31D2` |
| 8 | `0xeee661edcFE634Dc0e29D62C26AfD62c0843b817` |
| 9 | `0xc1047a4D9f6071B55585523F7F659F39A1fBA74b` |
| 10 | `0xDB97c377F23a9Dc54c3D6F9df7bC0ca4Cf7D5A81` |
| 11 | `0x89562FC5AEF155481aE0C7dde1300110B4dF2F1D` |

As the Delay's owner, any 5 of the 11 signers can also call the Delay's owner functions directly (`setTxNonce`, `setTxCooldown`, `setTxExpiration`, `setGuard`, `enableModule`, `transferOwnership`, …) without going through the Governor.

---

## 5. Ownerless Safe — `0xb8A1dF43c1c88b13937C0c5CEBbAd15830cAeC03`

Safe v1.3.0. Remains the Delay's `avatar`/`target` and the owner of `NewRoles`. One slot changes: the old Roles is no longer an enabled module.

| Slot | Variable | Value |
|---|---|---|
| 0 | `singleton` | `0xd9Db270c1B5E3Bd161E8c8503c55cEABeE709552` (`GnosisSafe` v1.3.0) — the value `DelayOwnerSafe` must match |
| **1** | **`modules`** | 0x0C19d8A404079d71E5CA3e32fE3f758Ab543ACdf (Delay Module) |
| 3 | `ownerCount` | `9` |
| 4 | `threshold` | `9` |
| 5 | `nonce` | `16` at time of reading — advances with each migration transaction the Ownerless Safe signs |
| `keccak256("guard_manager.guard.address")` | guard | `0x0` |
| `keccak256("fallback_manager.handler.address")` | fallback handler | `0xf48f2B2d2a534e402487b3ee7C18c33Aec0Fe5e4` (CompatibilityFallbackHandler v1.3.0) |

---

## 6. Governor — `0x2B715634134220ffeEE9458b4e34E41A41418607`

Existing deployment, **not replaced**. OpenZeppelin Governor v5, non-upgradeable, 23,341 bytes. Currently disconnected from the old Roles; in the target state it is the sole module on `NewRoles`.

### Storage — ends at slot 7

| Slot | Variable | Type | Declared in | Value |
|---|---|---|---|---|
| 0 | `_nameFallback` | string | EIP712 | empty — name fits the ShortString immutable path |
| 1 | `_versionFallback` | string | EIP712 | empty |
| 2 | `_nonces` | mapping(address⇒uint256) | Nonces | mapping root |
| 3 | `_name` | string | Governor | `"TermFinanceGovernor"` (len 19, inline) |
| 4 | `_proposals` | mapping(uint256⇒ProposalCore) | Governor | 66 historical proposals — all `Defeated`, none executed |
| 5–6 | `_governanceCall` | Bytes32Deque | Governor | `_begin == _end == 0` — empty |
| 7 | `_proposalVotes` | mapping(uint256⇒ProposalVote) | GovernorCountingSimple | tallies for the 66 proposals (57 `VoteCast` events) |
| 8+ | — | — | — | unallocated; all read zero |

Proposal history carries over because the Governor is reused. Every one of the 66 proposals (blocks 22,325,147 → 25,833,073) reads `Defeated`, and a `Defeated` proposal can never become executable, so re-enabling the Governor on `NewRoles` exposes no leftover proposal.

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
| `votingPeriod()` | `79200` (22 hours) |
| `proposalThreshold()` | `1000e18` (1,000 TERM) |
| `quorumNumerator()` / `quorumDenominator()` | `1` / `100` |
| `quorum(past)` | `1e24` (1,000,000 TERM of for+abstain) |
| `COUNTING_MODE()` | `support=bravo&quorum=for,abstain` |
| `CLOCK_MODE()` / `clock()` | `mode=timestamp&from=default` / read-time timestamp |
| `timelock()` | absent — no timelock extension |
| `proposalNeedsQueuing(id)` | `false` |
| ETH / TERM balance | `0` / `0` |

### Proposal payload

| Field | Value |
|---|---|
| `target` | `NewRoles` |
| `value` | `0` |
| `calldata` | `execTransactionWithRole(0x0C19d8A404079d71E5CA3e32fE3f758Ab543ACdf, 0, setTxNonce(n), Call, 1, true)` |

### Veto timing

`votingDelay() == 0`, so voting opens at proposal creation and `state()` reaches `Succeeded` at creation + 22 hours. There is no timelock, so `execute()` is callable from that moment. The Delay's cooldown is 1 day from the moment a transaction is queued.

| Event | Time |
|---|---|
| Proposer Safe queues tx `n` in the Delay | `t0` |
| Veto proposal created | `tp` |
| Proposal executable | `tp + 79200` |
| Delay tx `n` executable by anyone (`executeNextTx`) | `t0 + 86400` |
| Delay tx `n` expires | `t0 + 172800` |

Execution window for the veto is `[tp + 22h, t0 + 24h)`, i.e. **two hours when `tp == t0`**. The window shrinks one-for-one with proposal-creation latency: a proposal raised 1 hour after the queueing has 1 hour, and one raised more than 2 hours late has none at all.

---

## 7. PauseGuard — new address

Installed on the **Delay** (slot 101). While paused, every `executeNextTx` reverts.

| Item | Value |
|---|---|
| `paused` | `false` at deployment |
| `pauser` | `PauseSafe` — replaced by `admin` via `setPauser` |
| `admin` | Admin Safe `0x73d1C7dc9CEb14660Cf1E9BB29F80ECF9E97D774` (existing) — no function changes it |
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

**Whole-queue hold.** The pause blocks the queue as a whole, not a single entry. A reverted `executeNextTx` rolls back its `txNonce++`, so the head entry stays at the head. Cooldown and expiration keep running while paused: `executeNextTx` rejects any entry past `t0 + 86400 + 86400` ("Transaction expired"), so an entry whose expiration passes during the pause can never execute.

| Ends the hold on entry `n` | Who | When | Result |
|---|---|---|---|
| `setTxNonce(n+1)` | Governor `0x2B715634134220ffeEE9458b4e34E41A41418607` via `NewRoles`, or `DelayOwnerSafe` (5/11) directly | any time before the entry executes — not blocked by the pause | entry `n` and every entry before it are skipped |
| `skipExpired()` | permissionless | after the entry expires, `t0 + 86400 + 86400` | expired entries are skipped |
| `unpause()` | `admin` | any time | every unexpired entry past its cooldown is executable by anyone again, immediately |

So a pause holds the queue for as long as it lasts; an entry still held when it expires (2 days from queueing) is dead, and one that has not expired can execute as soon as `admin` unpauses unless it is skipped first.

---

## 8. PauseSafe — new address, 1-of-10

Safe v1.3.0, deployed against the **same singleton as the other Safes** — `0xd9Db270c1B5E3Bd161E8c8503c55cEABeE709552` (`GnosisSafe` v1.3.0), copied from the Ownerless Safe's slot 0. Holds the **pauser** role on `PauseGuard`. Threshold 1, so any single signer can pause.

| Slot | Variable | Type | Declared in | Value |
|---|---|---|---|---|
| 0 | `singleton` | address | SafeStorage | `0xd9Db270c1B5E3Bd161E8c8503c55cEABeE709552` (`GnosisSafe` v1.3.0) — **identical to `0xb8A1dF43c1c88b13937C0c5CEBbAd15830cAeC03` slot 0** |
| 1 | `modules` | mapping(address⇒address) | SafeStorage | empty ring: `0x1 → 0x1` |
| 2 | `owners` | mapping(address⇒address) | SafeStorage | ring of 10 signers — the same set as the Admin Safe (below) |
| 3 | `ownerCount` | uint256 | SafeStorage | `10` |
| 4 | `threshold` | uint256 | SafeStorage | `1` |
| 5 | `nonce` | uint256 | SafeStorage | `0` |
| 6 | `_deprecatedDomainSeparator` | bytes32 | SafeStorage | `0` |
| 7 | `signedMessages` | mapping(bytes32⇒uint256) | SafeStorage | empty |
| 8 | `approvedHashes` | mapping(address⇒mapping(bytes32⇒uint256)) | SafeStorage | empty |

### Signers

The same 10 signers as the Admin Safe `0x73d1C7dc9CEb14660Cf1E9BB29F80ECF9E97D774` (itself Safe v1.3.0, 4-of-10), in its owner-ring order, but with threshold 1:

| # | Signer |
|---|---|
| 1 | `0xF6A745f9B38FFcd17Ee8909AC89151D788F95282` |
| 2 | `0x8EF485fD38b7B29a827938C9F00300eaBf8E1710` |
| 3 | `0xbfFcAdCd5549cC378693108BcD4435776A6fa795` |
| 4 | `0xB680373c50E9E877DA7dCF9efcc0dFB234452ad3` |
| 5 | `0x6eb0c274EC4B1d51152e45BAED22f883B2A3Bc60` |
| 6 | `0xE82183cfAE1C24f044315c318FD97bE7e47b31D2` |
| 7 | `0xeee661edcFE634Dc0e29D62C26AfD62c0843b817` |
| 8 | `0xc1047a4D9f6071B55585523F7F659F39A1fBA74b` |
| 9 | `0xDB97c377F23a9Dc54c3D6F9df7bC0ca4Cf7D5A81` |
| 10 | `0x89562FC5AEF155481aE0C7dde1300110B4dF2F1D` |

---

## 9. Proposer Safe — `0xd5E12854A3Dba99deF295A7635D3Ba16427d2A28`

Safe v1.3.0, 5-of-11. Remains the Delay's sole enabled module. One slot changes: the fallback handler is cleared.

| Slot | Variable | Value |
|---|---|---|
| 0 | `singleton` | `0xd9Db270c1B5E3Bd161E8c8503c55cEABeE709552` (`GnosisSafe` v1.3.0) |
| 1 | `modules` | empty ring: `0x1 → 0x1` |
| 3 | `ownerCount` | `11` |
| 4 | `threshold` | `5` |
| 5 | `nonce` | `164` at time of reading — advances with each transaction the Proposer Safe signs |
| `keccak256("guard_manager.guard.address")` | guard | `0x0` |
| **`keccak256("fallback_manager.handler.address")`** | **fallback handler** | **`0x0000000000000000000000000000000000000000`** ← was `0xf48f2B2d2a534e402487b3ee7C18c33Aec0Fe5e4` (CompatibilityFallbackHandler v1.3.0) |

Fallback handler slot: `0x6c9a6c4a39284e37ed1cf53d337577d14212a4870fb976a4366c693b939918d5`.

**Task.** The Proposer Safe executes a transaction to itself calling `setFallbackHandler(0x0000000000000000000000000000000000000000)` (5 of 11 signatures). It emits `ChangedFallbackHandler(0x0000000000000000000000000000000000000000)`.
