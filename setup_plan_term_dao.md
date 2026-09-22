# Term DAO Governance — Setup Steps

How to reach the target state in [new_governance_plan_term_dao.md](new_governance_plan_term_dao.md). That file is the state to land on; this one is the order of operations. It is the Term DAO counterpart of [setup_plan_ownerless_safe.md](setup_plan_ownerless_safe.md) and follows the same shape, step for step.

## The rule this plan is built on

**The Term DAO signs nothing.** Where its authority is required — it owns the old Roles `0xF3BD578bDa56176Bbf8529B5C945193cF54DB1f5`, which is in turn the Delay's owner — that authority is exercised through the Delay: the Proposer Safe `0xe9dDBBD914063BC703D468e25d0B75148A480cC5` queues a transaction, and after the cooldown anyone executes it. The Delay is an enabled module on the Term DAO, so `executeNextTx` makes the Term DAO perform the call.

This is the same mechanism as the ownerless deployment, chosen here for the same two reasons:

- **A queued Delay transaction can be a batch.** The queue entry carries its own `operation`, so it can be a `DelegateCall` into MultiSendCallOnly. The Term DAO then performs every call in the batch, atomically.
- **The temporary grant opens and closes inside that one batch.** The old Roles gives the Term DAO module status and role membership, uses it to hand the Delay over, then takes both back. Nothing survives the transaction, and any revert rolls back all of it.

**If the Term DAO's signers are reachable and willing to sign,** the same six calls can instead be signed directly as one MultiSend transaction from the Term DAO, and steps 7 and 8 collapse into a single transaction with no cooldown. That variant is noted at the end of step 7. The queued route is written as the spine here because it holds whether or not the Term DAO is signable — section 5 of the target-state plan lists its `ownerCount` and `threshold` as not inspected.

> **This plan carries unverified assumptions about the old Roles `0xF3BD578bDa56176Bbf8529B5C945193cF54DB1f5`.** Unlike the ownerless deployment, its owner, module ring and role configuration are not recorded anywhere in this repository. Step 0 reads them. The migration batch in step 7 is written against the same structure the ownerless old Roles has, and **the reads in step 0 decide whether that structure holds**. Do not build the batch before running them.

## Addresses

| Role | Address |
|---|---|
| Term DAO (avatar/target; owns NewRoles; never signs) | `0xA5Ca93f1fa4dBB6E8141f6Bb22d74a79E07Fa2A1` |
| Delay | `0x80Ce5a0de8B1604e3122BEE73360dC3b987F891A` |
| Delay mastercopy | `0xd54895B1121A2eE3f37b502F507631FA1331BED6` |
| Old Roles (retired by the batch) | `0xF3BD578bDa56176Bbf8529B5C945193cF54DB1f5` |
| Old Governor (retired) | `0xfCCD42fc5C46810F395adfB29739AFF402913dd3` |
| Proposer Safe (2/4) | `0xe9dDBBD914063BC703D468e25d0B75148A480cC5` |
| TERM token | `0xC3d21f79C3120A4fFda7A535f8005a7c297799bF` |
| Roles v1.0.0 mastercopy (audited) | `0x85388a8cd772b19a468F982Dc264C238856939C9` |
| Permissions library (linked inside the mastercopy) | `0x543D1DE69b25420685Ef723842D0087d9b731B06` |
| Zodiac `ModuleProxyFactory` v1.2.0 | `0x000000000000aDdB49795b0f9bA5BC298cDda236` |
| Safe v1.4.1 singleton | `0x41675C099F32341bf84BFc5382aF534df5C7461a` |
| SafeProxyFactory v1.4.1 | `0x4e1DCf7AD4e460CfD30791CCC4F9c8a4f820ec67` |
| MultiSendCallOnly v1.4.1 | `0x9641d764fc13c8B624c04430C7356C1C7C8102e2` |
| CompatibilityFallbackHandler v1.4.1 (cleared in step 10) | `0xfd0732Dc9E303f09fCEf3a7388Ad10A83459Ec99` |
| Module-list sentinel | `0x0000000000000000000000000000000000000001` |
| PauseSafe (2/9) — **reused**, deployed 2026-09-21 | `0x74f3F3dEfdC563bbFC8637BaB2d30596D2817472` |
| Admin Safe — **reused** | `0x73d1C7dc9CEb14660Cf1E9BB29F80ECF9E97D774` |
| To deploy | `PauseGuard`, `DelayOwnerSafe`, `SetTxNonceGuard`, `NewGovernor`, `NewRoles` |

**The two pause Safes are shared with the ownerless deployment; the PauseGuard is not.** `PauseGuard` holds no per-Delay state, so a single instance installed on both Delays would pause both together. This plan deploys a second instance with the same `pauser` and `admin`. `SetTxNonceGuard` likewise cannot be shared: it holds its Delay as an `immutable`.

**Verify the three canonical Safe v1.4.1 addresses on chain before use** — factory, singleton and MultiSendCallOnly — against the `safe-deployments` registry for mainnet. The singleton is corroborated in-repo by section 8 of the target-state plan, which reads slot 0 of the Proposer Safe as `0x41675C099F32341bf84BFc5382aF534df5C7461a`; the other two are not.

## Who signs what

| Step | Signer | Transactions |
|---|---|---|
| 1 | deployer key | 1 — deploy PauseGuard |
| 2 | deployer key | 1 — deploy DelayOwnerSafe |
| 3 | deployer key | 1 — deploy SetTxNonceGuard |
| 4 | deployer key | 1 — deploy NewGovernor |
| 5 | deployer key | 1 deploy + 8 configuration calls on NewRoles |
| 6 | DelayOwnerSafe (2/4) | 1 — enable NewRoles |
| 7 | Proposer Safe (2/4) | 1 — queue the migration batch |
| 8 | anyone (gas only) | 1 — `executeNextTx` after the cooldown |
| 9 | DelayOwnerSafe (2/4) | 1 — set the Delay's guard |
| 10 | Proposer Safe (2/4) | 1 — clear the fallback handler |
| 11 | nobody | reads only |

## How each contract is deployed

| Contract | Method | Factory | Singleton |
|---|---|---|---|
| DelayOwnerSafe | proxy via factory | SafeProxyFactory v1.4.1 `0x4e1DCf7AD4e460CfD30791CCC4F9c8a4f820ec67` | `0x41675C099F32341bf84BFc5382aF534df5C7461a` — read from the Term DAO's slot 0 |
| PauseGuard | direct `CREATE` from the deployer key | none | — |
| SetTxNonceGuard | direct `CREATE` from the deployer key | none | — |
| NewGovernor | direct `CREATE` from the deployer key | none | — |
| NewRoles | EIP-1167 proxy via `deployModule` | Zodiac `ModuleProxyFactory` v1.2.0 `0x000000000000aDdB49795b0f9bA5BC298cDda236` | `0x85388a8cd772b19a468F982Dc264C238856939C9` — Roles v1.0.0, audited |

The DelayOwnerSafe and NewRoles both go through factories. **NewRoles is a module proxy, which is how Zodiac expects modifiers to be deployed** — `ModuleProxyFactory.deployModule` CREATE2-deploys a 45-byte EIP-1167 proxy and calls `setUp` on it in the same transaction. The Delay `0x80Ce5a0de8B1604e3122BEE73360dC3b987F891A` is already exactly this: the same proxy template pointing at Delay mastercopy `0xd54895B1121A2eE3f37b502F507631FA1331BED6`.

The mastercopy `0x85388a8cd772b19a468F982Dc264C238856939C9` is Roles v1.0.0, whose source is byte-identical to the audited commit `454be9d3c26f90221ca717518df002d1eca1845f` referenced in the repo README, with the audited `Permissions` library `0x543D1DE69b25420685Ef723842D0087d9b731B06` already linked inside it. So the executing code is audited and already on chain. **It is the audited code, not this repo's `main`** — the post-audit changes in our tree, notably the `assert(index <= type(uint8).max)` bound in `keyForCompValues`, are absent. ABI and storage layout are identical either way, so every call and slot below is unaffected.

**NewGovernor remains a plain deployment** — `votingPeriod` is a constant override compiled into its bytecode, which is the entire reason this is a redeploy rather than a reconfiguration. There is no mastercopy for it.

For the Safe, the deployment and the `setup` call are **one transaction, not two**: the factory calls `setup` on the fresh proxy inside `createProxyWithNonce`, and the whole thing reverts if that call fails. There is never a moment where an un-`setup` Safe exists on chain.

## Every transaction, in order

18 transactions in total, on the queued route. The direct-signature variant of step 7 replaces transactions 15 and 16 with one Term DAO transaction, for 17. Creating the DelayOwnerSafe through the Safe web app (option C in step 2) adds one, for 19.

| # | Step | Sender | To | Call |
|---|---|---|---|---|
| 1 | 1 | deployer key | — (`CREATE`) | `PauseGuard(admin, pauser)` |
| 2 | 2 | deployer key | SafeProxyFactory `0x4e1DCf7AD4e460CfD30791CCC4F9c8a4f820ec67` | `createProxyWithNonce` → DelayOwnerSafe |
| 3 | 3 | deployer key | — (`CREATE`) | `SetTxNonceGuard(delay)` |
| 4 | 4 | deployer key | — (`CREATE`) | `NewGovernor(...)` |
| 5 | 5 | deployer key | `ModuleProxyFactory` | `deployModule(mastercopy, setUp(owner, avatar, target), salt)` |
| 6 | 5 | deployer key | NewRoles | `setMultisend` |
| 7 | 5 | deployer key | NewRoles | `scopeTarget` |
| 8 | 5 | deployer key | NewRoles | `scopeAllowFunction` |
| 9 | 5 | deployer key | NewRoles | `assignRoles` |
| 10 | 5 | deployer key | NewRoles | `setDefaultRole` |
| 11 | 5 | deployer key | NewRoles | `enableModule` |
| 12 | 5 | deployer key | NewRoles | `setGuard` |
| 13 | 5 | deployer key | NewRoles | `transferOwnership` |
| 14 | 6 | DelayOwnerSafe (2/4) | DelayOwnerSafe | `enableModule(<NewRoles>)` |
| 15 | 7 | Proposer Safe (2/4) | Delay | `execTransactionFromModule` — queue the batch |
| 16 | 8 | anyone (gas only) | Delay | `executeNextTx` |
| 17 | 9 | DelayOwnerSafe (2/4) | Delay | `setGuard(<PauseGuard>)` |
| 18 | 10 | Proposer Safe (2/4) | Proposer Safe | `setFallbackHandler(0x0000000000000000000000000000000000000000)` |

Transactions 6–13 are eight separate transactions from an EOA. An EOA cannot batch them natively; batching would mean routing them through a multicall helper that the deployer owns, which is optional and changes nothing about the resulting state.

Total Term DAO transactions: **zero**.

---

## Step 0 — read the old Roles, then rehearse on a fork

### The reads that decide the batch

These four facts are what step 7 is built on and none of them are recorded in this repository. Run them first; the results change the batch.

```bash
export RPC=<rpc>
export TERMDAO=0xA5Ca93f1fa4dBB6E8141f6Bb22d74a79E07Fa2A1
export DELAY=0x80Ce5a0de8B1604e3122BEE73360dC3b987F891A
export OLDROLES=0xF3BD578bDa56176Bbf8529B5C945193cF54DB1f5
export OLDGOV=0xfCCD42fc5C46810F395adfB29739AFF402913dd3
export PROPOSER=0xe9dDBBD914063BC703D468e25d0B75148A480cC5
export SENTINEL=0x0000000000000000000000000000000000000001

cast call $OLDROLES 'owner()(address)' --rpc-url $RPC
cast call $OLDROLES 'getModulesPaginated(address,uint256)(address[],address)' $SENTINEL 10 --rpc-url $RPC
cast call $TERMDAO  'getModulesPaginated(address,uint256)(address[],address)' $SENTINEL 10 --rpc-url $RPC
cast code $OLDROLES --rpc-url $RPC | grep -c 639518aaac     # callTargetFunctionWithRole present?

# role 1 target entry for the Delay on the old Roles.
# roles[1] base = keccak256(abi.encode(uint16(1), uint256(107))); targets is base+1, members is base+0.
# The slot is key-derived, so this literal holds for any Roles deployment:
cast storage $OLDROLES 0x58378b12c62a352499987fe2cb0fd9b730ba7a8565e57928546a499547532ee8 --rpc-url $RPC
```

| Read | The batch assumes | If it differs |
|---|---|---|
| `OLDROLES.owner()` | `0xA5Ca93f1fa4dBB6E8141f6Bb22d74a79E07Fa2A1` (Term DAO) | **Stop.** Calls 1, 2, 4 and 5 are `onlyOwner`; nothing in this plan works and the handover needs a different actor entirely. |
| `callTargetFunctionWithRole` in bytecode | present | **Stop and rewrite call 3.** Without it the old Roles has no way to call the Delay on the Term DAO's behalf; the handover would have to go through `execTransactionWithRole` with the Term DAO as an enabled module, which changes calls 1–4. |
| role 1 `targets[Delay]` | non-zero — a `Clearance.Target` or `Clearance.Function` entry covering `transferOwnership` | **Add two calls to the batch:** `scopeTarget(1, Delay)` and `scopeAllowFunction(1, Delay, 0xf2fde38b, ExecutionOptions.None)` before call 3, and `revokeTarget(1, Delay)` after it. Use a role with no existing members if one is free. |
| `TERMDAO` module ring | contains the Delay; may or may not contain the old Roles | Call 6 removes the old Roles from the ring. **If the old Roles is not in the ring, drop call 6.** If it is, `prevModule` is whatever precedes it in the ring as read above — not necessarily the sentinel. |

`prevModule` in call 5 **is** the sentinel: `enableModule` inserts at the head of the ring, so the Term DAO is the first entry at the moment call 5 runs, whatever else the old Roles has enabled.

### Starting state

```bash
cast call $DELAY 'owner()(address)' --rpc-url $RPC                      # 0xF3BD578bDa56176Bbf8529B5C945193cF54DB1f5
cast call $DELAY 'guard()(address)' --rpc-url $RPC                      # 0x0000000000000000000000000000000000000000
cast call $DELAY 'txNonce()(uint256)' --rpc-url $RPC                    # 8
cast call $DELAY 'queueNonce()(uint256)' --rpc-url $RPC                 # 8 — queue empty
cast call $DELAY 'txCooldown()(uint256)' --rpc-url $RPC                 # 604800 (7 days)
cast call $DELAY 'txExpiration()(uint256)' --rpc-url $RPC               # 172800 (2 days)
cast call $DELAY 'getModulesPaginated(address,uint256)(address[],address)' $SENTINEL 10 --rpc-url $RPC   # [Proposer Safe]
cast storage $TERMDAO 0 --rpc-url $RPC                                  # 0x00000000000000000000000041675c099f32341bf84bfc5382af534df5c7461a
```

### Fork rehearsal

```bash
anvil --fork-url <rpc> --fork-block-number <recent>
```

Impersonate the Proposer Safe and the DelayOwnerSafe signers, run steps 1–10 including the cooldown warp, then run step 11's checks. Confirm before mainnet:

- **`PauseGuard.supportsInterface(0xe6d7a83a)` returns `true`.** `Guardable.setGuard` rejects a guard that doesn't, which would revert step 9.
- **`SetTxNonceGuard.supportsInterface(0xe6d7a83a)` returns `true` and `delay()` is `0x80Ce5a0de8B1604e3122BEE73360dC3b987F891A`.** The interface check gates `Roles.setGuard` in step 5. The `delay` check has no on-chain gate at all: the guard is pinned to whatever address it was constructed with, `setGuard` accepts it either way, and a guard pinned to the wrong Delay — the ownerless deployment's `0x0C19d8A404079d71E5CA3e32fE3f758Ab543ACdf` being the obvious slip — leaves the veto path dead with nothing reverting to say so.
- **The Delay's queue is empty** (`txNonce() == queueNonce()`, both `8` today). The queue is strictly FIFO, so anything queued ahead of the migration batch has to clear first. **The cooldown here is 7 days, not 1** — a stray entry queued ahead of the batch delays it by a week.
- **The exact batch calldata.** `executeNextTx` re-hashes `(to, value, data, operation)` and reverts unless it matches, so save the bytes queued in step 7 verbatim.

---

## Step 1 — deploy PauseGuard

A second instance, separate from the ownerless deployment's, with the same two Safes in the two roles:

```
PauseGuard(
  admin:  0x73d1C7dc9CEb14660Cf1E9BB29F80ECF9E97D774,
  pauser: 0x74f3F3dEfdC563bbFC8637BaB2d30596D2817472
)
```

`0x74f3F3dEfdC563bbFC8637BaB2d30596D2817472` is the 2-of-9 PauseSafe listed in the addresses table, already deployed 2026-09-21 and shared with [setup_plan_ownerless_safe.md](setup_plan_ownerless_safe.md). Do not deploy a new one. `paused` starts `false`. Verify before moving on:

```bash
cast call <PauseGuard> 'supportsInterface(bytes4)(bool)' 0xe6d7a83a --rpc-url $RPC   # true
cast call <PauseGuard> 'supportsInterface(bytes4)(bool)' 0x01ffc9a7 --rpc-url $RPC   # true
cast call <PauseGuard> 'paused()(bool)' --rpc-url $RPC                               # false
cast call <PauseGuard> 'pauser()(address)' --rpc-url $RPC                            # 0x74f3F3dEfdC563bbFC8637BaB2d30596D2817472
cast call <PauseGuard> 'admin()(address)' --rpc-url $RPC                             # 0x73d1C7dc9CEb14660Cf1E9BB29F80ECF9E97D774
```

**This address must differ from the ownerless deployment's PauseGuard.** Installing that one here would wire both Delays to a single `paused` flag: one `pause()` would stop both systems, and one `unpause()` would restart both. Diff the two addresses explicitly before step 9.

The interface check is not cosmetic: `Guardable.setGuard` requires it, and this guard is not installed until step 9, so a failure here would otherwise surface eight steps later.

---

## Step 2 — deploy DelayOwnerSafe

**DelayOwnerSafe (2-of-4).** One transaction, to the factory:

```
SafeProxyFactory v1.4.1  0x4e1DCf7AD4e460CfD30791CCC4F9c8a4f820ec67

  createProxyWithNonce(                       // 0x1688f0b9
    _singleton:  0x41675C099F32341bf84BFc5382aF534df5C7461a,   // Safe v1.4.1, read from the Term DAO's slot 0
    initializer: <the setup calldata below>,
    saltNonce:   <pick one; record it>
  )
```

`initializer` is the `setup` calldata the factory then calls on the new proxy. Build it verbatim — the Safe's address is derived from it, so a single byte's difference is a different Safe:

| `setup` argument | Value | Why |
|---|---|---|
| `_owners` | the 4 Proposer Safe signers, below | same set as the Proposer Safe |
| `_threshold` | `2` | matches the Proposer Safe |
| `to` / `data` | `0x0000000000000000000000000000000000000000` / `0x` | NewRoles does not exist yet |
| `fallbackHandler` | `0x0000000000000000000000000000000000000000` | — |
| `paymentToken` / `payment` / `paymentReceiver` | `0x0000000000000000000000000000000000000000` / `0` / `0x0000000000000000000000000000000000000000` | no refund |

`setup` is **not** a second transaction: `createProxyWithNonce` calls it on the proxy and reverts the whole deployment if it fails.

### Ready to send

`initializer` — needed by both options:

```
0xb63e800d00000000000000000000000000000000000000000000000000000000000001000000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001a00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000400000000000000000000000012c624c8bb9eab191055f8f11fb3c02c04c52c0700000000000000000000000039060471de4da1e9f0ebbd3adf36b905a830d24800000000000000000000000098e061ac25b5cce88bf315c52f488fd7ca46dd190000000000000000000000003dfcb8ca9d086fd90e949743f06199db5abdd1020000000000000000000000000000000000000000000000000000000000000000
```

#### Option A — script (viem)

```ts
import { createPublicClient, createWalletClient, http, parseAbi, encodeFunctionData } from 'viem'
import { privateKeyToAccount } from 'viem/accounts'
import { mainnet } from 'viem/chains'

const FACTORY   = '0x4e1DCf7AD4e460CfD30791CCC4F9c8a4f820ec67' as const   // SafeProxyFactory v1.4.1
const SINGLETON = '0x41675C099F32341bf84BFc5382aF534df5C7461a' as const
const ZERO      = '0x0000000000000000000000000000000000000000' as const

const OWNERS = [
  '0x12c624C8BB9EAb191055f8f11Fb3C02c04c52c07',
  '0x39060471dE4Da1e9f0ebbd3ADf36B905a830d248',
  '0x98E061AC25B5ccE88bf315C52f488fD7Ca46dd19',
  '0x3dfcB8CA9D086fD90e949743F06199dB5aBDD102',
] as const
const THRESHOLD  = 2n
const SALT_NONCE = 0n

const safeAbi = parseAbi([
  'function setup(address[] _owners, uint256 _threshold, address to, bytes data, address fallbackHandler, address paymentToken, uint256 payment, address paymentReceiver)',
])
const factoryAbi = parseAbi([
  'function createProxyWithNonce(address _singleton, bytes initializer, uint256 saltNonce) returns (address proxy)',
])

const initializer = encodeFunctionData({
  abi: safeAbi,
  functionName: 'setup',
  args: [OWNERS, THRESHOLD, ZERO, '0x', ZERO, ZERO, 0n, ZERO],
})

// The Safe's address is derived from these bytes. Refuse to send if they drifted.
const EXPECTED = '0xb63e800d00000000000000000000000000000000000000000000000000000000000001000000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001a00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000400000000000000000000000012c624c8bb9eab191055f8f11fb3c02c04c52c0700000000000000000000000039060471de4da1e9f0ebbd3adf36b905a830d24800000000000000000000000098e061ac25b5cce88bf315c52f488fd7ca46dd190000000000000000000000003dfcb8ca9d086fd90e949743f06199db5abdd1020000000000000000000000000000000000000000000000000000000000000000' as const
if (initializer !== EXPECTED) throw new Error('initializer mismatch — do not send')

const account = privateKeyToAccount(process.env.DEPLOYER_KEY as `0x${string}`)
const publicClient = createPublicClient({ chain: mainnet, transport: http(process.env.RPC) })
const wallet = createWalletClient({ account, chain: mainnet, transport: http(process.env.RPC) })

// Dry run first: `result` is the address the proxy will be created at.
const { request, result: predicted } = await publicClient.simulateContract({
  account,
  address: FACTORY,
  abi: factoryAbi,
  functionName: 'createProxyWithNonce',
  args: [SINGLETON, initializer, SALT_NONCE],
})
console.log('will deploy to', predicted)

const hash = await wallet.writeContract(request)
const receipt = await publicClient.waitForTransactionReceipt({ hash })
console.log(receipt.status, predicted)
```

`simulateContract` is the important line: it returns the proxy address without sending anything, and it reverts in advance if the salt is taken. Record `predicted` — it is the DelayOwnerSafe address the rest of this plan refers to.

**The `ProxyCreation` ABI above is deliberately omitted from `factoryAbi`.** v1.3.0 leaves both of its arguments non-indexed; this factory is v1.4.1 and may index `proxy`, and decoding a log with the wrong indexing fails or returns garbage. Using `simulateContract`'s `result` sidesteps the question entirely — if you do want to decode the log, take the event fragment from the deployed factory's own ABI.

#### Option B — Etherscan UI

Go to **https://etherscan.io/address/0x4e1DCf7AD4e460CfD30791CCC4F9c8a4f820ec67#writeContract**, confirm the network selector reads **Ethereum Mainnet**, click **Connect to Web3**, and connect the deployer EOA. Open **`createProxyWithNonce`** and fill the three fields:

| Field | Paste exactly |
|---|---|
| `_singleton (address)` | `0x41675C099F32341bf84BFc5382aF534df5C7461a` |
| `initializer (bytes)` | the `initializer` hex above, `0x` prefix included |
| `saltNonce (uint256)` | `0` |

Then **Write** and confirm in the wallet. The function is non-payable, so there is no ETH amount field — if Etherscan shows one, you are on the wrong function.

The new Safe's address is not shown by the Write tab. Open the transaction, go to **Logs**, and read the `ProxyCreation` event: the proxy is the first `data` word (confirm against the deployed factory's ABI whether v1.4.1 indexes `proxy`; if it does, the address is a topic instead). It also appears on the transaction's **Internal Txns** tab as a contract creation.

Paste the `initializer` as one unbroken string. A newline or a stray space is a different byte string, which derives a different Safe address — and Etherscan will not warn you.

If either option reverts with `Create2 call failed`, that salt is already taken at this factory for this initializer — raise `SALT_NONCE` / `saltNonce` by one and retry.

#### Option C — Safe web app, with one follow-up transaction

Unlike the ownerless plan's two Safes, this one **can** be created in the Safe web app: it wants v1.4.1, which is what the app's creation flow deploys.

**Deploying:**

1. Open **https://app.safe.global** and connect the deployer wallet. Confirm the network is **Ethereum Mainnet** before anything else.
2. Choose **Create account** (the app has also called this "Create new Safe").
3. Give it a name. This is an off-chain label stored in your browser — it is not written on chain and nothing in this plan reads it.
4. **Signers — remove the connected wallet first.** The form pre-fills the wallet you connected as the first owner. The deployer EOA is *not* one of this Safe's four signers, so delete that row, then add the four below. Getting this wrong hands the deployer key a permanent seat on the Safe that owns the Delay.
5. Set the threshold to **2 out of 4**.
6. On the review screen, pay the fee **from the connected wallet** rather than any sponsored or relayed option. Relayed creation can route through a different factory or initializer than the plain path, which is the one thing this step needs to stay predictable.
7. **Create**, confirm in the wallet, and wait for the transaction to land.
8. Copy the deployed address. The app prefixes it with the chain shortname, as `eth:` followed by the address — **drop that prefix**; every other place in this plan wants the bare 20-byte address.

**Then, before step 5, verify what you actually got:**

```bash
export DELAYOWNER=<the address from step 8, without the eth: prefix>
cast code $DELAYOWNER --rpc-url $RPC | head -c 20        # must not be 0x — see the counterfactual note below
cast storage $DELAYOWNER 0 --rpc-url $RPC                # must equal: cast storage $TERMDAO 0
cast call $DELAYOWNER 'getThreshold()(uint256)' --rpc-url $RPC   # 2
cast call $DELAYOWNER 'getOwners()(address[])' --rpc-url $RPC    # exactly the 4 below, no deployer EOA
```

**Then clear the fallback handler** — one DelayOwnerSafe transaction, 2 of 4, sent to itself. The app has no settings toggle for this, so use the **Transaction Builder** app (Apps → Transaction Builder):

| Field | Value |
|---|---|
| To / contract address | the DelayOwnerSafe's own address |
| ETH value | `0` |
| Method | `setFallbackHandler(address)` — or toggle custom data and paste the calldata below |
| `handler (address)` | `0x0000000000000000000000000000000000000000` |

Raw calldata, if you enter it directly:

```
0xf08a03230000000000000000000000000000000000000000000000000000000000000000
```

Two signers approve and execute it. Confirm afterwards:

```bash
cast storage $DELAYOWNER 0x6c9a6c4a39284e37ed1cf53d337577d14212a4870fb976a4366c693b939918d5 --rpc-url $RPC   # 0x0
```

That slot is the same fallback-handler slot step 10 clears on the Proposer Safe.

**Why that last transaction is needed** — what the app will not match, and what to do about each:

| Difference | Matters? | Action |
|---|---|---|
| Installs the CompatibilityFallbackHandler; this plan's initializer sets it to `0x0000000000000000000000000000000000000000` | **Yes** — step 10 clears exactly this slot on the Proposer Safe as a hardening step; leaving one on the DelayOwnerSafe contradicts that | The Transaction Builder transaction above, before step 6 |
| Pre-fills the connected wallet as an owner | **Yes** — it would leave the deployer EOA as a signer on the Safe that owns the Delay | Remove that row at creation (step 4 above); the `getOwners()` check catches it if you miss it |
| Picks its own `saltNonce`, so a different address | No | Nothing references this Safe's address until step 5 sets it as NewRoles' `target`, which happens after it exists. Read the address off the app and carry it forward. |
| Picks the version itself — no selector | Verify | Section C of the verification plan already requires slot 0 to equal the Term DAO's slot 0. Run that check; if Safe has moved its default off v1.4.1, this route is out. |

Two things to confirm rather than assume, because they would break the plan rather than inconvenience it:

- **The Safe must actually be deployed on chain, not counterfactual.** The app can create a Safe lazily, deploying it only when it first executes something. NewRoles takes this Safe as its `target` in step 5 and it must sign in step 6, so an undeployed address will not do. Convenient resolution: the `setFallbackHandler` transaction above *is* this Safe's first transaction, so executing it deploys a counterfactual Safe as a side effect. Either way, re-run `cast code $DELAYOWNER` after it and confirm the address has code before starting step 5.
- **Decode the initializer the app actually used** and confirm the rest matches, since the app's flows vary:

```bash
cast tx <creation-tx-hash> input --rpc-url $RPC \
  | xargs cast decode-calldata 'createProxyWithNonce(address,bytes,uint256)'
# then decode the initializer it prints:
cast decode-calldata 'setup(address[],uint256,address,bytes,address,address,uint256,address)' <initializer>
# _owners: the 4 below | _threshold: 2 | to,data: zero | paymentToken,payment,paymentReceiver: zero
```

Taking this route makes the plan 19 transactions rather than 18 — the extra one is the `setFallbackHandler` above. Options A and B avoid it by never installing a handler in the first place.

| # | Signer |
|---|---|
| 1 | `0x12c624C8BB9EAb191055f8f11Fb3C02c04c52c07` |
| 2 | `0x39060471dE4Da1e9f0ebbd3ADf36B905a830d248` |
| 3 | `0x98E061AC25B5ccE88bf315C52f488fD7Ca46dd19` |
| 4 | `0x3dfcB8CA9D086fD90e949743F06199dB5aBDD102` |

Copy the singleton from `cast storage 0xA5Ca93f1fa4dBB6E8141f6Bb22d74a79E07Fa2A1 0` verbatim rather than picking from a deployment list: v1.4.1 ships `Safe` and `SafeL2` at different addresses and only the former is in use here. Expected `0x41675C099F32341bf84BFc5382aF534df5C7461a`.

Modules can't be enabled during `setup`: NewRoles takes this Safe's address as its `target`, so the Safe has to exist first.

```bash
diff <(cast call <DelayOwnerSafe> 'getOwners()(address[])' --rpc-url $RPC | tr ',' '\n' | sort) \
     <(cast call $PROPOSER        'getOwners()(address[])' --rpc-url $RPC | tr ',' '\n' | sort)
```

---

## Step 3 — deploy SetTxNonceGuard

```
SetTxNonceGuard(delay: 0x80Ce5a0de8B1604e3122BEE73360dC3b987F891A)
```

The Delay `0x80Ce5a0de8B1604e3122BEE73360dC3b987F891A`, not the DelayOwnerSafe. The guard sees the final destination of a module transaction, which is the Delay; the DelayOwnerSafe is the avatar in between and never appears as `to`.

No storage: `delay` is `immutable` and lives in the bytecode, so `cast storage` shows nothing and the getter is the only way to read it. Check it before step 5 installs the guard:

```bash
cast call <SetTxNonceGuard> 'delay()(address)' --rpc-url $RPC                            # 0x80Ce5a0de8B1604e3122BEE73360dC3b987F891A
cast call <SetTxNonceGuard> 'supportsInterface(bytes4)(bool)' 0xe6d7a83a --rpc-url $RPC  # true
cast call <SetTxNonceGuard> 'supportsInterface(bytes4)(bool)' 0x01ffc9a7 --rpc-url $RPC  # true
```

**The `delay()` check is the one that matters.** Nothing on chain enforces it: `Roles.setGuard` only checks `supportsInterface`, so a guard constructed against the ownerless Delay `0x0C19d8A404079d71E5CA3e32fE3f758Ab543ACdf` installs cleanly and then rejects every transaction NewGovernor sends, with the failure only visible the first time a veto is attempted.

ABI-encoded constructor argument, to append to the creation bytecode:

```
0x00000000000000000000000080ce5a0de8b1604e3122bee73360dc3b987f891a
```

Independent of every other deployment — it takes only the Delay address, which is live today. It sits here because step 5 installs it.

---

## Step 4 — deploy NewGovernor

### The constructor takes one argument

Read off the deployed old Governor `0xfCCD42fc5C46810F395adfB29739AFF402913dd3`, whose verified ABI gives:

```json
{"inputs":[{"internalType":"contract IVotes","name":"_token","type":"address"}],
 "stateMutability":"nonpayable","type":"constructor"}
```

```solidity
constructor(IVotes _token)
```

| # | Parameter | Type | Value |
|---|---|---|---|
| 0 | `_token` | `address` (`contract IVotes`) | `0xC3d21f79C3120A4fFda7A535f8005a7c297799bF` — TERM |

ABI-encoded constructor argument, to append to the creation bytecode:

```
0x000000000000000000000000c3d21f79c3120a4ffda7a535f8005a7c297799bf
```

That is byte-for-byte what the old Governor was deployed with — its Etherscan "Constructor Arguments" section decodes to `Arg [0] : _token (address): 0xC3d21f79C3120A4fFda7A535f8005a7c297799bF`. The new deployment passes the same token.

### Everything else is compiled in, not passed in

The source is `contracts/TermFinanceGovernor.sol` in the **term-finance-ops-contracts** repo:

```solidity
contract TermFinanceGovernor is GovernorVotes, GovernorCountingSimple {

    constructor(IVotes _token) Governor("TermFinanceGovernor") GovernorVotes(_token) {}

    function votingDelay()        public view virtual override returns (uint256) { return 0; }
    function votingPeriod()       public view virtual override returns (uint256) { return 7 days; }   // <- the line to change
    function quorumNumerator()    public pure            returns (uint256) { return 1; }
    function quorumDenominator()  public pure            returns (uint256) { return 100; }
    function proposalThreshold()  public view virtual override returns (uint256) { return 1000e18; }
    function quorum(uint256 timepoint) public view virtual override returns (uint256) {
        return (token().getPastTotalSupply(timepoint) * quorumNumerator()) / quorumDenominator();
    }
}
```

**There is no constructor parameter for `votingPeriod`, and none for any other governance setting.** Every one of them is a hardcoded return value. `GovernorSettings` and `GovernorVotesQuorumFraction` are not inherited, which is why there is nothing to configure at deploy time.

This is also how every existing Term governor was produced — that repo's history on this one file is a series of edits to these literals:

| Commit | Message | Produced |
|---|---|---|
| `1ed8ea4` | gov 7 mintues voting period | a test governor |
| `0160332` | updated mainnet governor with 1000 T proposal threshold and 22 hr voting period | `0x2B715634134220ffeEE9458b4e34E41A41418607` — the ownerless deployment's Governor, `79200` |
| `b2832e4` | 7 day voting period on gov for token | `0xfCCD42fc5C46810F395adfB29739AFF402913dd3` — this plan's old Governor, `604800` |

### Deploying the new Governor

#### 1. Change the one line

In `term-finance-ops-contracts/contracts/TermFinanceGovernor.sol`:

```diff
-    function votingPeriod() public view virtual override returns (uint256) { return 7 days; }
+    function votingPeriod() public view virtual override returns (uint256) { return 5 days; }
```

`5 days` is `432000`. Commit it on a branch — the deployed bytecode has to be reproducible from a commit, and the three governors above are each identifiable by theirs.

**If more governors with differing periods are coming,** consider taking `votingPeriod` as a constructor argument instead:

```solidity
uint256 private immutable _votingPeriod;
constructor(IVotes _token, uint256 votingPeriod_) Governor("TermFinanceGovernor") GovernorVotes(_token) {
    _votingPeriod = votingPeriod_;
}
function votingPeriod() public view virtual override returns (uint256) { return _votingPeriod; }
```

That ends the edit-and-redeploy cycle, but it is a different contract: the bytecode no longer matches any existing governor, the constructor takes two arguments instead of one, and "identical to the old Governor except `votingPeriod`" stops being true. It is the better engineering answer and the worse answer for this migration's reviewability. Pick deliberately — this plan assumes the one-line edit.

#### 2. Pin the build — the repo's settings do not currently match the deployed Governor

This is the step most likely to be skipped and the one most likely to cause trouble. Building the repo as it stands today does **not** reproduce the old Governor:

| | Deployed `0xfCCD42fc5C46810F395adfB29739AFF402913dd3` | term-finance-ops-contracts today |
|---|---|---|
| solc | `v0.8.20+commit.a1b79de6` | `0.8.24` (`hardhat.config.ts`) |
| EVM version | `paris` | `cancun` |
| Optimizer | disabled | not configured, so disabled — matches |
| `@openzeppelin/contracts` | see below | `^5.6.1`, resolving to `5.6.1` |

`cancun` matters on its own: solc emits opcodes under it (`MCOPY`, transient storage) that `paris` has no equivalent for, so the bytecode differs far beyond the line you changed.

**Settle the OpenZeppelin version before building — the sources disagree.** The target-state plan says v5.0.2; the ops repo's `package.json` at commit `b2832e4`, the commit that produced this very Governor, pinned `^5.2.0`; HEAD floats to `^5.6.1`. Do not trust any of the three. The old Governor is verified on Etherscan in Solidity Standard JSON-Input format, which embeds the exact sources it was compiled from — export that and read the OpenZeppelin version out of it, then pin that version exactly, without a caret.

Then set `hardhat.config.ts` to match:

```ts
solidity: {
  compilers: [
    {
      version: "0.8.20",
      settings: {
        evmVersion: "paris",
        optimizer: { enabled: false },
        outputSelection: { "*": { "*": ["storageLayout"] } },
      },
    },
  ],
},
```

If that config change would disturb other contracts in the repo, add `0.8.20`/`paris` as a second compiler entry with an `overrides` entry for `contracts/TermFinanceGovernor.sol` rather than changing the global default.

#### 3. Build

```bash
cd ../term-finance-ops-contracts
yarn install            # after pinning @openzeppelin/contracts to the exact version
yarn hardhat compile
```

Confirm the artifact reports the settings you intended before going further — a silent fall back to the old compiler entry is the failure mode here:

```bash
jq -r '.metadata | fromjson | {compiler: .compiler.version, evmVersion: .settings.evmVersion, optimizer: .settings.optimizer}' \
  artifacts/contracts/TermFinanceGovernor.sol/TermFinanceGovernor.json
# compiler 0.8.20+commit.a1b79de6 | evmVersion paris | optimizer.enabled false
```

#### 4. Deploy

The repo already has the script, and it takes the token from the environment:

```bash
MAINNET_RPC=<rpc> \
DEPLOYER_WALLET=<deployer private key> \
TOKEN_ADDRESS=0xC3d21f79C3120A4fFda7A535f8005a7c297799bF \
yarn hardhat run scripts/deploy-governor-contracts.ts --network mainnet
```

`scripts/deploy-governor-contracts.ts` reads `TOKEN_ADDRESS`, gets a signer from `DEPLOYER_WALLET` via the `mainnet` network entry, calls `governorFactory.deploy(tokenAddress)` — the single constructor argument — and prints the deployment transaction and the address. Record the address as `<NewGovernor>`.

#### 5. Verify the source on Etherscan

```bash
yarn hardhat verify --network mainnet <NewGovernor> 0xC3d21f79C3120A4fFda7A535f8005a7c297799bF
```

The constructor argument is repeated here because Etherscan needs it to reproduce the creation code.

#### 6. Assert the settings actually landed

Nothing in the constructor enforces any of this, so read it all back:

```bash
export NEWGOV=<NewGovernor>
export OLDGOV=0xfCCD42fc5C46810F395adfB29739AFF402913dd3
cast call $NEWGOV 'votingPeriod()(uint256)' --rpc-url $RPC        # 432000  <- the reason this redeploy exists
cast call $OLDGOV 'votingPeriod()(uint256)' --rpc-url $RPC        # 604800  <- for the record
cast call $NEWGOV 'votingDelay()(uint256)' --rpc-url $RPC         # 0
cast call $NEWGOV 'proposalThreshold()(uint256)' --rpc-url $RPC   # 1000000000000000000000
cast call $NEWGOV 'quorumNumerator()(uint256)' --rpc-url $RPC     # 1
cast call $NEWGOV 'quorumDenominator()(uint256)' --rpc-url $RPC   # 100
cast call $NEWGOV 'name()(string)' --rpc-url $RPC                 # "TermFinanceGovernor"
cast call $NEWGOV 'token()(address)' --rpc-url $RPC               # 0xC3d21f79C3120A4fFda7A535f8005a7c297799bF
cast call $NEWGOV 'CLOCK_MODE()(string)' --rpc-url $RPC           # mode=timestamp&from=default
cast call $NEWGOV 'timelock()(address)' --rpc-url $RPC            # must revert — no timelock extension
```

Then check that nothing *else* changed, which is what step 2 was for:

```bash
diff <(cast code $NEWGOV --rpc-url $RPC | fold -w2 | tr '\n' ' ') \
     <(cast code $OLDGOV --rpc-url $RPC | fold -w2 | tr '\n' ' ') | head
```

Expect a small, localised difference: the `votingPeriod` constant and the trailing metadata hash. Anything broader means the compiler settings or the OpenZeppelin version still differ, and "identical except `votingPeriod`" is not true of what you just deployed.

**The `votingPeriod` assertion is the one that matters.** Deploying the unedited source succeeds, passes every other check in this plan, and leaves the veto window exactly as short as it is today — the failure stays invisible until someone tries to veto.

#### Alternative to 4: deploy with viem instead of the repo's hardhat script

Same transaction, same single constructor argument — useful if you want the post-deploy assertions to run in the same process and abort loudly rather than as a separate `cast` pass. It still needs the artifact produced by steps 2 and 3, so it does not let you skip pinning the build.

```ts
import { createPublicClient, createWalletClient, http } from 'viem'
import { privateKeyToAccount } from 'viem/accounts'
import { mainnet } from 'viem/chains'
import artifact from '../term-finance-ops-contracts/artifacts/contracts/TermFinanceGovernor.sol/TermFinanceGovernor.json'

// The one and only constructor argument.
const TERM = '0xC3d21f79C3120A4fFda7A535f8005a7c297799bF' as const

// What the recompiled source must produce. Checked after deploy, because
// nothing in the constructor enforces any of it.
const EXPECTED = {
  name: 'TermFinanceGovernor',
  votingDelay: 0n,
  votingPeriod: 432_000n,        // 5 days — the reason this redeploy exists
  proposalThreshold: 1_000_000_000_000_000_000_000n,   // 1,000 TERM
  quorumNumerator: 1n,
  quorumDenominator: 100n,
} as const

const account = privateKeyToAccount(process.env.DEPLOYER_KEY as `0x${string}`)
const publicClient = createPublicClient({ chain: mainnet, transport: http(process.env.RPC) })
const wallet = createWalletClient({ account, chain: mainnet, transport: http(process.env.RPC) })

const hash = await wallet.deployContract({
  abi: artifact.abi,
  bytecode: artifact.bytecode as `0x${string}`,   // hardhat artifact; under foundry this is artifact.bytecode.object
  args: [TERM],                  // constructor(IVotes _token)
})

const receipt = await publicClient.waitForTransactionReceipt({ hash })
const governor = receipt.contractAddress
if (!governor) throw new Error('deployment reverted')
console.log('NewGovernor', governor)

// Read the compiled-in settings back. A wrong source or wrong compiler
// surfaces here, not three steps later when a veto silently fails to land.
const read = (functionName: string) =>
  publicClient.readContract({ address: governor, abi: artifact.abi, functionName })

const actual = {
  name:              await read('name'),
  votingDelay:       await read('votingDelay'),
  votingPeriod:      await read('votingPeriod'),
  proposalThreshold: await read('proposalThreshold'),
  quorumNumerator:   await read('quorumNumerator'),
  quorumDenominator: await read('quorumDenominator'),
  token:             await read('token'),
}
console.table(actual)

if (actual.token !== TERM) throw new Error(`token is ${actual.token}`)
for (const [k, want] of Object.entries(EXPECTED)) {
  const got = (actual as Record<string, unknown>)[k]
  if (got !== want) throw new Error(`${k}: expected ${want}, got ${got}`)
}

// timelock() must not exist — this build has no timelock extension.
await read('timelock').then(
  (t) => { throw new Error(`timelock() returned ${t}; wrong build`) },
  () => console.log('timelock() absent, as expected'),
)
```

Deploying this way still requires `yarn hardhat verify` afterwards, as in 5 above.

All mappings are empty at deploy: no proposal, vote or nonce history carries over from the old Governor. It is a module on nothing until step 5, so it can execute nothing.

Deploy it before step 5 — three of that step's configuration calls take its address.

---

## Step 5 — deploy and configure NewRoles

Deployer key only. NewRoles is a module on nothing throughout, so its permissions can't be used yet.

**Deploy NewRoles** — one call to the Zodiac `ModuleProxyFactory` v1.2.0 `0x000000000000aDdB49795b0f9bA5BC298cDda236`, which CREATE2-deploys the proxy and initializes it in the same transaction:

```
deployModule(
  masterCopy:  0x85388a8cd772b19a468F982Dc264C238856939C9,     # Roles v1.0.0, audited
  initializer: setUp(abi.encode(<deployer>, 0xA5Ca93f1fa4dBB6E8141f6Bb22d74a79E07Fa2A1, <DelayOwnerSafe>)),
  saltNonce:   <any uint256 you pick>
)
```

`setUp` takes `(owner, avatar, target)` — the same three values the old constructor took, in the same order. Owner starts as the **deployer** so the configuration below can run; call 8 hands it to the Term DAO. `<DelayOwnerSafe>` must already exist, so this step stays after the DelayOwnerSafe deployment.

Build the initializer, then send:

```bash
INIT=$(cast calldata 'setUp(bytes)' $(cast abi-encode 'f(address,address,address)' \
  <deployer> 0xA5Ca93f1fa4dBB6E8141f6Bb22d74a79E07Fa2A1 <DelayOwnerSafe>))

cast send 0x000000000000aDdB49795b0f9bA5BC298cDda236 \
  'deployModule(address,bytes,uint256)' 0x85388a8cd772b19a468F982Dc264C238856939C9 $INIT <saltNonce> \
  --rpc-url $RPC --private-key $DEPLOYER
```

**Take `<NewRoles>` from the `ModuleProxyCreation(address indexed proxy, address indexed masterCopy)` event**, not from the transaction's `to`. The address is deterministic — CREATE2 from the factory with salt `keccak256(abi.encodePacked(keccak256(initializer), saltNonce))` — so it can be precomputed, but reading the event is the check that it landed where you expected.

The proxy's code is exactly 45 bytes and holds no logic of its own:

```
363d3d373d3d3d363d73 85388a8cd772b19a468f982dc264c238856939c9 5af43d82803e903d91602b57fd5bf3
```

**This proxy must not reuse the ownerless deployment's `saltNonce` with an identical initializer.** Same factory + same mastercopy + same initializer + same salt is the same CREATE2 address, and the factory reverts with `createProxy: address already taken`. The `avatar`/`target` differ between the two deployments, so the initializers already differ — but keep distinct salts anyway.

Two further consequences. The `Permissions` library is the mastercopy's (`0x543D1DE69b25420685Ef723842D0087d9b731B06`) and cannot be swapped. And **bytecode checks must read the mastercopy, not the proxy** — `cast code <NewRoles>` returns only those 45 bytes.

**Configure in this order** (all `onlyOwner`, so the deployer can batch them or send them one at a time):

| # | Call | Result |
|---|---|---|
| 1 | `setMultisend(0x9641d764fc13c8B624c04430C7356C1C7C8102e2)` | slot 105 |
| 2 | `scopeTarget(1, 0x80Ce5a0de8B1604e3122BEE73360dC3b987F891A)` | role 1 target → `Clearance.Function` |
| 3 | `scopeAllowFunction(1, 0x80Ce5a0de8B1604e3122BEE73360dC3b987F891A, 0x46ba2307, ExecutionOptions.None)` | only `setTxNonce` allowed |
| 4 | `assignRoles(<NewGovernor>, [1], [true])` | NewGovernor becomes a member of role 1 |
| 5 | `setDefaultRole(<NewGovernor>, 1)` | slot 106 |
| 6 | `enableModule(<NewGovernor>)` | NewGovernor becomes the sole module |
| 7 | `setGuard(<SetTxNonceGuard>)` | slot 101 |
| 8 | `transferOwnership(0xA5Ca93f1fa4dBB6E8141f6Bb22d74a79E07Fa2A1)` | owner becomes the Term DAO |

`scopeTarget` must precede `scopeAllowFunction`: scoping the target sets clearance to `Function`, and the function entry is what then permits `setTxNonce`. Keep `transferOwnership` last, since every earlier call needs the deployer to still be the owner.

### Ready to send

Four of the eight are fully determined. The other four take addresses that only exist after steps 3 and 4:

```
1 setMultisend        0x8b95eccd0000000000000000000000009641d764fc13c8b624c04430c7356c1c7c8102e2

2 scopeTarget         0x5e826695000000000000000000000000000000000000000000000000000000000000000100000000000000000000000080ce5a0de8b1604e3122bee73360dc3b987f891a

3 scopeAllowFunction  0x2fcf52d1000000000000000000000000000000000000000000000000000000000000000100000000000000000000000080ce5a0de8b1604e3122bee73360dc3b987f891a46ba2307000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000

4 assignRoles         NOT PRECOMPUTABLE — needs <NewGovernor> from step 4
5 setDefaultRole      NOT PRECOMPUTABLE — needs <NewGovernor> from step 4
6 enableModule        NOT PRECOMPUTABLE — needs <NewGovernor> from step 4
7 setGuard            NOT PRECOMPUTABLE — needs <SetTxNonceGuard> from step 3

8 transferOwnership   0xf2fde38b000000000000000000000000a5ca93f1fa4dbb6e8141f6bb22d74a79e07fa2a1
```

Build the four that are pending once those two addresses exist:

```bash
cast calldata 'assignRoles(address,uint16[],bool[])' <NewGovernor> '[1]' '[true]'
cast calldata 'setDefaultRole(address,uint16)' <NewGovernor> 1
cast calldata 'enableModule(address)' <NewGovernor>
cast calldata 'setGuard(address)' <SetTxNonceGuard>
```

Ownership lands on the Term DAO without it signing anything — `transferOwnership` is the deployer's call.

```bash
cast call <NewRoles> 'owner()(address)' --rpc-url $RPC       # 0xA5Ca93f1fa4dBB6E8141f6Bb22d74a79E07Fa2A1
cast call <NewRoles> 'avatar()(address)' --rpc-url $RPC      # 0xA5Ca93f1fa4dBB6E8141f6Bb22d74a79E07Fa2A1
cast call <NewRoles> 'target()(address)' --rpc-url $RPC      # <DelayOwnerSafe>
cast call <NewRoles> 'multisend()(address)' --rpc-url $RPC   # 0x9641d764fc13c8B624c04430C7356C1C7C8102e2
cast call <NewRoles> 'guard()(address)' --rpc-url $RPC       # <SetTxNonceGuard>
cast code <NewRoles> --rpc-url $RPC | grep -c 639518aaac     # 0 — callTargetFunctionWithRole is not in this build
```

`targets[Delay]` must read `0x0000000000000000000000000000000000000000000000000000000000000002` (`Clearance.Function`), not `0x0000000000000000000000000000000000000000000000000000000000000001`. `0x0000000000000000000000000000000000000000000000000000000000000001` means `allowTarget` was used instead of `scopeTarget`, which would let role 1 call **any** Delay function, including `transferOwnership` and `setGuard`.

---

## Step 6 — DelayOwnerSafe enables NewRoles

One DelayOwnerSafe transaction (2 of 4):

```
enableModule(<NewRoles>)
```

Inert for now: this Safe owns nothing until the batch in step 8 executes, so NewRoles can execute nothing through it.

---

## Step 7 — Proposer Safe queues the migration batch

**Build this only after step 0's reads.** One Proposer Safe transaction (2 of 4) to the Delay:

```
Delay.execTransactionFromModule(
  to:        0x9641d764fc13c8B624c04430C7356C1C7C8102e2,   // MultiSendCallOnly v1.4.1
  value:     0,
  data:      multiSend(<the calls below>),
  operation: DelegateCall (1)
)
```

Each inner call is packed as `operation(uint8=0) ‖ to(address) ‖ value(uint256=0) ‖ dataLength(uint256) ‖ data`, and every one of them runs with `msg.sender` = the Term DAO:

| # | To | Selector | Call | Why it's allowed |
|---|---|---|---|---|
| 1 | `0xF3BD578bDa56176Bbf8529B5C945193cF54DB1f5` | `0x610b5925` | `enableModule(0xA5Ca93f1fa4dBB6E8141f6Bb22d74a79E07Fa2A1)` | `onlyOwner`; the Term DAO owns the old Roles |
| 2 | `0xF3BD578bDa56176Bbf8529B5C945193cF54DB1f5` | `0xa6edf38f` | `assignRoles(0xA5Ca93f1fa4dBB6E8141f6Bb22d74a79E07Fa2A1, [1], [true])` | `onlyOwner` |
| 3 | `0xF3BD578bDa56176Bbf8529B5C945193cF54DB1f5` | `0x9518aaac` | `callTargetFunctionWithRole(0x80Ce5a0de8B1604e3122BEE73360dC3b987F891A, 0xf2fde38b ‖ <DelayOwnerSafe>, 1)` | `moduleOnly` (call 1) + role 1 membership (call 2) |
| 4 | `0xF3BD578bDa56176Bbf8529B5C945193cF54DB1f5` | `0xa6edf38f` | `assignRoles(0xA5Ca93f1fa4dBB6E8141f6Bb22d74a79E07Fa2A1, [1], [false])` | `onlyOwner` |
| 5 | `0xF3BD578bDa56176Bbf8529B5C945193cF54DB1f5` | `0xe009cfde` | `disableModule(0x0000000000000000000000000000000000000001, 0xA5Ca93f1fa4dBB6E8141f6Bb22d74a79E07Fa2A1)` | `onlyOwner` |
| 6 | `0xA5Ca93f1fa4dBB6E8141f6Bb22d74a79E07Fa2A1` | `0xe009cfde` | `disableModule(<prevModule>, 0xF3BD578bDa56176Bbf8529B5C945193cF54DB1f5)` | Safe `authorized` — `msg.sender` is the Safe itself |

Notes on the batch:

- **Call 3 is the handover.** `callTargetFunctionWithRole` calls the Delay directly from the old Roles, so `msg.sender` at the Delay is the old Roles, which is still its owner at that moment. Re-entering the Delay mid-`executeNextTx` is safe: `txNonce` was already incremented before `exec`, and `transferOwnership` only writes `_owner`.
- **Call 2 is required.** `Permissions.check` reverts with `NoMembership` unless the caller is a member of the role ([Permissions.sol:185](packages/evm/contracts/Permissions.sol:185)).
- **Call 3 needs role 1 to already permit the Delay.** Step 0's role-entry read is what confirms this. If it does not, add the scope/revoke pair from step 0's table — that grant is new permission, so it must be revoked in the same batch.
- **Calls 4–6 close everything.** The old Roles ends with no Term DAO membership, no Term DAO module entry, and no place in the Term DAO's module ring.
- **`prevModule` in call 5** is the sentinel `0x0000000000000000000000000000000000000001`, because `enableModule` in call 1 puts the Term DAO at the head of the ring. **`prevModule` in call 6 is whatever step 0's read of the Term DAO ring shows** — it is only the sentinel if the old Roles happens to be the first entry. Re-read the ring when building the calldata.
- **Call 6 is conditional.** If the old Roles is not an enabled module on the Term DAO, drop it; `disableModule` on an absent module reverts and would take the whole batch with it.
- **Do not touch the Delay's module entry on the Term DAO.** The Delay is the module executing this batch; leave it alone.
- **MultiSendCallOnly, not MultiSend.** It rejects inner delegatecalls, and every inner call here is a plain call.
- **The old Governor `0xfCCD42fc5C46810F395adfB29739AFF402913dd3` needs no call.** Once the old Roles is no longer the Delay's owner and no longer a module on the Term DAO, anything still enabled on the old Roles reaches nothing.

Confirm the hash the Delay stored, against the calldata you intend to execute, well before the cooldown ends:

```bash
cast call $DELAY 'getTransactionHash(address,uint256,bytes,uint8)(bytes32)' \
  0x9641d764fc13c8B624c04430C7356C1C7C8102e2 0 <multiSend-calldata> 1 --rpc-url $RPC   # must equal txHash(8)
```

**Direct-signature variant.** If the Term DAO's signers are reachable, the Term DAO can sign the same calls as one MultiSend transaction instead: steps 7 and 8 become a single Term DAO transaction, the 7-day cooldown and the 2-day window disappear, and the rest of the plan is unchanged. The calls, their order and their justifications are identical — only the delivery differs. Nothing else in this document depends on which route is used.

---

## Step 8 — execute the batch

After the 7-day cooldown, any address with gas calls:

```
Delay.executeNextTx(
  to:        0x9641d764fc13c8B624c04430C7356C1C7C8102e2,
  value:     0,
  data:      <the exact same multiSend calldata>,
  operation: DelegateCall (1)
)
```

`executeNextTx` re-hashes `(to, value, data, operation)` and reverts on any difference.

- **Window:** from `t0 + 604800` to `t0 + 777600`, where `t0` is when step 7 was queued — a 2-day window opening a week after queueing. Past that the entry expires and has to be queued again, for another full week.
- **Queue index:** the entry is `8`. After execution `txNonce` and `queueNonce` both read `9`.
- **Result:** the Delay's owner is the DelayOwnerSafe, and the old Roles is retired.

```bash
cast call $DELAY 'owner()(address)' --rpc-url $RPC        # <DelayOwnerSafe>
cast call $DELAY 'txNonce()(uint256)' --rpc-url $RPC      # 9
cast call $OLDROLES 'getModulesPaginated(address,uint256)(address[],address)' $SENTINEL 10 --rpc-url $RPC   # no Term DAO
cast call $TERMDAO  'getModulesPaginated(address,uint256)(address[],address)' $SENTINEL 10 --rpc-url $RPC   # Delay, no old Roles

# the temporary role 1 membership must be gone — old Roles roles[1].members[Term DAO]
cast storage $OLDROLES 0x010526f37f6ace9bfc4207af69d85db61a8f833e1f7714c9fd12b163f2511805 --rpc-url $RPC   # 0x0
```

---

## Step 9 — DelayOwnerSafe installs the pause guard

One DelayOwnerSafe transaction (2 of 4):

```
Delay.setGuard(<PauseGuard>)
```

`onlyOwner` on the Delay, which works because step 8 made this Safe the owner. Check the address against the ownerless deployment's PauseGuard one last time — they must differ.

The veto path is live from here: NewGovernor → NewRoles → DelayOwnerSafe → `Delay.setTxNonce`.

**Veto timing.** `votingDelay()` is `0` and there is no timelock, so a proposal is executable at creation + 5 days, while a queued Delay entry is executable at `t0 + 7 days` and dead at `t0 + 9 days`. The veto window is `[tp + 5d, t0 + 7d)` — two days when the proposal is raised the moment the transaction is queued, shrinking one-for-one with delay, and gone entirely if the proposal is raised more than 48 hours late.

---

## Step 10 — clear the Proposer Safe fallback handler

One Proposer Safe transaction (2 of 4), sent to itself:

```
setFallbackHandler(0x0000000000000000000000000000000000000000)
```

Calldata for the inner transaction the Safe executes against itself:

```
0xf08a03230000000000000000000000000000000000000000000000000000000000000000
```

Independent of everything else. Clears `0xfd0732Dc9E303f09fCEf3a7388Ad10A83459Ec99` (CompatibilityFallbackHandler v1.4.1) and emits `ChangedFallbackHandler`.

```bash
cast storage $PROPOSER 0x6c9a6c4a39284e37ed1cf53d337577d14212a4870fb976a4366c693b939918d5 --rpc-url $RPC   # 0x0
```

---

## Step 11 — verify

Every check is in [verification_plan_term_dao.md](verification_plan_term_dao.md), broken out per step, and packed into [verify_term_dao.sh](verify_term_dao.sh) — one section per step, exit status 0 only if every check in it passed. Run the matching section as each step lands:

| After | Command |
|---|---|
| — (before step 1) | `RPC=$RPC ./verify_term_dao.sh A` |
| step 0 — fork rehearsal | `RPC=$FORK ./verify_term_dao.sh all` |
| step 1 | `RPC=$RPC PAUSEGUARD=$PAUSEGUARD OWNERLESS_PAUSEGUARD=$OWNERLESS_PAUSEGUARD ./verify_term_dao.sh B` |
| step 2 | `RPC=$RPC DELAYOWNER=$DELAYOWNER ./verify_term_dao.sh C` |
| step 3 | `RPC=$RPC SETGUARD=$SETGUARD OWNERLESS_SETGUARD=$OWNERLESS_SETGUARD ./verify_term_dao.sh D` |
| step 4 | `RPC=$RPC NEWGOV=$NEWGOV ./verify_term_dao.sh E` |
| step 5 | `RPC=$RPC NEWROLES=$NEWROLES SETGUARD=$SETGUARD NEWGOV=$NEWGOV DELAYOWNER=$DELAYOWNER OWNERLESS_NEWROLES=$OWNERLESS_NEWROLES ./verify_term_dao.sh F` |
| step 6 | `RPC=$RPC DELAYOWNER=$DELAYOWNER NEWROLES=$NEWROLES ./verify_term_dao.sh G` |
| step 7 | `RPC=$RPC BATCH_TXHASH=0x.. BATCH_CALLDATA=0x.. ./verify_term_dao.sh H` |
| step 8 | `RPC=$RPC DELAYOWNER=$DELAYOWNER TERMDAO_NONCE=12 ./verify_term_dao.sh I` |
| step 9 | `RPC=$RPC PAUSEGUARD=$PAUSEGUARD OWNERLESS_PAUSEGUARD=$OWNERLESS_PAUSEGUARD ./verify_term_dao.sh J` |
| step 10 | `RPC=$RPC ./verify_term_dao.sh K` |
| step 11 | `RPC=$RPC PAUSEGUARD=$PAUSEGUARD DELAYOWNER=$DELAYOWNER SETGUARD=$SETGUARD NEWGOV=$NEWGOV NEWROLES=$NEWROLES TERMDAO_NONCE=12 ./verify_term_dao.sh L` |

`TERMDAO_NONCE` is the Term DAO nonce section A tells you to record — `12` when this was last read on mainnet. Sections I and L compare against it, which is how you prove the Term DAO never signed anything. A check needing an address you have not set reports `SKIP`, not `FAIL`; the fork-only checks in F and J are `SKIP` too.

The sweep below is the same list as section L, kept here for reading without switching files.

| Contract | Check | Expected |
|---|---|---|
| Delay | `owner`, `guard` | DelayOwnerSafe, PauseGuard (this deployment's) |
| Delay | modules | `[0xe9dDBBD914063BC703D468e25d0B75148A480cC5]` |
| Delay | `txCooldown`, `txExpiration` | `604800`, `172800` |
| Delay | `txNonce`, `queueNonce` | equal, `9` |
| Delay | `avatar`, `target` | `0xA5Ca93f1fa4dBB6E8141f6Bb22d74a79E07Fa2A1` (both) |
| NewRoles | `owner`, `avatar`, `target` | Term DAO, Term DAO, DelayOwnerSafe |
| NewRoles | `multisend`, `guard` | MultiSendCallOnly v1.4.1, SetTxNonceGuard |
| NewRoles | `defaultRoles(NewGovernor)`, modules | `1`, `[NewGovernor]` |
| NewRoles | role 1 `targets[Delay]` | `0x0000000000000000000000000000000000000000000000000000000000000002` — `Clearance.Function` |
| NewRoles | `callTargetFunctionWithRole` in bytecode | absent |
| NewGovernor | `votingPeriod`, `votingDelay`, `quorum` | `432000`, `0`, `1e24` |
| SetTxNonceGuard | `delay` | `0x80Ce5a0de8B1604e3122BEE73360dC3b987F891A` |
| PauseGuard | `paused`, `pauser`, `admin` | `false`, `0x74f3F3dEfdC563bbFC8637BaB2d30596D2817472`, `0x73d1C7dc9CEb14660Cf1E9BB29F80ECF9E97D774` |
| PauseGuard | address | **not** the ownerless deployment's PauseGuard |
| DelayOwnerSafe | owners, threshold, modules | the 4 Proposer Safe signers, `2`, `[NewRoles]` |
| Term DAO | modules | contains the Delay, not the old Roles |
| Old Roles | Delay ownership, Term DAO membership (slot `0x010526f37f6ace9bfc4207af69d85db61a8f833e1f7714c9fd12b163f2511805`) | none, `0x0` |
| Proposer Safe | fallback handler slot `0x6c9a6c4a39284e37ed1cf53d337577d14212a4870fb976a4366c693b939918d5` | `0x0` |
| Proposer Safe | owners, threshold | 4, `2` |

---

## Backing out

- **While the batch is queued,** don't execute it. It expires 9 days after queueing, and `skipExpired()` then clears it. Nothing has changed at that point except the deployments and the inert module entry on the DelayOwnerSafe.
- **After step 8,** the DelayOwnerSafe (2 of 4) owns the Delay and can undo the rest: `setGuard(0x0000000000000000000000000000000000000000)` to drop the pause guard, or `transferOwnership` to move the Delay elsewhere.
- **No pause guard exists until step 9.** While the batch is queued the Delay is unguarded, so a queued batch cannot be paused — the way to stop it is to let it expire.
- **NewGovernor goes live at step 8**, when NewRoles can first reach the Delay. It deploys with no proposal history, so there is nothing pending to execute.
- **A pause on this Delay does not pause the ownerless one,** provided step 1 deployed a separate PauseGuard. That separation is the whole reason for the second instance.
