# New Governance Plan — Ownerless Safe `0xb8A1dF43c1c88b13937C0c5CEBbAd15830cAeC03` — Target State

Expected storage state after the migration.

**Topology**

```
Branch 1   Proposer Safe 0xd5E12854A3Dba99deF295A7635D3Ba16427d2A28 (5/11)  --module-->  Delay 0x0C19d8A404079d71E5CA3e32fE3f758Ab543ACdf (+ PauseGuard 0x3A70244c0fEc95B5Dd238dfa60DAbDB60a99f618)  --module-->  Ownerless Safe 0xb8A1dF43c1c88b13937C0c5CEBbAd15830cAeC03
Branch 2   Governor 0x2B715634134220ffeEE9458b4e34E41A41418607              --module-->  NewRoles 0xaBAC51B6AEb05a2CE65310F79e64DF203D6c8Ab3 (+ SetTxNonceGuard 0x7aE03372ECDcEe335CdEfB7d354d507F0506616C)  --target-->  DelayOwnerSafe 0x2a875746D0c88EBD2bbBfc8F8a773c58c3373ad3 (5/11)  --owner-->  Delay 0x0C19d8A404079d71E5CA3e32fE3f758Ab543ACdf

Pause      PauseSafe 0x74f3F3dEfdC563bbFC8637BaB2d30596D2817472 (2/9)  --pause-->                  PauseGuard 0x3A70244c0fEc95B5Dd238dfa60DAbDB60a99f618
           Admin Safe 0x73d1C7dc9CEb14660Cf1E9BB29F80ECF9E97D774        --unpause / setPauser-->    PauseGuard 0x3A70244c0fEc95B5Dd238dfa60DAbDB60a99f618
```

**Existing contracts**

| Contract | Address | Target state |
|---|---|---|
| Ownerless Safe | `0xb8A1dF43c1c88b13937C0c5CEBbAd15830cAeC03` | kept on Safe v1.3.0 — loses Roles as a module |
| Delay | `0x0C19d8A404079d71E5CA3e32fE3f758Ab543ACdf` | kept — new owner, new guard |
| Proposer Safe | `0xd5E12854A3Dba99deF295A7635D3Ba16427d2A28` | kept — **fallback handler cleared** |
| Roles | `0x405b47354CF06A25DE1DDb35EC65F03939E2e8D2` | **retired** — replaced by `NewRoles` |
| Governor (22 hr voting period) | `0x2B715634134220ffeEE9458b4e34E41A41418607` | kept as-is — reconnected to `NewRoles` |
| Admin Safe | `0x73d1C7dc9CEb14660Cf1E9BB29F80ECF9E97D774` | kept — becomes `PauseGuard` admin |
| PauseSafe | `0x74f3F3dEfdC563bbFC8637BaB2d30596D2817472` | **deployed 2026-09-21** — becomes `PauseGuard` pauser |
| DelayOwnerSafe | `0x2a875746D0c88EBD2bbBfc8F8a773c58c3373ad3` | **deployed 2026-09-21** — becomes the Delay's owner and NewRoles' target |

**Placeholders** — none. `NewRoles` (section 2), `SetTxNonceGuard` (section 3), `DelayOwnerSafe` (section 4), `PauseGuard` (section 7) and `PauseSafe` (section 8) are all deployed.

**Safe versions** — the three existing Safes stay on v1.3.0 (`GnosisSafe` `0xd9Db270c1B5E3Bd161E8c8503c55cEABeE709552`); the two new ones, `DelayOwnerSafe` and `PauseSafe`, both deployed 2026-09-21, are on v1.4.1 (`Safe` `0x41675C099F32341bf84BFc5382aF534df5C7461a`). Nothing in the topology crosses a version boundary in a way that matters: the Delay and NewRoles reach a Safe only through `execTransactionFromModule`, whose interface and behaviour are identical in both, and no Safe here validates EIP-1271 signatures, which is where v1.4.1 tightened the rules (`GS027`).

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
| **51** | **`_owner`** | address | OwnableUpgradeable | **`DelayOwnerSafe (0x2a875746D0c88EBD2bbBfc8F8a773c58c3373ad3)`** ← was `0x405b47354CF06A25DE1DDb35EC65F03939E2e8D2` (old Roles) |
| 52–100 | `__gap` | uint256[49] | OwnableUpgradeable | zero |
| **101** | **`guard`** | address | Guardable | **`PauseGuard (0x3A70244c0fEc95B5Dd238dfa60DAbDB60a99f618)`** ← was `0x0` |
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

## 2. NewRoles — `0xaBAC51B6AEb05a2CE65310F79e64DF203D6c8Ab3` — DEPLOYED

Section D of the verification plan passes 19/19 against it. The fork-only permission test also passes: `setTxNonce` is allowed through role 1 and the default role, and `setTxCooldown`, a delegatecall and a non-member caller are all rejected.

Replaces `0x405b47354CF06A25DE1DDb35EC65F03939E2e8D2`. Deploys a EIP-1167 proxy against Gnosis Guild's audited Roles v1.0.0 mastercopy `0x85388a8cd772b19a468F982Dc264C238856939C9`, with its audited `Permissions` library `0x543D1DE69b25420685Ef723842D0087d9b731B06`. Standard Roles v1 slot layout.

| Slot | Variable | Type | Declared in | Value |
|---|---|---|---|---|
| 0.0 | `_initialized` | bool | Initializable | `true` |
| 0.1 | `_initializing` | bool | Initializable | `false` |
| 1–50 | `__gap` | uint256[50] | ContextUpgradeable | zero |
| 51 | `_owner` | address | OwnableUpgradeable | `0xb8A1dF43c1c88b13937C0c5CEBbAd15830cAeC03` (Ownerless Safe) |
| 52–100 | `__gap` | uint256[49] | OwnableUpgradeable | zero |
| 101 | `guard` | address | Guardable | `SetTxNonceGuard (0x7aE03372ECDcEe335CdEfB7d354d507F0506616C)` |
| 102 | `avatar` | address | Module | `0xb8A1dF43c1c88b13937C0c5CEBbAd15830cAeC03` (Ownerless Safe) — read by nothing |
| 103 | `target` | address | Module | `DelayOwnerSafe` `0x2a875746D0c88EBD2bbBfc8F8a773c58c3373ad3` |
| 104 | `modules` | mapping(address⇒address) | Modifier | Governor 0x2B715634134220ffeEE9458b4e34E41A41418607 (22 hr vote period)|
| 105 | `multisend` | address | Roles | `MultiSendCallOnly` v1.4.1 `0x9641d764fc13c8B624c04430C7356C1C7C8102e2` |
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

## 3. SetTxNonceGuard — `0x7aE03372ECDcEe335CdEfB7d354d507F0506616C` — DEPLOYED

Source verified on Etherscan. Section C of the verification plan passes 3/3 against it.

| Item | Value |
|---|---|
| Storage | **none** — the contract declares no state variables |
| `delay` | `0x0C19d8A404079d71E5CA3e32fE3f758Ab543ACdf` — `immutable`, held in bytecode, not storage |
| `supportsInterface(0xe6d7a83a)` | `true` — required by `Guardable.setGuard` |
| `supportsInterface(0x01ffc9a7)` | `true` |

---

## 4. DelayOwnerSafe — `0x2a875746D0c88EBD2bbBfc8F8a773c58c3373ad3` — DEPLOYED

Safe **v1.4.1** on the canonical L1 `Safe` singleton, one version ahead of the Ownerless Safe. Owns the Delay and is the target of `NewRoles`.

Deployed 2026-09-21 by `0xeee661ed…` through the v1.4.1 `SafeProxyFactory` `0x4e1DCf7AD4e460CfD30791CCC4F9c8a4f820ec67` with `createProxyWithNonce`, in transaction `0x54b897e162dfbe00cb00296a7cd22368ecc23cfa1224a0abe3776963b51b772e`. Every row below was read back from chain and matches, except `modules`, which is empty until NewRoles is deployed and enabled.

As with the PauseSafe, the `setup` call carried `to = 0xBD89A1CE4DDe368FFAB0eC35506eEcE0b1fFdc54` (`SafeToL2Setup`) with `setupToL2(0x29fcB43b…)`. That library rewrites slot 0 only when `chainId() != 1`, so on mainnet it did nothing and slot 0 holds the L1 singleton. `paymentReceiver` is the Safe UI marker `0x5afe7A11E7000000000000000000000000000000`, with `payment` and `paymentToken` both zero.

| Slot | Variable | Type | Declared in | Value |
|---|---|---|---|---|
| 0 | `singleton` | address | SafeStorage | `0x41675C099F32341bf84BFc5382aF534df5C7461a` (`Safe` v1.4.1) — verified, not `SafeL2` `0x29fcB43b…` |
| 1 | `modules` | mapping(address⇒address) | SafeStorage | ring of 1: `0x1 → NewRoles (0xaBAC51B6AEb05a2CE65310F79e64DF203D6c8Ab3) → 0x1` — **empty today**, enabled by setup step 5 |
| 2 | `owners` | mapping(address⇒address) | SafeStorage | ring of 11 signers, all EOAs — the same set as the Proposer Safe (below) |
| 3 | `ownerCount` | uint256 | SafeStorage | `11` — verified |
| 4 | `threshold` | uint256 | SafeStorage | `5` — verified |
| 5 | `nonce` | uint256 | SafeStorage | `0` — nothing executed yet |
| 6 | `_deprecatedDomainSeparator` | bytes32 | SafeStorage | `0` — verified |
| 7 | `signedMessages` | mapping(bytes32⇒uint256) | SafeStorage | empty |
| 8 | `approvedHashes` | mapping(address⇒mapping(bytes32⇒uint256)) | SafeStorage | empty |
| `keccak256("guard_manager.guard.address")` | guard | address | GuardManager | `0x0` — verified |
| `keccak256("fallback_manager.handler.address")` | fallback handler | address | FallbackManager | `0xfd0732Dc9E303f09fCEf3a7388Ad10A83459Ec99` (CompatibilityFallbackHandler v1.4.1) |

### Signers

The same 11 signers as the Proposer Safe `0xd5E12854A3Dba99deF295A7635D3Ba16427d2A28`, verified set-for-set against it, with threshold 5. Listed in the deployed ring order, which starts with the deployer `0xeee661ed…` and so runs one place behind the Proposer Safe's order for signers 1–8; ring order carries no meaning beyond the `prevOwner` argument when removing an owner.

| # | Signer |
|---|---|
| 1 | `0xeee661edcFE634Dc0e29D62C26AfD62c0843b817` — deployed the Safe |
| 2 | `0xF6A745f9B38FFcd17Ee8909AC89151D788F95282` |
| 3 | `0xC43d527E3544A3d199Ce28E87994384D89d90e6E` |
| 4 | `0x8EF485fD38b7B29a827938C9F00300eaBf8E1710` |
| 5 | `0xbfFcAdCd5549cC378693108BcD4435776A6fa795` |
| 6 | `0xB680373c50E9E877DA7dCF9efcc0dFB234452ad3` |
| 7 | `0x6eb0c274EC4B1d51152e45BAED22f883B2A3Bc60` |
| 8 | `0xE82183cfAE1C24f044315c318FD97bE7e47b31D2` |
| 9 | `0xc1047a4D9f6071B55585523F7F659F39A1fBA74b` |
| 10 | `0xDB97c377F23a9Dc54c3D6F9df7bC0ca4Cf7D5A81` |
| 11 | `0x89562FC5AEF155481aE0C7dde1300110B4dF2F1D` |

As the Delay's owner, any 5 of the 11 signers can also call the Delay's owner functions directly (`setTxNonce`, `setTxCooldown`, `setTxExpiration`, `setGuard`, `enableModule`, `transferOwnership`, …) without going through the Governor.

---

## 5. Ownerless Safe — `0xb8A1dF43c1c88b13937C0c5CEBbAd15830cAeC03`

Safe v1.3.0. Remains the Delay's `avatar`/`target` and the owner of `NewRoles`. One slot changes: the old Roles is no longer an enabled module.

| Slot | Variable | Value |
|---|---|---|
| 0 | `singleton` | `0xd9Db270c1B5E3Bd161E8c8503c55cEABeE709552` (`GnosisSafe` v1.3.0) — `DelayOwnerSafe` and `PauseSafe` deliberately differ: they deploy on v1.4.1 |
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
| `target` | `NewRoles` `0xaBAC51B6AEb05a2CE65310F79e64DF203D6c8Ab3` |
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

## 7. PauseGuard — `0x3A70244c0fEc95B5Dd238dfa60DAbDB60a99f618` — DEPLOYED

Section B of the verification plan passes 9/9 against it. Installed on the **Delay** (slot 101). While paused, every `executeNextTx` reverts.

| Item | Value |
|---|---|
| `paused` | `false` at deployment |
| `pauser` | `PauseSafe (0x74f3F3dEfdC563bbFC8637BaB2d30596D2817472)` — replaced by `admin` via `setPauser` |
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

## 8. PauseSafe — `0x74f3F3dEfdC563bbFC8637BaB2d30596D2817472` — DEPLOYED

Safe **v1.4.1** on the canonical L1 `Safe` singleton, the same version as `DelayOwnerSafe` and one ahead of the Ownerless Safe. Holds the **pauser** role on `PauseGuard`. Threshold 2, so pausing takes two of the nine signers.

Deployed 2026-09-21 by `0xeee661ed…` through the v1.4.1 `SafeProxyFactory` `0x4e1DCf7AD4e460CfD30791CCC4F9c8a4f820ec67` with `createProxyWithNonce`, in transaction `0x3d010efe1825c373a39c1ca54e41f003db418dda6a3a1caa9b442799f5e04e08`. Every row below was read back from chain and matches.

The `setup` call carried `to = 0xBD89A1CE4DDe368FFAB0eC35506eEcE0b1fFdc54` (`SafeToL2Setup`) with `setupToL2(0x29fcB43b…)`, which is what the Safe UI sends. That library rewrites slot 0 to the `SafeL2` singleton **only when `chainId() != 1`**, so on mainnet it did nothing and slot 0 holds the L1 singleton, as required. Deploying the same way on any other chain would land on `SafeL2`. `setup` also recorded `paymentReceiver = 0x5afe7A11E7000000000000000000000000000000`, a Safe UI marker; with `payment` and `paymentToken` both zero, no payment was made.

| Slot | Variable | Type | Declared in | Value |
|---|---|---|---|---|
| 0 | `singleton` | address | SafeStorage | `0x41675C099F32341bf84BFc5382aF534df5C7461a` (`Safe` v1.4.1) — verified, not `SafeL2` `0x29fcB43b…` |
| 1 | `modules` | mapping(address⇒address) | SafeStorage | empty ring: `0x1 → 0x1` — verified |
| 2 | `owners` | mapping(address⇒address) | SafeStorage | ring of 9 signers, all EOAs — 8 drawn from the Admin Safe plus one that is not (below) |
| 3 | `ownerCount` | uint256 | SafeStorage | `9` — verified |
| 4 | `threshold` | uint256 | SafeStorage | `2` — verified |
| 5 | `nonce` | uint256 | SafeStorage | `0` — nothing executed yet |
| 6 | `_deprecatedDomainSeparator` | bytes32 | SafeStorage | `0` |
| 7 | `signedMessages` | mapping(bytes32⇒uint256) | SafeStorage | empty |
| 8 | `approvedHashes` | mapping(address⇒mapping(bytes32⇒uint256)) | SafeStorage | empty |
| `keccak256("guard_manager.guard.address")` | guard | address | GuardManager | `0x0` — verified |
| `keccak256("fallback_manager.handler.address")` | fallback handler | address | FallbackManager | `0xfd0732Dc9E303f09fCEf3a7388Ad10A83459Ec99` (CompatibilityFallbackHandler v1.4.1) |

### Signers

Eight of the nine are owners of the Admin Safe `0x73d1C7dc9CEb14660Cf1E9BB29F80ECF9E97D774` (itself Safe v1.3.0, 4-of-10); the ninth is not. Threshold is 2. Listed in the deployed owner-ring order, which starts with the deployer rather than following the Admin Safe's order — ring order carries no meaning beyond the `prevOwner` argument when removing an owner.

| # | Signer | Admin Safe owner |
|---|---|---|
| 1 | `0xeee661edcFE634Dc0e29D62C26AfD62c0843b817` | yes — deployed the Safe |
| 2 | `0xF6A745f9B38FFcd17Ee8909AC89151D788F95282` | yes |
| 3 | `0xbfFcAdCd5549cC378693108BcD4435776A6fa795` | yes |
| 4 | `0xB680373c50E9E877DA7dCF9efcc0dFB234452ad3` | yes |
| 5 | `0x6eb0c274EC4B1d51152e45BAED22f883B2A3Bc60` | yes |
| 6 | `0xc1047a4D9f6071B55585523F7F659F39A1fBA74b` | yes |
| 7 | `0xDB97c377F23a9Dc54c3D6F9df7bC0ca4Cf7D5A81` | yes |
| 8 | `0x89562FC5AEF155481aE0C7dde1300110B4dF2F1D` | yes |
| 9 | `0xC3CbFc5DA4B3d4B1258D63cA7ba56518C33f28c7` | **no** — EOA created only for pausing |

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
