# Term DAO Governance — Verification

Checks for the setup in [setup_plan_term_dao.md](setup_plan_term_dao.md), against the target state in [new_governance_plan_term_dao.md](new_governance_plan_term_dao.md). The ownerless counterpart is [verification_plan_ownerless_safe.md](verification_plan_ownerless_safe.md).

Every check here is a read or a simulation. Nothing in this file sends a transaction. Run each section right after the matching setup step, so a mistake is caught before the next step builds on it. Sections A–F are pre-flight, G–K confirm the migration, and L is the final sweep. There is one section per setup step.

Set these once:

```bash
export RPC=<rpc>
export FORK=http://127.0.0.1:8545   # the step 0 fork
export TERMDAO=0xA5Ca93f1fa4dBB6E8141f6Bb22d74a79E07Fa2A1
export DELAY=0x80Ce5a0de8B1604e3122BEE73360dC3b987F891A
export OLDROLES=0xF3BD578bDa56176Bbf8529B5C945193cF54DB1f5
export OLDGOV=0xfCCD42fc5C46810F395adfB29739AFF402913dd3
export PROPOSER=0xe9dDBBD914063BC703D468e25d0B75148A480cC5
export ADMINSAFE=0x73d1C7dc9CEb14660Cf1E9BB29F80ECF9E97D774
export TERM=0xC3d21f79C3120A4fFda7A535f8005a7c297799bF
export PERMLIB=0x543D1DE69b25420685Ef723842D0087d9b731B06   # linked inside the Roles mastercopy
export SENTINEL=0x0000000000000000000000000000000000000001
export MULTISEND=0x9641d764fc13c8B624c04430C7356C1C7C8102e2
export SINGLETON=0x41675C099F32341bf84BFc5382aF534df5C7461a
# reused from the ownerless deployment
export PAUSESAFE=0x74f3F3dEfdC563bbFC8637BaB2d30596D2817472
export OWNERLESS_PAUSEGUARD=
export OWNERLESS_SETGUARD=
export OWNERLESS_NEWROLES=
# fill in as they are deployed
export PAUSEGUARD= DELAYOWNER= SETGUARD= NEWGOV= NEWROLES=
```

Every `cast` line below is packed into [verify_term_dao.sh](verify_term_dao.sh), which runs a section and exits non-zero if any check in it failed. Prefer the script — it compares against the expected value rather than leaving that to your eye. The commands are kept here so you can see what is being read, and run one on its own when a check fails.

Run the line for the step you just finished. Each section carries its own command below.

| After | Section | Command |
|---|---|---|
| — (before step 1) | A | `RPC=$RPC ./verify_term_dao.sh A` |
| step 0 — fork rehearsal | all | `RPC=$FORK ./verify_term_dao.sh all` |
| step 1 — PauseGuard | B | see section B |
| step 2 — DelayOwnerSafe | C | see section C |
| step 3 — SetTxNonceGuard | D | see section D |
| step 4 — NewGovernor | E | see section E |
| step 5 — NewRoles | F | see section F |
| step 6 — module enabled | G | see section G |
| step 7 — batch queued | H | see section H |
| step 8 — batch executed | I | see section I |
| step 9 — pause guard installed | J | see section J |
| step 10 — fallback handler cleared | K | see section K |
| step 11 — final | L | see section L |

`TERMDAO_NONCE` is the value section A tells you to record — it was `12` when this plan was last checked against mainnet. Sections I and L compare against it, which is how you prove the Term DAO never signed anything. A check needing an address you have not set is reported `SKIP`, not `FAIL`. The fork-only checks in F and J are `SKIP` as well.

Sections F–L describe the post-migration state, so running them early reports `FAIL`, not `SKIP`. That is expected before the step they belong to.

**Role 1 storage slots.** The `roles` mapping is `internal`, so role 1 is read from storage. `roles[1]` base is `keccak256(abi.encode(uint16(1), uint256(107)))` = `0xa775687211c2b3346a0f5a2a0e7590e6c1838453e3785e6dd2a8efd6265ddf15`; within the `Role` struct `members` is base+0, `targets` is base+1, `functions` is base+2. The `functions` key is `bytes32(abi.encodePacked(target, selector))`. The slots below are key-derived, so they hold for any Roles deployment with this layout — the old Roles and NewRoles alike.

| Slot | Meaning |
|---|---|
| `0x010526f37f6ace9bfc4207af69d85db61a8f833e1f7714c9fd12b163f2511805` | `roles[1].members[Term DAO]` |
| `0x58378b12c62a352499987fe2cb0fd9b730ba7a8565e57928546a499547532ee8` | `roles[1].targets[Delay]` |
| `0x5abf4934a98379a2309534eef94a8d2c16aa3d3f8be7f82e740ffba60056c59d` | `roles[1].functions[Delay ‖ 0x46ba2307]` |

`members[<NewGovernor>]` cannot be precomputed — NewGovernor's address is not known until step 4:

```bash
cast index address $NEWGOV 0xa775687211c2b3346a0f5a2a0e7590e6c1838453e3785e6dd2a8efd6265ddf15
```

---

## A. Before anything — starting state

```bash
RPC=$RPC ./verify_term_dao.sh A
```

Confirms the chain still looks like the plan assumed. If any of these differ, stop and re-read the state before deploying.

```bash
cast call $DELAY 'owner()(address)' --rpc-url $RPC                      # 0xF3BD578bDa56176Bbf8529B5C945193cF54DB1f5 (old Roles)
cast call $DELAY 'guard()(address)' --rpc-url $RPC                      # 0x0000000000000000000000000000000000000000
cast call $DELAY 'txNonce()(uint256)' --rpc-url $RPC                    # 8
cast call $DELAY 'queueNonce()(uint256)' --rpc-url $RPC                 # 8 — queue empty
cast call $DELAY 'txCooldown()(uint256)' --rpc-url $RPC                 # 604800
cast call $DELAY 'txExpiration()(uint256)' --rpc-url $RPC               # 172800
cast call $DELAY 'avatar()(address)' --rpc-url $RPC                     # 0xA5Ca93f1fa4dBB6E8141f6Bb22d74a79E07Fa2A1
cast call $DELAY 'target()(address)' --rpc-url $RPC                     # 0xA5Ca93f1fa4dBB6E8141f6Bb22d74a79E07Fa2A1
cast call $DELAY 'getModulesPaginated(address,uint256)(address[],address)' $SENTINEL 10 --rpc-url $RPC   # [Proposer Safe]
cast storage $TERMDAO 0 --rpc-url $RPC                                  # 0x00000000000000000000000041675c099f32341bf84bfc5382af534df5c7461a
cast call $TERMDAO 'nonce()(uint256)' --rpc-url $RPC                    # RECORD THIS — section I compares against it
```

### The four reads that decide the batch

None of these are recorded anywhere in this repository, and step 7's batch is built on all four. This is the same block as step 0 of the setup plan; it is repeated here because it is a verification, not a deployment.

```bash
cast call $OLDROLES 'owner()(address)' --rpc-url $RPC
cast call $OLDROLES 'getModulesPaginated(address,uint256)(address[],address)' $SENTINEL 10 --rpc-url $RPC
cast call $TERMDAO  'getModulesPaginated(address,uint256)(address[],address)' $SENTINEL 10 --rpc-url $RPC
cast code $OLDROLES --rpc-url $RPC | grep -c 639518aaac     # 1 — callTargetFunctionWithRole present
cast storage $OLDROLES 0x58378b12c62a352499987fe2cb0fd9b730ba7a8565e57928546a499547532ee8 --rpc-url $RPC   # role 1 targets[Delay]
```

| Check | Expected | If it differs |
|---|---|---|
| `OLDROLES.owner()` | `0xA5Ca93f1fa4dBB6E8141f6Bb22d74a79E07Fa2A1` | **Stop.** Batch calls 1, 2, 4 and 5 are `onlyOwner`. |
| `callTargetFunctionWithRole` present | `1` | **Stop.** Batch call 3 has no path to the Delay. |
| role 1 `targets[Delay]` | non-zero | **Add the scope/revoke pair** described in step 0 of the setup plan; without it call 3 reverts with `TargetAddressNotAllowed`. |
| Term DAO module ring | contains the Delay | **Stop.** The queued route needs the Delay to be a module on the Term DAO. |
| Term DAO module ring | old Roles present or absent | Determines `prevModule` in batch call 6, and whether call 6 exists at all. |
| Delay queue | `txNonce == queueNonce == 8` | FIFO: anything queued ahead of the batch executes first, and the cooldown here is **7 days**. |

---

## B. After step 1 — PauseGuard

```bash
RPC=$RPC PAUSEGUARD=$PAUSEGUARD OWNERLESS_PAUSEGUARD=$OWNERLESS_PAUSEGUARD ./verify_term_dao.sh B
```

```bash
cast call $PAUSEGUARD 'supportsInterface(bytes4)(bool)' 0xe6d7a83a --rpc-url $RPC   # true
cast call $PAUSEGUARD 'supportsInterface(bytes4)(bool)' 0x01ffc9a7 --rpc-url $RPC   # true
cast call $PAUSEGUARD 'paused()(bool)' --rpc-url $RPC                   # false
cast call $PAUSEGUARD 'pauser()(address)' --rpc-url $RPC                # 0x74f3F3dEfdC563bbFC8637BaB2d30596D2817472 (PauseSafe)
cast call $PAUSEGUARD 'admin()(address)' --rpc-url $RPC                 # 0x73d1C7dc9CEb14660Cf1E9BB29F80ECF9E97D774

# the shared PauseSafe itself — this deployment must not have changed it
cast call $PAUSESAFE 'getThreshold()(uint256)' --rpc-url $RPC           # 2
cast call $PAUSESAFE 'getOwners()(address[])' --rpc-url $RPC            # 9 owners
cast call $PAUSESAFE 'nonce()(uint256)' --rpc-url $RPC                  # 0, unless a pause has been exercised on chain
```

- **`supportsInterface(0xe6d7a83a)` must be `true`.** `Guardable.setGuard` reverts otherwise, which would fail setup step 9.
- **This must not be the ownerless deployment's PauseGuard.** That instance is already installed on `0x0C19d8A404079d71E5CA3e32fE3f758Ab543ACdf`, and `PauseGuard` has no per-Delay state: sharing one instance would put both Delays behind a single `paused` flag. Assert it, don't eyeball it:

```bash
[ "${PAUSEGUARD,,}" != "${OWNERLESS_PAUSEGUARD,,}" ] && echo OK || echo "SHARED GUARD — STOP"
```

- **The two Safes are deliberately shared** with the ownerless deployment: same `pauser`, same `admin`. Confirm `pauser()` matches the PauseSafe that deployment actually uses:

```bash
cast call $OWNERLESS_PAUSEGUARD 'pauser()(address)' --rpc-url $RPC      # must equal this guard's pauser()
cast call $OWNERLESS_PAUSEGUARD 'admin()(address)' --rpc-url $RPC       # must equal this guard's admin()
```

- View names (`paused`, `pauser`, `admin`) depend on your implementation; adjust if they differ.

Simulate the two access rules before trusting them:

```bash
cast call $PAUSEGUARD 'pause()' --from $PAUSESAFE --rpc-url $RPC         # succeeds (no state change from a call)
cast call $PAUSEGUARD 'pause()' --from $ADMINSAFE --rpc-url $RPC         # must revert — admin is not the pauser
cast call $PAUSEGUARD 'unpause()' --from $PAUSESAFE --rpc-url $RPC       # must revert — pauser is not the admin
cast call $PAUSEGUARD 'setPauser(address)' $ADMINSAFE --from $PAUSESAFE --rpc-url $RPC   # must revert
```

---

## C. After step 2 — DelayOwnerSafe

```bash
RPC=$RPC DELAYOWNER=$DELAYOWNER ./verify_term_dao.sh C
```

```bash
cast call $DELAYOWNER 'VERSION()(string)' --rpc-url $RPC                 # "1.4.1"
cast storage $DELAYOWNER 0 --rpc-url $RPC                                # identical to: cast storage $TERMDAO 0
cast call $DELAYOWNER 'getThreshold()(uint256)' --rpc-url $RPC           # 2
cast call $DELAYOWNER 'getOwners()(address[])' --rpc-url $RPC            # the 4 Proposer Safe signers
cast call $DELAYOWNER 'getModulesPaginated(address,uint256)(address[],address)' $SENTINEL 10 --rpc-url $RPC  # [] for now
cast call $DELAYOWNER 'nonce()(uint256)' --rpc-url $RPC                  # 0
```

Diff the owner sets directly rather than by eye:

```bash
diff <(cast call $DELAYOWNER 'getOwners()(address[])' --rpc-url $RPC | tr ',' '\n' | sort) \
     <(cast call $PROPOSER   'getOwners()(address[])' --rpc-url $RPC | tr ',' '\n' | sort)
```

Slot 0 must equal the Term DAO's slot 0 — v1.4.1 ships both `Safe` and `SafeL2`, and only the former is in use here. Expected `0x41675C099F32341bf84BFc5382aF534df5C7461a`.

---

## D. After step 3 — SetTxNonceGuard

```bash
RPC=$RPC SETGUARD=$SETGUARD OWNERLESS_SETGUARD=$OWNERLESS_SETGUARD ./verify_term_dao.sh D
```

```bash
cast call $SETGUARD 'delay()(address)' --rpc-url $RPC                            # 0x80Ce5a0de8B1604e3122BEE73360dC3b987F891A
cast call $SETGUARD 'supportsInterface(bytes4)(bool)' 0xe6d7a83a --rpc-url $RPC  # true
cast call $SETGUARD 'supportsInterface(bytes4)(bool)' 0x01ffc9a7 --rpc-url $RPC  # true
```

- **`delay()` is the only thing this contract holds, and nothing on chain checks it.** `Roles.setGuard` in step 5 verifies `supportsInterface` and nothing else, so a guard built against the ownerless Delay `0x0C19d8A404079d71E5CA3e32fE3f758Ab543ACdf` installs without complaint and then rejects every NewGovernor transaction. Run this before step 5, not after.
- **It must not be the ownerless deployment's instance.** `delay` is `immutable`, so one instance serves exactly one Delay:

```bash
[ "${SETGUARD,,}" != "${OWNERLESS_SETGUARD,,}" ] && echo OK || echo "SHARED GUARD — STOP"
```

- `delay` is `immutable`, so it is in the bytecode and `cast storage $SETGUARD 0` shows nothing. The getter is the only read.
- The contract declares no state variables; there is nothing else to check here.

---

## E. After step 4 — NewGovernor

```bash
RPC=$RPC NEWGOV=$NEWGOV ./verify_term_dao.sh E
```

```bash
cast call $NEWGOV 'votingPeriod()(uint256)' --rpc-url $RPC               # 432000 — the only reason this is a redeploy
cast call $NEWGOV 'votingDelay()(uint256)' --rpc-url $RPC                # 0
cast call $NEWGOV 'proposalThreshold()(uint256)' --rpc-url $RPC          # 1000000000000000000000
cast call $NEWGOV 'token()(address)' --rpc-url $RPC                      # 0xC3d21f79C3120A4fFda7A535f8005a7c297799bF
cast call $NEWGOV 'name()(string)' --rpc-url $RPC                        # "TermFinanceGovernor"
cast call $NEWGOV 'quorumNumerator()(uint256)' --rpc-url $RPC            # 1
cast call $NEWGOV 'quorumDenominator()(uint256)' --rpc-url $RPC          # 100
cast call $NEWGOV 'COUNTING_MODE()(string)' --rpc-url $RPC               # support=bravo&quorum=for,abstain
cast call $NEWGOV 'CLOCK_MODE()(string)' --rpc-url $RPC                  # mode=timestamp&from=default
cast balance $NEWGOV --rpc-url $RPC                                      # 0
cast call $TERM 'balanceOf(address)(uint256)' $NEWGOV --rpc-url $RPC     # 0
```

`votingPeriod()` is the single value this redeploy exists for. Check it against the old Governor to make the change visible:

```bash
cast call $OLDGOV 'votingPeriod()(uint256)' --rpc-url $RPC               # 604800 — the old 7 days
cast call $NEWGOV 'quorum(uint256)' $(( $(cast block latest --field timestamp --rpc-url $RPC) - 3600 )) --rpc-url $RPC   # 1000000000000000000000000
```

| Check | Expected | Meaning if wrong |
|---|---|---|
| `votingPeriod()` | `432000` | the redeploy achieved nothing; `GovernorSettings` is not inherited, so there is no setter to fix it |
| `votingDelay()` | `0` | voting does not open at creation, and the veto window shrinks further |
| `timelock()` | reverts / absent | a timelock extension was inherited by mistake, adding delay on top of the 5-day vote |
| `token()` | TERM | the Governor counts the wrong votes |

```bash
cast call $NEWGOV 'timelock()(address)' --rpc-url $RPC                   # must revert — no timelock extension
```

Storage must be empty at deploy — no proposal, vote or nonce history carries over:

```bash
for s in 0 1 2 3 4 5 6 7; do echo -n "slot $s: "; cast storage $NEWGOV $s --rpc-url $RPC; done
# 3 is _name ("TermFinanceGovernor", len 19, inline); 0,1,2,4,5,6,7 are zero
```

---

## F. After step 5 — NewRoles

```bash
RPC=$RPC NEWROLES=$NEWROLES SETGUARD=$SETGUARD NEWGOV=$NEWGOV DELAYOWNER=$DELAYOWNER OWNERLESS_NEWROLES=$OWNERLESS_NEWROLES ./verify_term_dao.sh F
```

Wiring:

```bash
cast call $NEWROLES 'owner()(address)' --rpc-url $RPC                    # 0xA5Ca93f1fa4dBB6E8141f6Bb22d74a79E07Fa2A1 (Term DAO)
cast call $NEWROLES 'avatar()(address)' --rpc-url $RPC                   # 0xA5Ca93f1fa4dBB6E8141f6Bb22d74a79E07Fa2A1
cast call $NEWROLES 'target()(address)' --rpc-url $RPC                   # $DELAYOWNER
cast call $NEWROLES 'multisend()(address)' --rpc-url $RPC                # 0x9641d764fc13c8B624c04430C7356C1C7C8102e2
cast call $NEWROLES 'guard()(address)' --rpc-url $RPC                    # $SETGUARD
cast call $NEWROLES 'defaultRoles(address)(uint16)' $NEWGOV --rpc-url $RPC   # 1
cast call $NEWROLES 'isModuleEnabled(address)(bool)' $NEWGOV --rpc-url $RPC  # true
```

`target()` must be the DelayOwnerSafe, **not** the Term DAO. The target-state plan has this slot changing from the Term DAO to the DelayOwnerSafe; leaving it at the Term DAO would point the whole veto path at the wrong avatar.

`guard()` must be the SetTxNonceGuard that section D cleared — re-read `delay()` on the address that actually came back here, in case a different instance was installed.

Role 1, read from storage:

```bash
cast storage $NEWROLES $(cast index address $NEWGOV 0xa775687211c2b3346a0f5a2a0e7590e6c1838453e3785e6dd2a8efd6265ddf15) --rpc-url $RPC
cast storage $NEWROLES 0x58378b12c62a352499987fe2cb0fd9b730ba7a8565e57928546a499547532ee8 --rpc-url $RPC
cast storage $NEWROLES 0x5abf4934a98379a2309534eef94a8d2c16aa3d3f8be7f82e740ffba60056c59d --rpc-url $RPC
```

| Slot | Meaning | Expected |
|---|---|---|
| `members[NewGovernor]` (derived above) | NewGovernor is a member of role 1 | `0x0000000000000000000000000000000000000000000000000000000000000001` |
| `0x58378b12c62a352499987fe2cb0fd9b730ba7a8565e57928546a499547532ee8` | `targets[Delay]` | `0x0000000000000000000000000000000000000000000000000000000000000002` — `Clearance.Function`, `ExecutionOptions.None` |
| `0x5abf4934a98379a2309534eef94a8d2c16aa3d3f8be7f82e740ffba60056c59d` | `functions[Delay ‖ 0x46ba2307]` | `0x2000000000000000000000000000000000000000000000000000000000000000` — options None, wildcarded, length 0 |

`targets[Delay]` reading `0x0000000000000000000000000000000000000000000000000000000000000001` instead of `0x0000000000000000000000000000000000000000000000000000000000000002` means `allowTarget` was used instead of `scopeTarget`, which would let role 1 call **any** Delay function — including `transferOwnership`, `setGuard` and `setTxCooldown`. That is the single most important value in this file.

**NewRoles is a proxy, so its own code is 45 bytes and contains no logic.** Check the proxy shape first, then run every bytecode check against the mastercopy it points at.

```bash
# the proxy is the exact EIP-1167 template pointing at the audited mastercopy — nothing else
cast code $NEWROLES --rpc-url $RPC | tr 'A-F' 'a-f'
# 0x363d3d373d3d3d363d7385388a8cd772b19a468f982dc264c238856939c95af43d82803e903d91602b57fd5bf3
```

A single equality on that string is the strongest check in this section: it fixes the implementation, and it fails if the proxy points anywhere else.

```bash
export MASTERCOPY=0x85388a8cd772b19a468F982Dc264C238856939C9

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

**Unlike the previous plan, this deployment and the ownerless one share a mastercopy and therefore a `Permissions` library.** That is expected — the mastercopy is stateless and both proxies hold their own storage — so there is no longer a "must differ" check here. What must still differ is the two proxies' own addresses; confirm they are not the same contract:

```bash
lc() { printf '%s' "$1" | tr 'A-Z' 'a-z'; }
[ "$(lc $NEWROLES)" != "$(lc $OWNERLESS_NEWROLES)" ] && echo OK || echo "SAME PROXY — STOP"
```

The mastercopy's own `owner`/`avatar`/`target` read `0x…01`, the locked state that makes `setUp` unrepeatable:

```bash
cast call $MASTERCOPY 'owner()(address)' --rpc-url $RPC     # 0x0000000000000000000000000000000000000001
```

The fork is the only safe place for a negative permission test, since the Delay's queue is empty on mainnet and `setTxNonce` always reverts then. On the fork, with an entry queued:

```bash
# allowed: setTxNonce through role 1
cast call $NEWROLES 'execTransactionWithRole(address,uint256,bytes,uint8,uint16,bool)(bool)' \
  $DELAY 0 $(cast calldata 'setTxNonce(uint256)' <queueNonce>) 0 1 true --from $NEWGOV --rpc-url $RPC   # true

# denied: anything else on the Delay
cast call $NEWROLES 'execTransactionWithRole(address,uint256,bytes,uint8,uint16,bool)(bool)' \
  $DELAY 0 $(cast calldata 'setTxCooldown(uint256)' 0) 0 1 true --from $NEWGOV --rpc-url $RPC           # must revert

# denied: the multisend branch, closed by the guard
cast call $NEWROLES 'execTransactionWithRole(address,uint256,bytes,uint8,uint16,bool)(bool)' \
  $MULTISEND 0 0x 0 1 true --from $NEWGOV --rpc-url $RPC                                                # must revert
```

---

## G. After step 6 — NewRoles enabled, still inert

```bash
RPC=$RPC DELAYOWNER=$DELAYOWNER NEWROLES=$NEWROLES ./verify_term_dao.sh G
```

```bash
cast call $DELAYOWNER 'getModulesPaginated(address,uint256)(address[],address)' $SENTINEL 10 --rpc-url $RPC  # [NewRoles]
cast call $DELAY 'owner()(address)' --rpc-url $RPC                       # still 0xF3BD578bDa56176Bbf8529B5C945193cF54DB1f5 — unchanged
```

The second line is the point of this section: NewRoles is wired but the Delay has not moved, so the new branch still has no authority.

---

## H. After step 7 — the batch is queued, not executed

```bash
RPC=$RPC BATCH_TXHASH=0x.. BATCH_CALLDATA=0x.. ./verify_term_dao.sh H
```

```bash
cast call $DELAY 'queueNonce()(uint256)' --rpc-url $RPC                  # 9
cast call $DELAY 'txNonce()(uint256)' --rpc-url $RPC                     # 8 — nothing executed
cast call $DELAY 'txHash(uint256)(bytes32)' 8 --rpc-url $RPC
cast call $DELAY 'txCreatedAt(uint256)(uint256)' 8 --rpc-url $RPC        # t0
cast call $DELAY 'owner()(address)' --rpc-url $RPC                       # still the old Roles
```

Confirm the stored hash matches the calldata you intend to execute, before the cooldown elapses:

```bash
cast call $DELAY 'getTransactionHash(address,uint256,bytes,uint8)(bytes32)' \
  $MULTISEND 0 <batch-calldata> 1 --rpc-url $RPC      # must equal txHash(8)
```

| Check | Expected |
|---|---|
| Execution window | `t0 + 604800` to `t0 + 777600` |
| `getTransactionHash(...)` | equal to `txHash(8)` |
| Old Roles role 1 members[Term DAO] | still `0x0` — the grant is inside the batch, not yet applied |
| Old Roles modules | unchanged from section A |

```bash
cast storage $OLDROLES 0x010526f37f6ace9bfc4207af69d85db61a8f833e1f7714c9fd12b163f2511805 --rpc-url $RPC   # 0x0
```

A mismatch on the hash means the entry can never be executed. Let it expire and queue again; don't try to patch the arguments. **Re-queueing costs another 7 days**, so check this the day it is queued, not the day it matures.

---

## I. After step 8 — the migration landed

```bash
RPC=$RPC DELAYOWNER=$DELAYOWNER TERMDAO_NONCE=12 ./verify_term_dao.sh I
```

```bash
cast call $DELAY 'owner()(address)' --rpc-url $RPC                       # $DELAYOWNER
cast call $DELAY 'txNonce()(uint256)' --rpc-url $RPC                     # 9 == queueNonce
cast call $TERMDAO  'getModulesPaginated(address,uint256)(address[],address)' $SENTINEL 10 --rpc-url $RPC   # Delay present, old Roles absent
cast call $OLDROLES 'getModulesPaginated(address,uint256)(address[],address)' $SENTINEL 10 --rpc-url $RPC   # Term DAO absent
cast call $TERMDAO 'nonce()(uint256)' --rpc-url $RPC                     # unchanged from section A
```

The temporary grant must be gone. Check the old Roles' membership slot for the Term DAO directly:

```bash
cast storage $OLDROLES 0x010526f37f6ace9bfc4207af69d85db61a8f833e1f7714c9fd12b163f2511805 --rpc-url $RPC   # 0x0
```

| Check | Expected | Meaning if wrong |
|---|---|---|
| Delay `owner` | DelayOwnerSafe | the handover didn't happen |
| Term DAO modules | Delay present, old Roles absent | the old Roles still has a path into the Term DAO |
| Old Roles modules | no Term DAO | the temporary module grant was left open |
| Old Roles role 1 members[Term DAO] | `0x0` | the temporary role grant was left open |
| Term DAO `nonce` | the value recorded in section A | the rule was broken — the Term DAO signed something |

The last row is the check that the queued route was actually used. If the direct-signature variant was chosen instead, the Term DAO's nonce advances by exactly one and this row reads `+1`; anything more means additional transactions were signed.

---

## J. After step 9 — the guard, and the live veto path

```bash
RPC=$RPC PAUSEGUARD=$PAUSEGUARD OWNERLESS_PAUSEGUARD=$OWNERLESS_PAUSEGUARD ./verify_term_dao.sh J
```

```bash
INSTALLED=$(cast call $DELAY 'guard()(address)' --rpc-url $RPC)          # $PAUSEGUARD
[ "${INSTALLED,,}" = "${PAUSEGUARD,,}" ] && echo OK || echo "WRONG GUARD — STOP"
[ "${INSTALLED,,}" != "${OWNERLESS_PAUSEGUARD,,}" ] && echo OK || echo "SHARED GUARD — STOP"
```

On the fork, exercise all three paths end to end:

1. **Normal execution.** Queue a harmless transaction from the Proposer Safe, warp past `txCooldown` (7 days), call `executeNextTx`, confirm it runs.
2. **Pause.** `pause()` from the PauseSafe `0x74f3F3dEfdC563bbFC8637BaB2d30596D2817472` (2 of 9), confirm `executeNextTx` now reverts; `unpause()` from the Admin Safe `0x73d1C7dc9CEb14660Cf1E9BB29F80ECF9E97D774`, confirm it runs again.
3. **Veto.** Queue a transaction, create a NewGovernor proposal carrying `execTransactionWithRole(Delay, 0, setTxNonce(n), Call, 1, true)`, vote it through, warp past the 5-day voting period, `execute`, and confirm `txNonce` moved past `n`.

Also confirm the two systems are independent, which is the whole reason for a second PauseGuard:

4. **Isolation.** With this Delay paused, confirm `executeNextTx` on the ownerless Delay `0x0C19d8A404079d71E5CA3e32fE3f758Ab543ACdf` still runs.

Path 3 confirms the timing the plan flags: with a 5-day vote and a 7-day cooldown, the veto window is `[tp + 5d, t0 + 7d)` — two days when the proposal is created the moment the transaction is queued, and nothing at all if it is created more than 48 hours late.

---

## K. After step 10 — fallback handler cleared

```bash
RPC=$RPC ./verify_term_dao.sh K
```

```bash
cast storage $PROPOSER 0x6c9a6c4a39284e37ed1cf53d337577d14212a4870fb976a4366c693b939918d5 --rpc-url $RPC   # 0x0
```

Was `0xfd0732Dc9E303f09fCEf3a7388Ad10A83459Ec99` (CompatibilityFallbackHandler v1.4.1). The transaction emits `ChangedFallbackHandler(0x0000000000000000000000000000000000000000)`.

This step is independent of the migration; it can be verified at any point after it is sent.

---

## L. Final sweep — full target state

```bash
RPC=$RPC PAUSEGUARD=$PAUSEGUARD DELAYOWNER=$DELAYOWNER SETGUARD=$SETGUARD NEWGOV=$NEWGOV NEWROLES=$NEWROLES TERMDAO_NONCE=12 ./verify_term_dao.sh L
```

Run this once everything is done; it is the same list as the plan's tables, in one place.

| Contract | Check | Expected |
|---|---|---|
| Delay | `owner`, `guard` | DelayOwnerSafe, this deployment's PauseGuard |
| Delay | modules | `[0xe9dDBBD914063BC703D468e25d0B75148A480cC5]` |
| Delay | `txCooldown`, `txExpiration` | `604800`, `172800` |
| Delay | `txNonce`, `queueNonce` | equal, `9` |
| Delay | `avatar`, `target` | `0xA5Ca93f1fa4dBB6E8141f6Bb22d74a79E07Fa2A1` (both) |
| NewRoles | `owner`, `avatar`, `target` | Term DAO, Term DAO, DelayOwnerSafe |
| NewRoles | `multisend`, `guard` | `0x9641d764fc13c8B624c04430C7356C1C7C8102e2`, SetTxNonceGuard |
| NewRoles | `defaultRoles(NewGovernor)`, modules | `1`, `[NewGovernor]` |
| NewRoles | role 1 `members[NewGovernor]`, `targets[Delay]`, `functions[Delay ‖ 0x46ba2307]` | the three values in section F, in full |
| NewRoles | code | the 45-byte EIP-1167 template pointing at `0x85388a8cd772b19a468F982Dc264C238856939C9` — exact string match |
| Roles mastercopy `0x85388a8cd772b19a468F982Dc264C238856939C9` | codehash | `0xccd8ad5609bd6b5dffb5aa4be6ac4b0c4fd12f0d5ab908f69c9342e63e186db1` — the audited Roles v1.0.0 build |
| Roles mastercopy | `owner` / `avatar` / `target` | `0x…01` — locked, `setUp` spent |
| Permissions library `0x543D1DE69b25420685Ef723842D0087d9b731B06` | codehash | `0x8855a716d8a3ff5fedf4be46bed673d391a183f54e406d702a9bafa767fc407a` |
| NewGovernor | `votingPeriod`, `votingDelay`, `quorum` | `432000`, `0`, `1e24` |
| NewGovernor | `timelock()` | reverts — no timelock extension |
| SetTxNonceGuard | `delay` | `0x80Ce5a0de8B1604e3122BEE73360dC3b987F891A` |
| SetTxNonceGuard | address | **not** the ownerless deployment's instance |
| DelayOwnerSafe | owners, threshold, modules | the 4 Proposer Safe signers, `2`, `[NewRoles]` |
| DelayOwnerSafe | slot 0 | equal to the Term DAO's slot 0 |
| PauseGuard | `paused`, `pauser`, `admin` | `false`, `0x74f3F3dEfdC563bbFC8637BaB2d30596D2817472`, `0x73d1C7dc9CEb14660Cf1E9BB29F80ECF9E97D774` |
| PauseGuard | address | **not** the ownerless deployment's instance |
| PauseSafe `0x74f3F3dEfdC563bbFC8637BaB2d30596D2817472` | owners, threshold | 9, `2` — shared with the ownerless deployment; neither plan changes it |
| Term DAO | modules, `nonce` | Delay present / old Roles absent, unchanged from section A |
| Old Roles | Delay ownership, Term DAO module entry, role 1 membership | none, none, `0x0` |
| Old Governor | reachability | inert — the old Roles owns nothing and is a module on nothing |
| Proposer Safe | fallback handler slot `0x6c9a6c4a39284e37ed1cf53d337577d14212a4870fb976a4366c693b939918d5` | `0x0` |
| Proposer Safe | owners, threshold | 4, `2` |
