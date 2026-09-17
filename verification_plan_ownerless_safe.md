# Ownerless Safe Governance — Verification

Checks for the setup in [setup_plan_ownerless_safe.md](setup_plan_ownerless_safe.md), against the target state in [new_governance_plan_ownerless_safe.md](new_governance_plan_ownerless_safe.md).

Every check here is a read or a simulation. Nothing in this file sends a transaction. Run each section right after the matching setup step, so a mistake is caught before the next step builds on it. Sections A–D are pre-flight, E–H confirm the migration, and I is the final sweep.

Set these once:

```bash
export RPC=<rpc>
export OWNERLESS=0xb8A1dF43c1c88b13937C0c5CEBbAd15830cAeC03
export DELAY=0x0C19d8A404079d71E5CA3e32fE3f758Ab543ACdf
export OLDROLES=0x405b47354CF06A25DE1DDb35EC65F03939E2e8D2
export GOV=0x2B715634134220ffeEE9458b4e34E41A41418607
export PROPOSER=0xd5E12854A3Dba99deF295A7635D3Ba16427d2A28
export ADMINSAFE=0x73d1C7dc9CEb14660Cf1E9BB29F80ECF9E97D774
export SENTINEL=0x0000000000000000000000000000000000000001
export MULTISEND=0x40A2aCCbd92BCA938b02010E17A5b8929b49130D
# fill in as they are deployed
export PAUSESAFE= PAUSEGUARD= DELAYOWNER= NEWROLES= SETGUARD=
```

---

## A. Before anything — starting state

Confirms the chain still looks like the plan assumed. If any of these differ, stop and re-read the state before deploying.

```bash
cast call $DELAY 'owner()(address)' --rpc-url $RPC                      # 0x405b4735… (old Roles)
cast call $DELAY 'guard()(address)' --rpc-url $RPC                      # 0x0
cast call $DELAY 'txNonce()(uint256)' --rpc-url $RPC                    # 203
cast call $DELAY 'queueNonce()(uint256)' --rpc-url $RPC                 # 203 — queue empty
cast call $DELAY 'txCooldown()(uint256)' --rpc-url $RPC                 # 86400
cast call $DELAY 'txExpiration()(uint256)' --rpc-url $RPC               # 86400
cast call $DELAY 'getModulesPaginated(address,uint256)(address[],address)' $SENTINEL 10 --rpc-url $RPC   # [Proposer Safe]
cast call $OLDROLES 'owner()(address)' --rpc-url $RPC                   # 0xb8A1dF43… (Ownerless Safe)
cast call $OLDROLES 'getModulesPaginated(address,uint256)(address[],address)' $SENTINEL 10 --rpc-url $RPC  # [] — Governor disconnected
cast call $OWNERLESS 'getModulesPaginated(address,uint256)(address[],address)' $SENTINEL 10 --rpc-url $RPC # [old Roles, Delay]
```

| Check | Expected | Why it matters |
|---|---|---|
| Delay `owner` | old Roles | the batch's call 3 depends on it |
| Delay queue | `txNonce == queueNonce` | FIFO: anything queued ahead of the batch executes first |
| Ownerless Safe ring | `0x1 → old Roles → Delay → 0x1` | fixes `prevModule` = `0x…01` in batch calls 5 and 6 |
| old Roles role 1 target entry | `0x…01` | `Clearance.Target`, which is what permits call 3 |

```bash
# role 1 targets[Delay] on the old Roles
cast storage $OLDROLES 0x6d118fdf1559b49b55b86a40bd7fa6c747463e77d457904632e6b94ed8c4134f --rpc-url $RPC   # 0x…01
```

---

## B. After step 1 — PauseSafe and PauseGuard

```bash
cast call $PAUSESAFE 'VERSION()(string)' --rpc-url $RPC                 # "1.3.0"
cast storage $PAUSESAFE 0 --rpc-url $RPC                                # …d9db270c1b5e3bd161e8c8503c55ceabee709552
cast call $PAUSESAFE 'getThreshold()(uint256)' --rpc-url $RPC           # 1
cast call $PAUSESAFE 'getOwners()(address[])' --rpc-url $RPC            # the 10 Admin Safe signers
cast call $PAUSEGUARD 'supportsInterface(bytes4)(bool)' 0xe6d7a83a --rpc-url $RPC   # true
cast call $PAUSEGUARD 'supportsInterface(bytes4)(bool)' 0x01ffc9a7 --rpc-url $RPC   # true
cast call $PAUSEGUARD 'paused()(bool)' --rpc-url $RPC                   # false
cast call $PAUSEGUARD 'pauser()(address)' --rpc-url $RPC                # PauseSafe
cast call $PAUSEGUARD 'admin()(address)' --rpc-url $RPC                 # 0x73d1C7dc…
```

- **`supportsInterface(0xe6d7a83a)` must be `true`.** `Guardable.setGuard` reverts otherwise, which would fail setup step 7.
- **The PauseSafe signer set must match the Admin Safe's**, not the Proposer Safe's. Compare against `cast call $ADMINSAFE 'getOwners()(address[])'`.
- View names (`paused`, `pauser`, `admin`) depend on your implementation; adjust if they differ.

Simulate the two access rules before trusting them:

```bash
cast call $PAUSEGUARD 'pause()' --from $PAUSESAFE --rpc-url $RPC         # succeeds (no state change from a call)
cast call $PAUSEGUARD 'pause()' --from $ADMINSAFE --rpc-url $RPC         # must revert — admin is not the pauser
cast call $PAUSEGUARD 'unpause()' --from $PAUSESAFE --rpc-url $RPC       # must revert — pauser is not the admin
cast call $PAUSEGUARD 'setPauser(address)' $ADMINSAFE --from $PAUSESAFE --rpc-url $RPC  # must revert
```

---

## C. After step 2 — DelayOwnerSafe

```bash
cast storage $DELAYOWNER 0 --rpc-url $RPC                               # identical to: cast storage $OWNERLESS 0
cast call $DELAYOWNER 'getThreshold()(uint256)' --rpc-url $RPC           # 5
cast call $DELAYOWNER 'getOwners()(address[])' --rpc-url $RPC            # the 11 Proposer Safe signers
cast call $DELAYOWNER 'getModulesPaginated(address,uint256)(address[],address)' $SENTINEL 10 --rpc-url $RPC  # [] for now
cast call $DELAYOWNER 'nonce()(uint256)' --rpc-url $RPC                  # 0
```

Diff the owner sets directly rather than by eye:

```bash
diff <(cast call $DELAYOWNER 'getOwners()(address[])' --rpc-url $RPC | tr ',' '\n' | sort) \
     <(cast call $PROPOSER   'getOwners()(address[])' --rpc-url $RPC | tr ',' '\n' | sort)
```

Slot 0 must equal the Ownerless Safe's slot 0 — v1.3.0 ships both `GnosisSafe` and `GnosisSafeL2`, and only the former is in use here.

---

## D. After step 3 — NewRoles and SetTxNonceGuard

Wiring:

```bash
cast call $NEWROLES 'owner()(address)' --rpc-url $RPC                    # 0xb8A1dF43… (Ownerless Safe)
cast call $NEWROLES 'avatar()(address)' --rpc-url $RPC                   # 0xb8A1dF43…
cast call $NEWROLES 'target()(address)' --rpc-url $RPC                   # DelayOwnerSafe
cast call $NEWROLES 'multisend()(address)' --rpc-url $RPC                # 0x40A2aCCb…
cast call $NEWROLES 'guard()(address)' --rpc-url $RPC                    # SetTxNonceGuard
cast call $NEWROLES 'defaultRoles(address)(uint16)' $GOV --rpc-url $RPC   # 1
cast call $NEWROLES 'isModuleEnabled(address)(bool)' $GOV --rpc-url $RPC  # true
cast call $SETGUARD 'delay()(address)' --rpc-url $RPC                    # 0x0C19d8A4…
cast call $SETGUARD 'supportsInterface(bytes4)(bool)' 0xe6d7a83a --rpc-url $RPC  # true
```

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

# denied: the removed function is not in the bytecode at all
cast code $NEWROLES --rpc-url $RPC | grep -c 639518aaac                                              # 0
```

Also confirm the overrides that replace it are present, and that the Permissions library is the expected one:

```bash
cast code $NEWROLES --rpc-url $RPC | grep -c 63468721a7    # 1 — execTransactionFromModule
cast code $NEWROLES --rpc-url $RPC | grep -c 635229073f    # 1 — execTransactionFromModuleReturnData
cast code $NEWROLES --rpc-url $RPC | tr 'A-F' 'a-f' | grep -c 73a4af47637c32482820960f680b1e52a11c705087   # >0 — linked library
```

---

## E. After step 4 — NewRoles enabled, still inert

```bash
cast call $DELAYOWNER 'getModulesPaginated(address,uint256)(address[],address)' $SENTINEL 10 --rpc-url $RPC  # [NewRoles]
cast call $DELAY 'owner()(address)' --rpc-url $RPC                       # still 0x405b4735… — unchanged
```

The second line is the point of this section: NewRoles is wired but the Delay has not moved, so the new branch still has no authority.

---

## F. After step 5 — the batch is queued, not executed

```bash
cast call $DELAY 'queueNonce()(uint256)' --rpc-url $RPC                  # 204
cast call $DELAY 'txNonce()(uint256)' --rpc-url $RPC                     # 203 — nothing executed
cast call $DELAY 'txHash(uint256)(bytes32)' 203 --rpc-url $RPC
cast call $DELAY 'txCreatedAt(uint256)(uint256)' 203 --rpc-url $RPC      # t0
cast call $DELAY 'owner()(address)' --rpc-url $RPC                       # still the old Roles
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
cast call $DELAY 'owner()(address)' --rpc-url $RPC                       # DelayOwnerSafe
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
| Delay `owner` | DelayOwnerSafe | the handover didn't happen |
| Ownerless Safe modules | `[Delay]` | old Roles still has a path into the Safe |
| Old Roles modules | `[]` | something can still call through the old Roles |
| Old Roles role 1 members | `0x0` for the Ownerless Safe | the temporary grant was left open |
| Ownerless Safe `nonce` | `16`, the pre-migration value | the rule was broken — the Safe signed something |

---

## H. After step 7 — the guard, and the live veto path

```bash
cast call $DELAY 'guard()(address)' --rpc-url $RPC                       # PauseGuard
```

On the fork, exercise all three paths end to end:

1. **Normal execution.** Queue a harmless transaction from the Proposer Safe, warp past `txCooldown`, call `executeNextTx`, confirm it runs.
2. **Pause.** `pause()` from PauseSafe, confirm `executeNextTx` now reverts; `unpause()` from the Admin Safe, confirm it runs again.
3. **Veto.** Queue a transaction, create a Governor proposal carrying `execTransactionWithRole(Delay, 0, setTxNonce(n), Call, 1, true)`, vote it through, warp past the 22-hour voting period, `execute`, and confirm `txNonce` moved past `n`.

Path 3 also confirms the timing that the plan flags: with a 22-hour vote and a 1-day cooldown, the proposal has to be created within about 2 hours of the queueing to have any execution window at all.

---

## I. Final sweep — full target state

Run this once everything is done; it is the same list as the plan's tables, in one place.

| Contract | Check | Expected |
|---|---|---|
| Delay | `owner`, `guard` | DelayOwnerSafe, PauseGuard |
| Delay | modules | `[Proposer Safe]` |
| Delay | `txCooldown`, `txExpiration` | `86400`, `86400` |
| Delay | `txNonce`, `queueNonce` | equal |
| Delay | `avatar`, `target` | Ownerless Safe (both) |
| NewRoles | `owner`, `avatar`, `target` | Ownerless Safe, Ownerless Safe, DelayOwnerSafe |
| NewRoles | `multisend`, `guard` | MultiSendCallOnly, SetTxNonceGuard |
| NewRoles | `defaultRoles(Governor)`, modules | `1`, `[Governor]` |
| NewRoles | role 1 slots | `0x…01`, `0x…02`, `0x2000…0` (section D) |
| NewRoles | `callTargetFunctionWithRole` in bytecode | absent |
| DelayOwnerSafe | owners, threshold, modules | 11, `5`, `[NewRoles]` |
| Ownerless Safe | modules, `nonce` | `[Delay]`, unchanged at `16` |
| Old Roles | Delay ownership, modules, role 1 members | none, `[]`, none |
| PauseGuard | `paused`, `pauser`, `admin` | `false`, PauseSafe, Admin Safe |
| PauseSafe | owners, threshold | the 10 Admin Safe signers, `1` |
| Governor | `votingPeriod`, `quorum` | `79200`, `1e24` |
| Proposer Safe | fallback handler slot `0x6c9a6c4a…918d5` | `0x0` |
| Proposer Safe | owners, threshold | 11, `5` |
