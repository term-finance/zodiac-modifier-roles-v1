# Ownerless Safe Governance — Verification

Checks for the setup in [setup_plan_ownerless_safe.md](setup_plan_ownerless_safe.md), against the target state in [new_governance_plan_ownerless_safe.md](new_governance_plan_ownerless_safe.md).

Every check here is a read or a simulation. Nothing in this file sends a transaction. Run each section right after the matching setup step, so a mistake is caught before the next step builds on it. Sections A–D are pre-flight, E–H confirm the migration, and I is the final sweep.

Every `cast` line below is packed into [verify_ownerless_safe.sh](verify_ownerless_safe.sh), which runs a section and exits non-zero if any check in it failed. Prefer the script — it compares against the expected value rather than leaving that to your eye. The commands are kept here so you can see what is being read, and run one on its own when a check fails.

Run the line for the step you just finished. Each one exits `0` only if every check in that section passed — don't start the next step until it does.

| After | Section | Command |
|---|---|---|
| — (before step 1) | A | `RPC=$RPC ./verify_ownerless_safe.sh A` |
| step 0 — fork rehearsal | all | `RPC=$FORK ./verify_ownerless_safe.sh all` |
| step 1 — PauseGuard | B | `RPC=$RPC PAUSEGUARD=$PAUSEGUARD ./verify_ownerless_safe.sh B` |
| step 2 — SetTxNonceGuard | C | `RPC=$RPC SETGUARD=$SETGUARD ./verify_ownerless_safe.sh C` |
| step 3 — NewRoles | D | `RPC=$RPC NEWROLES=$NEWROLES SETGUARD=$SETGUARD ./verify_ownerless_safe.sh D` |
| step 4 — module enabled | E | `RPC=$RPC NEWROLES=$NEWROLES ./verify_ownerless_safe.sh E` |
| step 5 — batch queued | F | `RPC=$RPC BATCH_CALLDATA=0x.. ./verify_ownerless_safe.sh F` |
| step 6 — batch executed | G | `RPC=$RPC ./verify_ownerless_safe.sh G` |
| step 7 — pause guard installed | H | `RPC=$RPC PAUSEGUARD=$PAUSEGUARD ./verify_ownerless_safe.sh H` |
| step 8 — fallback handler cleared | I | `RPC=$RPC PAUSEGUARD=$PAUSEGUARD SETGUARD=$SETGUARD NEWROLES=$NEWROLES ./verify_ownerless_safe.sh I` |
| step 9 — final | all | `RPC=$RPC PAUSEGUARD=$PAUSEGUARD SETGUARD=$SETGUARD NEWROLES=$NEWROLES ./verify_ownerless_safe.sh all` |

Step 0 runs `all` against the fork, where the whole sequence has already been played out, so every section should be green there before you touch mainnet. On a fork started with a custom chain id, add `CHAIN=0` to skip the chain check.

Addresses that do not exist yet are passed in as you deploy them; a section that needs one you have not set reports `SKIP` for those checks rather than failing. The fork-only checks in D and H are marked `SKIP` too — run those by hand.

Sections E–I describe the post-migration state, so running them early reports `FAIL`, not `SKIP`. That is expected before the step they belong to.

Set these once:

```bash
export RPC=<rpc>
export FORK=http://127.0.0.1:8545   # the step 0 fork
export OWNERLESS=0xb8A1dF43c1c88b13937C0c5CEBbAd15830cAeC03
export DELAY=0x0C19d8A404079d71E5CA3e32fE3f758Ab543ACdf
export OLDROLES=0x405b47354CF06A25DE1DDb35EC65F03939E2e8D2
export GOV=0x2B715634134220ffeEE9458b4e34E41A41418607
export PROPOSER=0xd5E12854A3Dba99deF295A7635D3Ba16427d2A28
export ADMINSAFE=0x73d1C7dc9CEb14660Cf1E9BB29F80ECF9E97D774
export SENTINEL=0x0000000000000000000000000000000000000001
export MULTISEND=0x40A2aCCbd92BCA938b02010E17A5b8929b49130D        # v1.3.0 — the migration batch
export ROLES_MULTISEND=0x9641d764fc13c8B624c04430C7356C1C7C8102e2  # v1.4.1 — NewRoles multisend
export PAUSESAFE=0x74f3F3dEfdC563bbFC8637BaB2d30596D2817472
export DELAYOWNER=0x2a875746D0c88EBD2bbBfc8F8a773c58c3373ad3
export MASTERCOPY=0x85388a8cd772b19a468F982Dc264C238856939C9   # Roles v1.0.0, audited
export PERMLIB=0x543D1DE69b25420685Ef723842D0087d9b731B06      # linked inside the mastercopy
# fill in as they are deployed
export PAUSEGUARD= NEWROLES= SETGUARD=
```

---

## A. Before anything — starting state

```bash
RPC=$RPC ./verify_ownerless_safe.sh A
```

Confirms the chain still looks like the plan assumed. If any of these differ, stop and re-read the state before deploying.

```bash
cast call $DELAY 'owner()(address)' --rpc-url $RPC                      # 0x405b47354CF06A25DE1DDb35EC65F03939E2e8D2 (old Roles)
cast call $DELAY 'guard()(address)' --rpc-url $RPC                      # 0x0
cast call $DELAY 'txNonce()(uint256)' --rpc-url $RPC                    # 203
cast call $DELAY 'queueNonce()(uint256)' --rpc-url $RPC                 # 203 — queue empty
cast call $DELAY 'txCooldown()(uint256)' --rpc-url $RPC                 # 86400
cast call $DELAY 'txExpiration()(uint256)' --rpc-url $RPC               # 86400
cast call $DELAY 'getModulesPaginated(address,uint256)(address[],address)' $SENTINEL 10 --rpc-url $RPC   # [Proposer Safe]
cast call $OLDROLES 'owner()(address)' --rpc-url $RPC                   # 0xb8A1dF43c1c88b13937C0c5CEBbAd15830cAeC03 (Ownerless Safe)
cast call $OLDROLES 'getModulesPaginated(address,uint256)(address[],address)' $SENTINEL 10 --rpc-url $RPC  # [] — Governor disconnected
cast call $OWNERLESS 'getModulesPaginated(address,uint256)(address[],address)' $SENTINEL 10 --rpc-url $RPC # [old Roles, Delay]
```

| Check | Expected | Why it matters |
|---|---|---|
| Delay `owner` | old Roles | the batch's call 3 depends on it |
| Delay queue | `txNonce == queueNonce` | FIFO: anything queued ahead of the batch executes first |
| Ownerless Safe ring | `0x1 → 0x405b47354CF06A25DE1DDb35EC65F03939E2e8D2 → 0x0C19d8A404079d71E5CA3e32fE3f758Ab543ACdf → 0x1` | fixes `prevModule` = `0x…01` in batch calls 5 and 6 |
| old Roles role 1 target entry | `0x…01` | `Clearance.Target`, which is what permits call 3 |

```bash
# role 1 targets[Delay] on the old Roles
cast storage $OLDROLES 0x6d118fdf1559b49b55b86a40bd7fa6c747463e77d457904632e6b94ed8c4134f --rpc-url $RPC   # 0x…01
```

---

## B. After step 1 — PauseGuard

```bash
RPC=$RPC PAUSEGUARD=$PAUSEGUARD ./verify_ownerless_safe.sh B
```

```bash
cast call $PAUSEGUARD 'supportsInterface(bytes4)(bool)' 0xe6d7a83a --rpc-url $RPC   # true
cast call $PAUSEGUARD 'supportsInterface(bytes4)(bool)' 0x01ffc9a7 --rpc-url $RPC   # true
cast call $PAUSEGUARD 'paused()(bool)' --rpc-url $RPC                   # false
cast call $PAUSEGUARD 'pauser()(address)' --rpc-url $RPC                # 0x74f3F3dEfdC563bbFC8637BaB2d30596D2817472 (PauseSafe)
cast call $PAUSEGUARD 'admin()(address)' --rpc-url $RPC                 # 0x73d1C7dc9CEb14660Cf1E9BB29F80ECF9E97D774 (Admin Safe)
```

- **`supportsInterface(0xe6d7a83a)` must be `true`.** `Guardable.setGuard` reverts otherwise, which would fail setup step 7.
- View names (`paused`, `pauser`, `admin`) depend on your implementation; adjust if they differ.

Simulate the two access rules before trusting them:

```bash
cast call $PAUSEGUARD 'pause()' --from $PAUSESAFE --rpc-url $RPC         # succeeds (no state change from a call)
cast call $PAUSEGUARD 'pause()' --from $ADMINSAFE --rpc-url $RPC         # must revert — admin is not the pauser
cast call $PAUSEGUARD 'unpause()' --from $PAUSESAFE --rpc-url $RPC       # must revert — pauser is not the admin
cast call $PAUSEGUARD 'setPauser(address)' $ADMINSAFE --from $PAUSESAFE --rpc-url $RPC  # must revert
```

---

## C. After step 2 — SetTxNonceGuard

```bash
RPC=$RPC SETGUARD=$SETGUARD ./verify_ownerless_safe.sh C
```

```bash
cast call $SETGUARD 'delay()(address)' --rpc-url $RPC                            # 0x0C19d8A404079d71E5CA3e32fE3f758Ab543ACdf — the Delay
cast call $SETGUARD 'supportsInterface(bytes4)(bool)' 0xe6d7a83a --rpc-url $RPC  # true
cast call $SETGUARD 'supportsInterface(bytes4)(bool)' 0x01ffc9a7 --rpc-url $RPC  # true
```

- **`delay()` is the only thing this contract holds, and nothing on chain checks it.** `Roles.setGuard` in step 3 verifies `supportsInterface` and nothing else, so a guard built against the wrong Delay — the Term DAO's `0x80Ce5a0de8B1604e3122BEE73360dC3b987F891A`, or the DelayOwnerSafe `0x2a875746D0c88EBD2bbBfc8F8a773c58c3373ad3` — installs without complaint and then rejects every Governor transaction. Run this before step 3, not after.
- `delay` is `immutable`, so it is in the bytecode and `cast storage $SETGUARD 0` shows nothing. The getter is the only read.
- The contract declares no state variables; there is nothing else to check here.

---

## D. After step 3 — NewRoles

```bash
RPC=$RPC NEWROLES=$NEWROLES SETGUARD=$SETGUARD ./verify_ownerless_safe.sh D
```

Wiring:

```bash
cast call $NEWROLES 'owner()(address)' --rpc-url $RPC                    # 0xb8A1dF43c1c88b13937C0c5CEBbAd15830cAeC03 (Ownerless Safe)
cast call $NEWROLES 'avatar()(address)' --rpc-url $RPC                   # 0xb8A1dF43c1c88b13937C0c5CEBbAd15830cAeC03
cast call $NEWROLES 'target()(address)' --rpc-url $RPC                   # 0x2a875746D0c88EBD2bbBfc8F8a773c58c3373ad3 (DelayOwnerSafe)
cast call $NEWROLES 'multisend()(address)' --rpc-url $RPC                # 0x9641d764fc13c8B624c04430C7356C1C7C8102e2 (MultiSendCallOnly v1.4.1)
cast call $NEWROLES 'guard()(address)' --rpc-url $RPC                    # SetTxNonceGuard
cast call $NEWROLES 'defaultRoles(address)(uint16)' $GOV --rpc-url $RPC   # 1
cast call $NEWROLES 'isModuleEnabled(address)(bool)' $GOV --rpc-url $RPC  # true
```

`guard()` must be the SetTxNonceGuard that section C cleared — re-read `delay()` on the address that actually came back here, in case a different instance was installed.

Role 1, read from storage (the `roles` mapping is `internal`; these slots are key-derived, so they hold for any Roles deployment):

```bash
cast storage $NEWROLES 0x84f2af0e843bf5d088bc58e2ec3e637cc9a06f27000758f776cf7f0048bbf316 --rpc-url $RPC  # members[Governor]  = 0x…01
cast storage $NEWROLES 0x6d118fdf1559b49b55b86a40bd7fa6c747463e77d457904632e6b94ed8c4134f --rpc-url $RPC  # targets[Delay]     = 0x…02
cast storage $NEWROLES 0x2e72263c2be6fdc6f1499ba76346dee89ffb39313281bfa1f661681dff2962df --rpc-url $RPC  # functions[Delay‖setTxNonce] = 0x2000…0
```

| Slot | Meaning | Expected |
|---|---|---|
| `0x84f2af0e…f316` | `members[Governor]` | `0x…0001` — Governor is a member |
| `0x6d118fdf…134f` | `targets[Delay]` | `0x…0002` — `Clearance.Function`, `ExecutionOptions.None` |
| `0x2e72263c…62df` | `functions[Delay ‖ 0x46ba2307]` | `0x2000…0` — options None, wildcarded, length 0 |

`targets[Delay]` reading `0x…01` instead of `0x…02` means `allowTarget` was used instead of `scopeTarget`, which would let role 1 call **any** Delay function. That is the single most important value in this file.

The fork is the only safe place for a negative permission test, since the Delay's queue is empty on mainnet and `setTxNonce` always reverts then. On the fork, with an entry queued:

```bash
# allowed: setTxNonce through role 1
cast call $NEWROLES 'execTransactionWithRole(address,uint256,bytes,uint8,uint16,bool)(bool)' \
  $DELAY 0 $(cast calldata 'setTxNonce(uint256)' <queueNonce>) 0 1 true --from $GOV --rpc-url $RPC   # true

# denied: anything else on the Delay
cast call $NEWROLES 'execTransactionWithRole(address,uint256,bytes,uint8,uint16,bool)(bool)' \
  $DELAY 0 $(cast calldata 'setTxCooldown(uint256)' 0) 0 1 true --from $GOV --rpc-url $RPC           # must revert

```

**NewRoles is a proxy, so its own code is 45 bytes and contains no logic.** Check the proxy shape first, then run every bytecode check against the mastercopy it points at.

```bash
# the proxy is the exact EIP-1167 template pointing at the audited mastercopy — nothing else
cast code $NEWROLES --rpc-url $RPC | tr 'A-F' 'a-f'
# 0x363d3d373d3d3d363d7385388a8cd772b19a468f982dc264c238856939c95af43d82803e903d91602b57fd5bf3
```

A single equality on that string is the strongest check in this section: it fixes the implementation, and it fails if the proxy points anywhere else.

```bash
# THE check. keccak256 of the deployed runtime pins the implementation exactly;
# the selector greps below are indicative, another build could carry the same
# selectors. Recompiling the audited commit with the mastercopy's own solc
# settings reproduces this hash.
cast codehash $MASTERCOPY --rpc-url $RPC   # 0xccd8ad5609bd6b5dffb5aa4be6ac4b0c4fd12f0d5ab908f69c9342e63e186db1
cast codehash $PERMLIB    --rpc-url $RPC   # 0x8855a716d8a3ff5fedf4be46bed673d391a183f54e406d702a9bafa767fc407a
```

If either differs, stop: the proxy is delegating to something other than the audited Roles v1.0.0, or that build is linked against a different `Permissions`. Neither is recoverable by reconfiguring — it needs a new proxy off the right mastercopy.

```bash
cast code $MASTERCOPY --rpc-url $RPC | grep -c 639518aaac    # 0 — callTargetFunctionWithRole absent
cast code $MASTERCOPY --rpc-url $RPC | grep -c 63468721a7    # 1 — execTransactionFromModule
cast code $MASTERCOPY --rpc-url $RPC | grep -c 635229073f    # 1 — execTransactionFromModuleReturnData
cast code $MASTERCOPY --rpc-url $RPC | tr 'A-F' 'a-f' | grep -c 73543d1de69b25420685ef723842d0087d9b731b06   # 1 — linked Permissions
```

The mastercopy is Roles v1.0.0, byte-identical in source to the audited commit, and it is shared — other deployments proxy off it, so never assume it is yours to change. Its own `owner`/`avatar`/`target` read `0x…01`, the locked state that makes `setUp` unrepeatable:

```bash
cast call $MASTERCOPY 'owner()(address)' --rpc-url $RPC     # 0x0000000000000000000000000000000000000001
```

Storage slots and the ABI are identical to a direct deployment, so every other check in this section is unchanged — the proxy holds its own storage.

---

## E. After step 4 — NewRoles enabled, still inert

```bash
RPC=$RPC NEWROLES=$NEWROLES ./verify_ownerless_safe.sh E
```

```bash
cast call $DELAYOWNER 'getModulesPaginated(address,uint256)(address[],address)' $SENTINEL 10 --rpc-url $RPC  # [NewRoles]
cast call $DELAY 'owner()(address)' --rpc-url $RPC                       # still 0x405b47354CF06A25DE1DDb35EC65F03939E2e8D2 (old Roles) — unchanged
```

The second line is the point of this section: NewRoles is wired but the Delay has not moved, so the new branch still has no authority.

---

## F. After step 5 — the batch is queued, not executed

```bash
RPC=$RPC BATCH_CALLDATA=0x.. ./verify_ownerless_safe.sh F   # calldata re-derives the hash
```

```bash
cast call $DELAY 'queueNonce()(uint256)' --rpc-url $RPC                  # 204
cast call $DELAY 'txNonce()(uint256)' --rpc-url $RPC                     # 203 — nothing executed
cast call $DELAY 'txHash(uint256)(bytes32)' 203 --rpc-url $RPC
cast call $DELAY 'txCreatedAt(uint256)(uint256)' 203 --rpc-url $RPC      # t0
cast call $DELAY 'owner()(address)' --rpc-url $RPC                       # still 0x405b47354CF06A25DE1DDb35EC65F03939E2e8D2 (old Roles)
```

Confirm the stored hash matches the calldata you intend to execute, before the cooldown elapses:

```bash
cast call $DELAY 'getTransactionHash(address,uint256,bytes,uint8)(bytes32)' \
  $MULTISEND 0 <batch-calldata> 1 --rpc-url $RPC      # must equal txHash(203)
```

| Check | Expected |
|---|---|
| Execution window | `t0 + 86400` to `t0 + 172800` |
| `getTransactionHash(...)` | equal to `txHash(203)` |
| Old Roles modules | still `[]` — the grant is inside the batch, not yet applied |

A mismatch here means the entry can never be executed. Let it expire and queue again; don't try to patch the arguments.

---

## G. After step 6 — the migration landed

```bash
RPC=$RPC ./verify_ownerless_safe.sh G
```

```bash
cast call $DELAY 'owner()(address)' --rpc-url $RPC                       # 0x2a875746D0c88EBD2bbBfc8F8a773c58c3373ad3 (DelayOwnerSafe)
cast call $DELAY 'txNonce()(uint256)' --rpc-url $RPC                     # 204 == queueNonce
cast call $OWNERLESS 'getModulesPaginated(address,uint256)(address[],address)' $SENTINEL 10 --rpc-url $RPC  # [Delay] only
cast call $OLDROLES 'getModulesPaginated(address,uint256)(address[],address)' $SENTINEL 10 --rpc-url $RPC   # []
cast storage $OLDROLES 0x84f2af0e843bf5d088bc58e2ec3e637cc9a06f27000758f776cf7f0048bbf316 --rpc-url $RPC    # 0x0
cast call $OWNERLESS 'nonce()(uint256)' --rpc-url $RPC                   # 16 — unchanged, the Safe never signed
```

The temporary grant must be gone. Check the old Roles' membership slot for the Ownerless Safe directly:

```bash
cast storage $OLDROLES $(cast index address $OWNERLESS 0xa775687211c2b3346a0f5a2a0e7590e6c1838453e3785e6dd2a8efd6265ddf15) --rpc-url $RPC   # 0x0
```

| Check | Expected | Meaning if wrong |
|---|---|---|
| Delay `owner` | `0x2a875746D0c88EBD2bbBfc8F8a773c58c3373ad3` (DelayOwnerSafe) | the handover didn't happen |
| Ownerless Safe modules | `[Delay]` | old Roles still has a path into the Safe |
| Old Roles modules | `[]` | something can still call through the old Roles |
| Old Roles role 1 members | `0x0` for the Ownerless Safe | the temporary grant was left open |
| Ownerless Safe `nonce` | `16`, the pre-migration value | the rule was broken — the Safe signed something |

---

## H. After step 7 — the guard, and the live veto path

```bash
RPC=$RPC PAUSEGUARD=$PAUSEGUARD ./verify_ownerless_safe.sh H
```

```bash
cast call $DELAY 'guard()(address)' --rpc-url $RPC                       # PauseGuard
```

On the fork, exercise all three paths end to end:

1. **Normal execution.** Queue a harmless transaction from the Proposer Safe `0xd5E12854A3Dba99deF295A7635D3Ba16427d2A28`, warp past `txCooldown`, call `executeNextTx`, confirm it runs.
2. **Pause.** `pause()` from the PauseSafe `0x74f3F3dEfdC563bbFC8637BaB2d30596D2817472`, which now needs 2 of 9 signatures; confirm `executeNextTx` reverts. Then `unpause()` from the Admin Safe `0x73d1C7dc9CEb14660Cf1E9BB29F80ECF9E97D774` (4 of 10) and confirm it runs again. Exercise the threshold too: a single PauseSafe signature must not be enough to pause.
3. **Veto.** Queue a transaction, create a Governor proposal carrying `execTransactionWithRole(Delay, 0, setTxNonce(n), Call, 1, true)`, vote it through, warp past the 22-hour voting period, `execute`, and confirm `txNonce` moved past `n`.

Path 3 also confirms the timing that the plan flags: with a 22-hour vote and a 1-day cooldown, the proposal has to be created within about 2 hours of the queueing to have any execution window at all.

---

## I. After step 8 — final sweep, full target state

```bash
RPC=$RPC PAUSEGUARD=$PAUSEGUARD SETGUARD=$SETGUARD NEWROLES=$NEWROLES ./verify_ownerless_safe.sh I
```

Run this once everything is done; it is the same list as the plan's tables, in one place.

| Contract | Check | Expected |
|---|---|---|
| Delay | `owner`, `guard` | `0x2a875746D0c88EBD2bbBfc8F8a773c58c3373ad3`, PauseGuard |
| Delay | modules | `[0xd5E12854A3Dba99deF295A7635D3Ba16427d2A28]` (Proposer Safe) |
| Delay | `txCooldown`, `txExpiration` | `86400`, `86400` |
| Delay | `txNonce`, `queueNonce` | equal |
| Delay | `avatar`, `target` | `0xb8A1dF43c1c88b13937C0c5CEBbAd15830cAeC03` (both) |
| NewRoles | `owner`, `avatar`, `target` | `0xb8A1dF43c1c88b13937C0c5CEBbAd15830cAeC03`, `0xb8A1dF43c1c88b13937C0c5CEBbAd15830cAeC03`, `0x2a875746D0c88EBD2bbBfc8F8a773c58c3373ad3` |
| NewRoles | `multisend`, `guard` | `0x9641d764fc13c8B624c04430C7356C1C7C8102e2`, SetTxNonceGuard |
| NewRoles | `defaultRoles(Governor)`, modules | `1`, `[0x2B715634134220ffeEE9458b4e34E41A41418607]` (Governor) |
| NewRoles | role 1 slots | `0x…01`, `0x…02`, `0x2000…0` (section D) |
| NewRoles | code | the 45-byte EIP-1167 template pointing at `0x85388a8cd772b19a468F982Dc264C238856939C9` — exact string match |
| Roles mastercopy `0x85388a8cd772b19a468F982Dc264C238856939C9` | codehash | `0xccd8ad5609bd6b5dffb5aa4be6ac4b0c4fd12f0d5ab908f69c9342e63e186db1` — the audited Roles v1.0.0 build |
| Roles mastercopy | `owner` / `avatar` / `target` | `0x…01` — locked, `setUp` spent |
| Permissions library `0x543D1DE69b25420685Ef723842D0087d9b731B06` | codehash | `0x8855a716d8a3ff5fedf4be46bed673d391a183f54e406d702a9bafa767fc407a` |
| DelayOwnerSafe `0x2a875746D0c88EBD2bbBfc8F8a773c58c3373ad3` | owners, threshold, modules | 11, `5`, `[NewRoles]` |
| Ownerless Safe | modules, `nonce` | `[0x0C19d8A404079d71E5CA3e32fE3f758Ab543ACdf]` (Delay), unchanged at `16` |
| Old Roles `0x405b47354CF06A25DE1DDb35EC65F03939E2e8D2` | Delay ownership, modules, role 1 members | none, `[]`, none |
| PauseGuard | `paused`, `pauser`, `admin` | `false`, `0x74f3F3dEfdC563bbFC8637BaB2d30596D2817472`, `0x73d1C7dc9CEb14660Cf1E9BB29F80ECF9E97D774` |
| PauseSafe `0x74f3F3dEfdC563bbFC8637BaB2d30596D2817472` | owners, threshold | 9 owners — 8 Admin Safe signers plus `0xC3CbFc5DA4B3d4B1258D63cA7ba56518C33f28c7` — and `2` |
| Governor `0x2B715634134220ffeEE9458b4e34E41A41418607` | `votingPeriod`, `quorum` | `79200`, `1e24` |
| Proposer Safe | fallback handler slot `0x6c9a6c4a39284e37ed1cf53d337577d14212a4870fb976a4366c693b939918d5` | `0x0` |
| Proposer Safe | owners, threshold | 11, `5` |
