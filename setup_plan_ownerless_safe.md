# Ownerless Safe Governance — Setup Steps

How to reach the target state in [new_governance_plan_ownerless_safe.md](new_governance_plan_ownerless_safe.md). That file is the state to land on; this one is the order of operations.

## The rule this plan is built on

**The Ownerless Safe signs nothing.** It never executes a transaction of its own. Where its authority is required — it owns the old Roles `0x405b47354CF06A25DE1DDb35EC65F03939E2e8D2` and holds the module ring the old Roles sits in — that authority is exercised the same way it always is: the Proposer Safe queues a transaction in the Delay, and after the cooldown anyone executes it. The Delay is an enabled module on the Ownerless Safe, so `executeNextTx` makes the Ownerless Safe perform the call.

This removes the over-permissioning problem entirely rather than shortening it:

- **A queued Delay transaction can be a batch.** The queue entry carries its own `operation`, so it can be a `DelegateCall` into MultiSendCallOnly. The Ownerless Safe then performs every call in the batch, atomically, with no signatures from its owners.
- **The temporary grant opens and closes inside that one batch.** The old Roles gives the Ownerless Safe module status and role 1 membership, uses it to hand the Delay over, then takes both back. Nothing survives the transaction, and any revert rolls back all of it.
- **Nothing is rushed.** The batch sits in the queue for the 1-day cooldown in plain sight, and backing out means simply not executing it.

Total Ownerless Safe transactions: **zero**.

## Addresses

| Role | Address |
|---|---|
| Ownerless Safe (9/9, never signs) | `0xb8A1dF43c1c88b13937C0c5CEBbAd15830cAeC03` |
| Delay | `0x0C19d8A404079d71E5CA3e32fE3f758Ab543ACdf` |
| Old Roles (retired by the batch) | `0x405b47354CF06A25DE1DDb35EC65F03939E2e8D2` |
| Governor | `0x2B715634134220ffeEE9458b4e34E41A41418607` |
| Proposer Safe (5/11) | `0xd5E12854A3Dba99deF295A7635D3Ba16427d2A28` |
| Admin Safe (4/10) | `0x73d1C7dc9CEb14660Cf1E9BB29F80ECF9E97D774` |
| Permissions library | `0xA4af47637C32482820960f680b1e52a11c705087` |
| Safe v1.3.0 singleton | `0xd9Db270c1B5E3Bd161E8c8503c55cEABeE709552` |
| SafeProxyFactory v1.3.0 | `0xa6B71E26C5e0845f74c812102Ca7114b6a896AB2` |
| MultiSendCallOnly v1.3.0 | `0x40A2aCCbd92BCA938b02010E17A5b8929b49130D` |
| To deploy | `PauseSafe`, `PauseGuard`, `DelayOwnerSafe`, `SetTxNonceGuard`, `NewRoles` |

## Who signs what

| Step | Signer | Transactions |
|---|---|---|
| 1–3 | deployer key | deployments and NewRoles configuration |
| 4 | DelayOwnerSafe (5/11) | 1 — enable NewRoles |
| 5 | Proposer Safe (5/11) | 1 — queue the migration batch |
| 6 | anyone (gas only) | 1 — `executeNextTx` after the cooldown |
| 7 | DelayOwnerSafe (5/11) | 1 — set the Delay's guard |
| 8 | Proposer Safe (5/11) | 1 — clear the fallback handler |
| 9 | nobody | reads only — see the verification plan |

---

## Step 0 — rehearse on a fork

```bash
anvil --fork-url <rpc> --fork-block-number <recent>
```

Impersonate the Proposer Safe and the DelayOwnerSafe signers, run steps 1–8 including the cooldown warp, then run step 9's checks. Confirm before mainnet:

- **`PauseGuard.supportsInterface(0xe6d7a83a)` returns `true`.** `Guardable.setGuard` rejects a guard that doesn't, which would revert step 7.
- **The Delay's queue is empty** (`txNonce() == queueNonce()`, both `203` today). The queue is strictly FIFO, so anything queued ahead of the migration batch has to clear first.
- **The exact batch calldata.** `executeNextTx` re-hashes `(to, value, data, operation)` and reverts unless it matches, so save the bytes queued in step 5 verbatim.

---

## Step 1 — deploy PauseSafe and PauseGuard

**PauseSafe (1-of-10),** through SafeProxyFactory v1.3.0 against singleton `0xd9Db270c…`:

```
setup(
  owners:          the 10 Admin Safe signers (section 8 of the plan),
  threshold:       1,
  to:              0x0,      // no modules
  data:            "",
  fallbackHandler: 0x0,      // nothing calls this Safe
  paymentToken:    0x0, payment: 0, paymentReceiver: 0x0
)
```

**PauseGuard:**

```
PauseGuard(admin: 0x73d1C7dc9CEb14660Cf1E9BB29F80ECF9E97D774, pauser: <PauseSafe>)
```

`paused` starts `false`. Verify `supportsInterface(0xe6d7a83a)` and `supportsInterface(0x01ffc9a7)`.

---

## Step 2 — deploy DelayOwnerSafe

**DelayOwnerSafe (5-of-11),** same factory and singleton:

```
setup(
  owners:          the 11 Proposer Safe signers (section 4 of the plan),
  threshold:       5,
  to:              0x0,      // NewRoles does not exist yet
  data:            "",
  fallbackHandler: 0x0,
  paymentToken:    0x0, payment: 0, paymentReceiver: 0x0
)
```

Modules can't be enabled during `setup`: NewRoles takes this Safe's address as its `target`, so the Safe has to exist first.

---

## Step 3 — deploy and fully configure NewRoles

Deployer key only. NewRoles is a module on nothing throughout, so its permissions can't be used yet.

**Deploy `SetTxNonceGuard(delay: 0x0C19d8A4…)`.**

**Deploy NewRoles** — the Term fork without `callTargetFunctionWithRole`, `Permissions` linked at `0xA4af4763…`:

```
Roles(
  owner:  <deployer>,
  avatar: 0xb8A1dF43c1c88b13937C0c5CEBbAd15830cAeC03,
  target: <DelayOwnerSafe>
)
```

**Configure in this order** (all `onlyOwner`, so the deployer can batch them or send them one at a time):

| # | Call | Result |
|---|---|---|
| 1 | `setMultisend(0x40A2aCCbd92BCA938b02010E17A5b8929b49130D)` | slot 105 |
| 2 | `scopeTarget(1, 0x0C19d8A4…)` | role 1 target → `Clearance.Function` |
| 3 | `scopeAllowFunction(1, 0x0C19d8A4…, 0x46ba2307, ExecutionOptions.None)` | only `setTxNonce` allowed |
| 4 | `assignRoles(0x2B715634…, [1], [true])` | Governor becomes a member of role 1 |
| 5 | `setDefaultRole(0x2B715634…, 1)` | slot 106 |
| 6 | `enableModule(0x2B715634…)` | Governor becomes the sole module |
| 7 | `setGuard(<SetTxNonceGuard>)` | slot 101 |
| 8 | `transferOwnership(0xb8A1dF43…)` | owner becomes the Ownerless Safe |

`scopeTarget` must precede `scopeAllowFunction`: scoping the target sets clearance to `Function`, and the function entry is what then permits `setTxNonce`. Keep `transferOwnership` last, since every earlier call needs the deployer to still be the owner.

Ownership lands on the Ownerless Safe without it signing anything — `transferOwnership` is the deployer's call.

---

## Step 4 — DelayOwnerSafe enables NewRoles

One DelayOwnerSafe transaction (5 of 11):

```
enableModule(<NewRoles>)
```

Inert for now: this Safe owns nothing until the batch in step 6 executes, so NewRoles can execute nothing through it.

---

## Step 5 — Proposer Safe queues the migration batch

One Proposer Safe transaction (5 of 11) to the Delay:

```
Delay.execTransactionFromModule(
  to:        0x40A2aCCbd92BCA938b02010E17A5b8929b49130D,   // MultiSendCallOnly v1.3.0
  value:     0,
  data:      multiSend(<the six calls below>),
  operation: DelegateCall (1)
)
```

Each inner call is packed as `operation(uint8=0) ‖ to(address) ‖ value(uint256=0) ‖ dataLength(uint256) ‖ data`, and every one of them runs with `msg.sender` = the Ownerless Safe:

| # | Target | Call | Why it's allowed |
|---|---|---|---|
| 1 | old Roles | `enableModule(0xb8A1dF43…)` | `onlyOwner`; the Ownerless Safe owns the old Roles |
| 2 | old Roles | `assignRoles(0xb8A1dF43…, [1], [true])` | `onlyOwner` |
| 3 | old Roles | `callTargetFunctionWithRole(0x0C19d8A4…, transferOwnership(<DelayOwnerSafe>), 1)` | `moduleOnly` (call 1) + role 1 membership (call 2) |
| 4 | old Roles | `assignRoles(0xb8A1dF43…, [1], [false])` | `onlyOwner` |
| 5 | old Roles | `disableModule(0x…01, 0xb8A1dF43…)` | `onlyOwner` |
| 6 | Ownerless Safe (self) | `disableModule(0x…01, 0x405b4735…)` | Safe `authorized` — `msg.sender` is the Safe itself |

Notes on the batch:

- **Call 3 is the handover.** `callTargetFunctionWithRole` calls the Delay directly from the old Roles, so `msg.sender` at the Delay is the old Roles, which is still its owner at that moment. Re-entering the Delay mid-`executeNextTx` is safe: `txNonce` was already incremented before `exec`, and `transferOwnership` only writes `_owner`.
- **Call 2 is required.** `Permissions.check` reverts with `NoMembership` unless the caller is a member of the role ([Permissions.sol:185](packages/evm/contracts/Permissions.sol:185)), and role 1 has no members today.
- **No new permission is granted.** Role 1's existing target entry for the Delay is `Clearance.Target` with `ExecutionOptions.None`, which covers call 3: value 0, plain call.
- **Calls 4–6 close everything.** The old Roles ends with no members, no modules and no place in the Ownerless Safe's module ring.
- **`prevModule` in calls 5 and 6** is the sentinel `0x0000000000000000000000000000000000000001`. In the Ownerless Safe the ring is `0x1 → old Roles → Delay → 0x1`, and in the old Roles the Ownerless Safe will be the only entry. Re-read both rings when building the calldata.
- **Do not touch the Delay's module entry.** The Delay is the module executing this batch; leave the Ownerless Safe's Delay entry alone.
- **MultiSendCallOnly, not MultiSend.** It rejects inner delegatecalls, and every inner call here is a plain call.

### Encoding

Each inner call, with `0x1111…1111` standing in for the DelayOwnerSafe:

| # | To | Calldata |
|---|---|---|
| 1 | old Roles | `0x610b5925` ‖ `b8A1dF43…` — `enableModule(Ownerless Safe)` |
| 2 | old Roles | `0xa6edf38f` ‖ … — `assignRoles(Ownerless Safe, [1], [true])` |
| 3 | old Roles | `0x9518aaac` ‖ … — `callTargetFunctionWithRole(Delay, 0xf2fde38b ‖ <DelayOwnerSafe>, 1)` |
| 4 | old Roles | `0xa6edf38f` ‖ … — `assignRoles(Ownerless Safe, [1], [false])` |
| 5 | old Roles | `0xe009cfde` ‖ … — `disableModule(0x…01, Ownerless Safe)` |
| 6 | Ownerless Safe | `0xe009cfde` ‖ … — `disableModule(0x…01, old Roles)` |

Each is packed as `00 ‖ to (20 bytes) ‖ value (32 bytes of zero) ‖ dataLength (32 bytes) ‖ data`, the six are concatenated, and the result is wrapped as `multiSend(bytes)` (`0x8d80ff0a`). With the placeholder above the packed blob is 1,334 bytes.

[build_migration_batch.sh](build_migration_batch.sh) builds all of it. Pass the real DelayOwnerSafe address; it prints the inner calls, the packed batch, the `multiSend` calldata, the full calldata for steps 5 and 6, and the `txHash` the Delay will store:

```bash
./build_migration_batch.sh <DelayOwnerSafe>
```

Confirm the printed hash against the chain before the cooldown ends:

```bash
cast call $DELAY 'getTransactionHash(address,uint256,bytes,uint8)(bytes32)' \
  0x40A2aCCbd92BCA938b02010E17A5b8929b49130D 0 <multiSend-calldata> 1 --rpc-url $RPC
```

---

## Step 6 — execute the batch

After the 1-day cooldown, any address with gas calls:

```
Delay.executeNextTx(
  to:        0x40A2aCCbd92BCA938b02010E17A5b8929b49130D,
  value:     0,
  data:      <the exact same multiSend calldata>,
  operation: DelegateCall (1)
)
```

Use the step 6 calldata printed by [build_migration_batch.sh](build_migration_batch.sh) — the same `multiSend` bytes as step 5, re-wrapped for `executeNextTx` (`0xee072baf`). Any difference and the hash check rejects it.

- **Window:** from `t0 + 86400` to `t0 + 172800`, where `t0` is when step 5 was queued. Past that the entry expires and has to be queued again.
- **Result:** the Delay's owner is the DelayOwnerSafe, and the old Roles is retired.

---

## Step 7 — DelayOwnerSafe installs the pause guard

One DelayOwnerSafe transaction (5 of 11):

```
Delay.setGuard(<PauseGuard>)
```

`onlyOwner` on the Delay, which works because step 6 made this Safe the owner. The Governor's veto path is live from here: Governor → NewRoles → DelayOwnerSafe → `Delay.setTxNonce`.

---

## Step 8 — clear the Proposer Safe fallback handler

One Proposer Safe transaction (5 of 11), sent to itself:

```
setFallbackHandler(0x0000000000000000000000000000000000000000)
```

Independent of everything else. Emits `ChangedFallbackHandler`.

---

## Step 9 — verify

Every check is in [verification_plan_ownerless_safe.md](verification_plan_ownerless_safe.md), broken out per step. Run that file's section for a step before starting the next one; section A runs before step 1.

---

## Backing out

- **While the batch is queued,** don't execute it. It expires 2 days after queueing, and `skipExpired()` then clears it. Nothing has changed at that point except the deployments and the inert module entry on the DelayOwnerSafe.
- **After step 6,** the DelayOwnerSafe (5 of 11) owns the Delay and can undo the rest: `setGuard(0x0)` to drop the pause guard, or `transferOwnership` to move the Delay elsewhere.
- **No pause guard exists until step 7.** While the batch is queued the Delay is unguarded, so a queued batch cannot be paused — the way to stop it is to let it expire.
- **The Governor goes live at step 6**, when NewRoles can first reach the Delay. Its 66 existing proposals are all `Defeated`, so none of them can be executed.
