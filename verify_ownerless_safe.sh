#!/usr/bin/env bash
# Usage: verify_ownerless_safe.sh <section>      section = A B C D E F G H I | all
#
# Runs the reads in verification_plan_ownerless_safe.md. Reads only — nothing here
# sends a transaction. Exit status is 0 only if every check in the section passed.
#
#   RPC=<rpc> ./verify_ownerless_safe.sh A                 # before step 1
#   RPC=<rpc> PAUSEGUARD=0x.. ./verify_ownerless_safe.sh B # after step 1
#   RPC=<rpc> PAUSEGUARD=0x.. SETGUARD=0x.. NEWROLES=0x.. ./verify_ownerless_safe.sh I
set -uo pipefail

usage() { sed -n '2,9p' "$0" | sed 's/^# \{0,1\}//'; exit 2; }
case "${1:-}" in A|B|C|D|E|F|G|H|I|all) ;; *) usage ;; esac

RPC=${RPC:?set RPC to an archive-capable endpoint}
CHAIN=${CHAIN:-1}   # expected chain id; CHAIN=0 to skip the check

# A dead endpoint returns empty for every read, which an "expect empty" check would
# otherwise score as a pass. Fail loudly here instead.
if ! _chain=$(cast chain-id --rpc-url "$RPC" 2>&1); then
  printf 'RPC %s is not answering: %s\n' "$RPC" "${_chain%%$'\n'*}" >&2; exit 2
fi
if [[ "$CHAIN" != 0 && "$_chain" != "$CHAIN" ]]; then
  printf 'RPC %s is chain %s, expected %s (set CHAIN to override)\n' "$RPC" "$_chain" "$CHAIN" >&2; exit 2
fi

# deployed and fixed
OWNERLESS=0xb8A1dF43c1c88b13937C0c5CEBbAd15830cAeC03
DELAY=0x0C19d8A404079d71E5CA3e32fE3f758Ab543ACdf
OLDROLES=0x405b47354CF06A25DE1DDb35EC65F03939E2e8D2
GOV=0x2B715634134220ffeEE9458b4e34E41A41418607
PROPOSER=0xd5E12854A3Dba99deF295A7635D3Ba16427d2A28
ADMINSAFE=0x73d1C7dc9CEb14660Cf1E9BB29F80ECF9E97D774
PAUSESAFE=0x74f3F3dEfdC563bbFC8637BaB2d30596D2817472
DELAYOWNER=0x2a875746D0c88EBD2bbBfc8F8a773c58c3373ad3
MULTISEND=0x40A2aCCbd92BCA938b02010E17A5b8929b49130D        # v1.3.0 — the migration batch
ROLES_MULTISEND=0x9641d764fc13c8B624c04430C7356C1C7C8102e2  # v1.4.1 — NewRoles multisend
SENTINEL=0x0000000000000000000000000000000000000001
ZERO=0x0000000000000000000000000000000000000000
NINTH=0xC3CbFc5DA4B3d4B1258D63cA7ba56518C33f28c7   # PauseSafe signer that is not an Admin Safe owner
MASTERCOPY=${MASTERCOPY:-0x85388a8cd772b19a468F982Dc264C238856939C9}   # Roles v1.0.0, audited
PERMISSIONS=543d1de69b25420685ef723842d0087d9b731b06                  # linked inside the mastercopy
PERMLIB=${PERMLIB:-0x543D1DE69b25420685Ef723842D0087d9b731B06}      # the same library, as an address
# keccak256 of the deployed runtime. This is the check that actually pins the
# implementation: the selector greps below are indicative, another build could
# contain the same selectors. Recompiling the audited commit's source with the
# mastercopy's own solc settings reproduces these exactly.
MASTERCODEHASH=${MASTERCODEHASH:-0xccd8ad5609bd6b5dffb5aa4be6ac4b0c4fd12f0d5ab908f69c9342e63e186db1}
PERMCODEHASH=${PERMCODEHASH:-0x8855a716d8a3ff5fedf4be46bed673d391a183f54e406d702a9bafa767fc407a}
# the 45-byte EIP-1167 proxy the ModuleProxyFactory emits for that mastercopy
PROXYCODE=0x363d3d373d3d3d363d7385388a8cd772b19a468f982dc264c238856939c95af43d82803e903d91602b57fd5bf3

# deployed as the plan progresses — export before the section that needs them
PAUSEGUARD=${PAUSEGUARD:-}
SETGUARD=${SETGUARD:-}
NEWROLES=${NEWROLES:-}

# point-in-time values, override if the chain has moved on
START_NONCE=${START_NONCE:-203}
OWNERLESS_NONCE=${OWNERLESS_NONCE:-16}
BATCH_TXHASH=${BATCH_TXHASH:-0xb0ae0a2f2f777c3da8e4a22979038c7ab8e5a714a93479deffdb02434c91cb09}
BATCH_CALLDATA=${BATCH_CALLDATA:-}   # multiSend calldata, if you want the hash recomputed

# storage slots (key-derived, from the plan)
S_MEMBERS_GOV=0x84f2af0e843bf5d088bc58e2ec3e637cc9a06f27000758f776cf7f0048bbf316
S_TARGETS_DELAY=0x6d118fdf1559b49b55b86a40bd7fa6c747463e77d457904632e6b94ed8c4134f
S_FUNCTIONS_SETTXNONCE=0x2e72263c2be6fdc6f1499ba76346dee89ffb39313281bfa1f661681dff2962df
S_MEMBERS_BASE=0xa775687211c2b3346a0f5a2a0e7590e6c1838453e3785e6dd2a8efd6265ddf15
S_FALLBACK=0x6c9a6c4a39284e37ed1cf53d337577d14212a4870fb976a4366c693b939918d5
W_ONE=0x0000000000000000000000000000000000000000000000000000000000000001
W_TWO=0x0000000000000000000000000000000000000000000000000000000000000002
W_ZERO=0x0000000000000000000000000000000000000000000000000000000000000000
W_FUNCTION=0x2000000000000000000000000000000000000000000000000000000000000000

pass=0; fail=0; skip=0
red=$'\033[31m'; grn=$'\033[32m'; yel=$'\033[33m'; off=$'\033[0m'
[[ -t 1 ]] || { red=; grn=; yel=; off=; }

norm() { printf '%s' "$1" | tr 'A-F' 'a-f' | tr -d '[:space:]'; }
ok()   { pass=$((pass+1)); printf '  %sPASS%s  %-46s %s\n' "$grn" "$off" "$1" "${2-}"; }
bad()  { fail=$((fail+1)); printf '  %sFAIL%s  %-46s got %s, want %s\n' "$red" "$off" "$1" "${2-}" "${3-}"; }
note() { skip=$((skip+1)); printf '  %sSKIP%s  %-46s %s\n' "$yel" "$off" "$1" "${2-}"; }

check() { # check <label> <expected> <actual>
  if [[ "$(norm "$2")" == "$(norm "$3")" ]]; then ok "$1" "$3"; else bad "$1" "${3:-<none>}" "$2"; fi
}

# read; empty on revert. Strips cast's trailing "[8.64e4]" scientific-notation hint.
rd() { cast call "$@" --rpc-url "$RPC" 2>/dev/null | sed 's/ \[[0-9.e+-]*\]$//'; }
st() { cast storage "$1" "$2" --rpc-url "$RPC" 2>/dev/null || printf 'ERR'; }
ch() { # keccak256 of the runtime at $1; "ERR" if it cannot be read
  local h; h=$(cast codehash "$1" --rpc-url "$RPC" 2>/dev/null) && [[ -n "$h" ]] || { printf 'ERR'; return; }
  printf '%s' "$h"
}

modules() { # comma-joined, lowercased module ring of $1; "ERR" if the read failed
  local out
  out=$(cast call "$1" 'getModulesPaginated(address,uint256)(address[],address)' "$SENTINEL" 10 \
        --rpc-url "$RPC" 2>/dev/null) || { printf 'ERR'; return; }
  printf '%s' "$out" | head -1 | tr -d '[] ' | tr 'A-F' 'a-f'
}
owners() { rd "$1" 'getOwners()(address[])' | tr -d '[]' | tr ',' '\n' | tr -d ' ' | tr 'A-F' 'a-f' | grep . | sort; }

expect_revert() { # expect_revert <label> <cast call args...>
  local label=$1; shift
  if out=$(cast call "$@" --rpc-url "$RPC" 2>&1); then bad "$label" "returned ${out:0:24}" "revert"
  # a transport failure is not a revert — don't let a flaky endpoint score as a pass
  elif [[ "$out" != *revert* && "$out" != *EvmError* && "$out" != *"custom error"* ]]; then
    bad "$label" "RPC error: ${out%%$'\n'*}" "revert"
  else ok "$label" "reverted"; fi
}
expect_call_ok() {
  local label=$1; shift
  if cast call "$@" --rpc-url "$RPC" >/dev/null 2>&1; then ok "$label" "succeeds"
  else bad "$label" "reverted" "success"; fi
}
have() { # have <label> <var> -> 0 if set
  if [[ -n "${2:-}" ]]; then return 0; fi
  note "$1" "set \$${3} first"; return 1
}
in_code() { # in_code <needle> <label> <expected count 0|1> -- reads the MASTERCOPY; the proxy holds no logic
  local n; n=$(cast code "$MASTERCOPY" --rpc-url "$RPC" 2>/dev/null | tr 'A-F' 'a-f' | grep -c "$1")
  check "$2" "$3" "$n"
}

section_A() {
  echo "A. Before anything — starting state"
  check "Delay owner == old Roles"           "$OLDROLES"     "$(rd $DELAY 'owner()(address)')"
  check "Delay guard unset"                  "$ZERO"         "$(rd $DELAY 'guard()(address)')"
  check "Delay txNonce"                      "$START_NONCE"  "$(rd $DELAY 'txNonce()(uint256)')"
  check "Delay queueNonce (queue empty)"     "$START_NONCE"  "$(rd $DELAY 'queueNonce()(uint256)')"
  check "Delay txCooldown"                   "86400"         "$(rd $DELAY 'txCooldown()(uint256)')"
  check "Delay txExpiration"                 "86400"         "$(rd $DELAY 'txExpiration()(uint256)')"
  check "Delay modules == [Proposer Safe]"   "$PROPOSER"     "$(modules $DELAY)"
  check "old Roles owner == Ownerless Safe"  "$OWNERLESS"    "$(rd $OLDROLES 'owner()(address)')"
  check "old Roles modules == []"            ""              "$(modules $OLDROLES)"
  check "Ownerless ring == [old Roles,Delay]" "$OLDROLES,$DELAY" "$(modules $OWNERLESS)"
  check "old Roles targets[Delay] == Target" "$W_ONE"        "$(st $OLDROLES $S_TARGETS_DELAY)"
}

section_B() {
  echo "B. After step 1 — PauseGuard"
  have "PauseGuard checks" "$PAUSEGUARD" PAUSEGUARD || return
  check "supportsInterface(0xe6d7a83a)" "true"  "$(rd $PAUSEGUARD 'supportsInterface(bytes4)(bool)' 0xe6d7a83a)"
  check "supportsInterface(0x01ffc9a7)" "true"  "$(rd $PAUSEGUARD 'supportsInterface(bytes4)(bool)' 0x01ffc9a7)"
  check "paused"                        "false" "$(rd $PAUSEGUARD 'paused()(bool)')"
  check "pauser == PauseSafe"           "$PAUSESAFE" "$(rd $PAUSEGUARD 'pauser()(address)')"
  local admin; admin=$(rd $PAUSEGUARD 'admin()(address)')
  if [[ -n "$admin" ]]; then
    check "admin == Admin Safe"         "$ADMINSAFE" "$admin"
  else
    check "ADMIN_ROLE held by Admin Safe" "true" \
      "$(rd $PAUSEGUARD 'hasRole(bytes32,address)(bool)' "$(cast keccak ADMIN_ROLE)" $ADMINSAFE)"
  fi
  expect_call_ok "pause() from PauseSafe"        $PAUSEGUARD 'pause()'   --from $PAUSESAFE
  expect_revert  "pause() from Admin Safe"       $PAUSEGUARD 'pause()'   --from $ADMINSAFE
  expect_revert  "unpause() from PauseSafe"      $PAUSEGUARD 'unpause()' --from $PAUSESAFE
  expect_revert  "setPauser() from PauseSafe"    $PAUSEGUARD 'setPauser(address)' $ADMINSAFE --from $PAUSESAFE
}

section_C() {
  echo "C. After step 2 — SetTxNonceGuard"
  have "SetTxNonceGuard checks" "$SETGUARD" SETGUARD || return
  check "delay() == the Delay"           "$DELAY" "$(rd $SETGUARD 'delay()(address)')"
  check "supportsInterface(0xe6d7a83a)"  "true"   "$(rd $SETGUARD 'supportsInterface(bytes4)(bool)' 0xe6d7a83a)"
  check "supportsInterface(0x01ffc9a7)"  "true"   "$(rd $SETGUARD 'supportsInterface(bytes4)(bool)' 0x01ffc9a7)"
}

section_D() {
  echo "D. After step 3 — NewRoles"
  have "NewRoles checks" "$NEWROLES" NEWROLES || return
  check "owner == Ownerless Safe"        "$OWNERLESS"  "$(rd $NEWROLES 'owner()(address)')"
  check "avatar == Ownerless Safe"       "$OWNERLESS"  "$(rd $NEWROLES 'avatar()(address)')"
  check "target == DelayOwnerSafe"       "$DELAYOWNER" "$(rd $NEWROLES 'target()(address)')"
  check "multisend == MultiSendCallOnly" "$ROLES_MULTISEND"  "$(rd $NEWROLES 'multisend()(address)')"
  check "defaultRoles(Governor) == 1"    "1"           "$(rd $NEWROLES 'defaultRoles(address)(uint16)' $GOV)"
  check "Governor enabled as module"     "true"        "$(rd $NEWROLES 'isModuleEnabled(address)(bool)' $GOV)"
  local g; g=$(rd $NEWROLES 'guard()(address)')
  if [[ -n "$SETGUARD" ]]; then check "guard == SetTxNonceGuard" "$SETGUARD" "$g"
  else note "guard == SetTxNonceGuard" "set \$SETGUARD first; guard() reads $g"; fi
  # the installed guard must itself point at the Delay, whichever instance came back
  [[ -n "$g" && "$(norm "$g")" != "$(norm "$ZERO")" ]] && \
    check "installed guard's delay() == Delay" "$DELAY" "$(rd "$g" 'delay()(address)')"
  check "members[Governor] == 1"         "$W_ONE"      "$(st $NEWROLES $S_MEMBERS_GOV)"
  check "targets[Delay] == Function (2)" "$W_TWO"      "$(st $NEWROLES $S_TARGETS_DELAY)"
  check "functions[Delay|setTxNonce]"    "$W_FUNCTION" "$(st $NEWROLES $S_FUNCTIONS_SETTXNONCE)"
  check "proxy is EIP-1167 -> mastercopy" "$PROXYCODE" "$(cast code $NEWROLES --rpc-url "$RPC" 2>/dev/null)"
  check "mastercopy codehash (audited build)" "$MASTERCODEHASH" "$(ch $MASTERCOPY)"
  check "Permissions library codehash"        "$PERMCODEHASH"   "$(ch $PERMLIB)"
  check "mastercopy locked (owner==0x..01)" "$SENTINEL" "$(rd $MASTERCOPY 'owner()(address)')"
  in_code 639518aaac      "callTargetFunctionWithRole absent"  0
  in_code 63468721a7      "execTransactionFromModule present"  1
  in_code 635229073f      "execTransactionFromModuleReturnData" 1
  in_code "73$PERMISSIONS" "Permissions library linked"        1
  note "fork-only: setTxNonce allowed / others denied" "see section D of the plan"
}

section_E() {
  echo "E. After step 4 — NewRoles enabled, still inert"
  if [[ -n "$NEWROLES" ]]; then check "DelayOwnerSafe modules == [NewRoles]" "$NEWROLES" "$(modules $DELAYOWNER)"
  else note "DelayOwnerSafe modules == [NewRoles]" "set \$NEWROLES first; reads $(modules $DELAYOWNER)"; fi
  check "Delay owner still old Roles" "$OLDROLES" "$(rd $DELAY 'owner()(address)')"
}

section_F() {
  echo "F. After step 5 — the batch is queued, not executed"
  check "Delay queueNonce"            "$((START_NONCE+1))" "$(rd $DELAY 'queueNonce()(uint256)')"
  check "Delay txNonce (nothing ran)" "$START_NONCE"       "$(rd $DELAY 'txNonce()(uint256)')"
  check "Delay owner still old Roles" "$OLDROLES"          "$(rd $DELAY 'owner()(address)')"
  check "old Roles modules still []"  ""                   "$(modules $OLDROLES)"
  check "txHash($START_NONCE)"        "$BATCH_TXHASH"      "$(rd $DELAY 'txHash(uint256)(bytes32)' $START_NONCE)"
  if [[ -n "$BATCH_CALLDATA" ]]; then
    check "getTransactionHash(batch)" "$BATCH_TXHASH" \
      "$(rd $DELAY 'getTransactionHash(address,uint256,bytes,uint8)(bytes32)' $MULTISEND 0 "$BATCH_CALLDATA" 1)"
  else
    note "getTransactionHash(batch)" "set \$BATCH_CALLDATA to re-derive the hash"
  fi
  local t0; t0=$(rd $DELAY 'txCreatedAt(uint256)(uint256)' $START_NONCE)
  t0=${t0%% *}
  when() { date -r "$1" '+%F %T %Z' 2>/dev/null || date -d "@$1" '+%F %T %Z' 2>/dev/null || echo "$1"; }
  [[ -n "$t0" && "$t0" != 0 ]] && printf '  ----  %-46s %s → %s\n' "execution window" \
    "$(when $((t0+86400)))" "$(when $((t0+172800)))"
}

section_G() {
  echo "G. After step 6 — the migration landed"
  check "Delay owner == DelayOwnerSafe"   "$DELAYOWNER"        "$(rd $DELAY 'owner()(address)')"
  check "Delay txNonce"                   "$((START_NONCE+1))" "$(rd $DELAY 'txNonce()(uint256)')"
  check "Delay queueNonce == txNonce"     "$(rd $DELAY 'txNonce()(uint256)')" "$(rd $DELAY 'queueNonce()(uint256)')"
  check "Ownerless ring == [Delay]"       "$DELAY"             "$(modules $OWNERLESS)"
  check "old Roles modules == []"         ""                   "$(modules $OLDROLES)"
  check "old Roles members[Governor] == 0" "$W_ZERO"           "$(st $OLDROLES $S_MEMBERS_GOV)"
  check "old Roles grant to Ownerless closed" "$W_ZERO" \
    "$(st $OLDROLES "$(cast index address $OWNERLESS $S_MEMBERS_BASE)")"
  check "Ownerless nonce unchanged"       "$OWNERLESS_NONCE"   "$(rd $OWNERLESS 'nonce()(uint256)')"
}

section_H() {
  echo "H. After step 7 — the guard, and the live veto path"
  if [[ -n "$PAUSEGUARD" ]]; then check "Delay guard == PauseGuard" "$PAUSEGUARD" "$(rd $DELAY 'guard()(address)')"
  else note "Delay guard == PauseGuard" "set \$PAUSEGUARD first; reads $(rd $DELAY 'guard()(address)')"; fi
  note "fork-only: normal execution / pause / veto" "three paths, section H of the plan"
}

section_I() {
  echo "I. After step 8 — final sweep, full target state"
  section_G
  section_H
  echo "  Delay"
  check "Delay modules == [Proposer Safe]" "$PROPOSER"   "$(modules $DELAY)"
  check "Delay txCooldown"                 "86400"       "$(rd $DELAY 'txCooldown()(uint256)')"
  check "Delay txExpiration"               "86400"       "$(rd $DELAY 'txExpiration()(uint256)')"
  check "Delay avatar == Ownerless Safe"   "$OWNERLESS"  "$(rd $DELAY 'avatar()(address)')"
  check "Delay target == Ownerless Safe"   "$OWNERLESS"  "$(rd $DELAY 'target()(address)')"
  echo "  NewRoles"; section_D
  echo "  DelayOwnerSafe / PauseSafe / Proposer Safe"
  check "DelayOwnerSafe owner count"       "11"          "$(owners $DELAYOWNER | wc -l | tr -d ' ')"
  check "DelayOwnerSafe threshold"         "5"           "$(rd $DELAYOWNER 'getThreshold()(uint256)')"
  check "PauseSafe owner count"            "9"           "$(owners $PAUSESAFE | wc -l | tr -d ' ')"
  check "PauseSafe threshold"              "2"           "$(rd $PAUSESAFE 'getThreshold()(uint256)')"
  check "PauseSafe owners \\ Admin Safe"   "$NINTH"      "$(comm -23 <(owners $PAUSESAFE) <(owners $ADMINSAFE) | tr -d '\n')"
  check "Proposer Safe owner count"        "11"          "$(owners $PROPOSER | wc -l | tr -d ' ')"
  check "Proposer Safe threshold"          "5"           "$(rd $PROPOSER 'getThreshold()(uint256)')"
  check "Proposer Safe fallback handler"   "$W_ZERO"     "$(st $PROPOSER $S_FALLBACK)"
  echo "  PauseGuard / Governor"
  if [[ -n "$PAUSEGUARD" ]]; then
    check "PauseGuard paused"              "false"       "$(rd $PAUSEGUARD 'paused()(bool)')"
    check "PauseGuard pauser == PauseSafe" "$PAUSESAFE"  "$(rd $PAUSEGUARD 'pauser()(address)')"
  fi
  check "Governor votingPeriod"            "79200"       "$(rd $GOV 'votingPeriod()(uint256)')"
  local blk; blk=$(( $(cast block-number --rpc-url "$RPC" 2>/dev/null || echo 1) - 1 ))
  check "Governor quorum"  "1000000000000000000000000" "$(rd $GOV 'quorum(uint256)(uint256)' $blk)"
}

want=${1:-}
case "$want" in
  A|B|C|D|E|F|G|H|I) "section_$want" ;;
  all) for s in A B C D E F G H I; do "section_$s"; echo; done ;;
esac

echo
printf '%s passed, %s failed, %s skipped\n' "$pass" "$fail" "$skip"
[[ $fail -eq 0 ]]
