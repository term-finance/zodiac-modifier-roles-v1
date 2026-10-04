#!/usr/bin/env bash
# Usage: verify_term_dao.sh <section>      section = A B C D E F G H I J K L | all
#
# Runs the reads in verification_plan_term_dao.md. Reads only — nothing here
# sends a transaction. Exit status is 0 only if every check in the section passed.
#
#   RPC=<rpc> ./verify_term_dao.sh A                 # before step 1
#   RPC=<rpc> PAUSEGUARD=0x.. ./verify_term_dao.sh B # after step 1
#   RPC=<rpc> PAUSEGUARD=0x.. DELAYOWNER=0x.. SETGUARD=0x.. NEWGOV=0x.. NEWROLES=0x.. ./verify_term_dao.sh L
set -uo pipefail

usage() { sed -n '2,9p' "$0" | sed 's/^# \{0,1\}//'; exit 2; }
case "${1:-}" in A|B|C|D|E|F|G|H|I|J|K|L|all) ;; *) usage ;; esac

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
TERMDAO=0xA5Ca93f1fa4dBB6E8141f6Bb22d74a79E07Fa2A1
DELAY=0x80Ce5a0de8B1604e3122BEE73360dC3b987F891A
OLDROLES=0xF3BD578bDa56176Bbf8529B5C945193cF54DB1f5
OLDGOV=0xfCCD42fc5C46810F395adfB29739AFF402913dd3
PROPOSER=0xe9dDBBD914063BC703D468e25d0B75148A480cC5
ADMINSAFE=0x73d1C7dc9CEb14660Cf1E9BB29F80ECF9E97D774
PAUSESAFE=0x74f3F3dEfdC563bbFC8637BaB2d30596D2817472
TERM=0xC3d21f79C3120A4fFda7A535f8005a7c297799bF
MULTISEND=0x9641d764fc13c8B624c04430C7356C1C7C8102e2
SINGLETON=0x41675C099F32341bf84BFc5382aF534df5C7461a
FALLBACKHANDLER=0xfd0732Dc9E303f09fCEf3a7388Ad10A83459Ec99
SENTINEL=0x0000000000000000000000000000000000000001
ZERO=0x0000000000000000000000000000000000000000

# the Roles proxy's implementation, shared with the ownerless deployment
MASTERCOPY=${MASTERCOPY:-0x85388a8cd772b19a468F982Dc264C238856939C9}   # Roles v1.0.0, audited
PERMLIB=${PERMLIB:-0x543D1DE69b25420685Ef723842D0087d9b731B06}         # linked inside it
PERMISSIONS=543d1de69b25420685ef723842d0087d9b731b06
# keccak256 of the deployed runtime. This is the check that actually pins the
# implementation: the selector greps are indicative, another build could contain
# the same selectors.
MASTERCODEHASH=${MASTERCODEHASH:-0xccd8ad5609bd6b5dffb5aa4be6ac4b0c4fd12f0d5ab908f69c9342e63e186db1}
PERMCODEHASH=${PERMCODEHASH:-0x8855a716d8a3ff5fedf4be46bed673d391a183f54e406d702a9bafa767fc407a}
PROXYCODE=0x363d3d373d3d3d363d7385388a8cd772b19a468f982dc264c238856939c95af43d82803e903d91602b57fd5bf3

# deployed as the plan progresses — export before the section that needs them
PAUSEGUARD=${PAUSEGUARD:-}
DELAYOWNER=${DELAYOWNER:-}
SETGUARD=${SETGUARD:-}
NEWGOV=${NEWGOV:-}
NEWROLES=${NEWROLES:-}

# the ownerless deployment's instances — these must NOT be reused here
OWNERLESS_PAUSEGUARD=${OWNERLESS_PAUSEGUARD:-}
OWNERLESS_SETGUARD=${OWNERLESS_SETGUARD:-}
OWNERLESS_NEWROLES=${OWNERLESS_NEWROLES:-}
OWNERLESS_DELAY=0x0C19d8A404079d71E5CA3e32fE3f758Ab543ACdf

# point-in-time values, override if the chain has moved on
START_NONCE=${START_NONCE:-8}
TERMDAO_NONCE=${TERMDAO_NONCE:-}     # record in section A, compare in section I
BATCH_TXHASH=${BATCH_TXHASH:-}
BATCH_CALLDATA=${BATCH_CALLDATA:-}   # multiSend calldata, if you want the hash recomputed

# storage slots (key-derived, from the plan)
S_MEMBERS_BASE=0xa775687211c2b3346a0f5a2a0e7590e6c1838453e3785e6dd2a8efd6265ddf15
S_TARGETS_DELAY=0x58378b12c62a352499987fe2cb0fd9b730ba7a8565e57928546a499547532ee8
S_FUNCTIONS_SETTXNONCE=0x5abf4934a98379a2309534eef94a8d2c16aa3d3f8be7f82e740ffba60056c59d
S_OLDROLES_MEMBER_TERMDAO=0x010526f37f6ace9bfc4207af69d85db61a8f833e1f7714c9fd12b163f2511805
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
differs() { # differs <label> <a> <b> -- passes when a != b and both are set
  if [[ -z "$3" ]]; then note "$1" "set the ownerless address to compare"; return; fi
  if [[ "$(norm "$2")" != "$(norm "$3")" ]]; then ok "$1" "distinct"; else bad "$1" "same as $3" "a different instance"; fi
}
contains() { # contains <label> <needle> <haystack>
  if [[ "$(norm "$3")" == *"$(norm "$2")"* ]]; then ok "$1" "present"; else bad "$1" "${3:-<none>}" "to contain $2"; fi
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
  elif [[ "$out" != *revert* && "$out" != *EvmError* && "$out" != *"custom error"* ]]; then
    bad "$label" "RPC error: ${out%%$'\n'*}" "revert"
  else ok "$label" "reverted"; fi
}
expect_call_ok() {
  local label=$1; shift
  if cast call "$@" --rpc-url "$RPC" >/dev/null 2>&1; then ok "$label" "succeeds"
  else bad "$label" "reverted" "success"; fi
}
have() { # have <label> <value> <varname> -> 0 if set
  if [[ -n "${2:-}" ]]; then return 0; fi
  note "$1" "set \$${3} first"; return 1
}
in_code() { # in_code <needle> <label> <expected count 0|1> -- reads the MASTERCOPY
  local n; n=$(cast code "$MASTERCOPY" --rpc-url "$RPC" 2>/dev/null | tr 'A-F' 'a-f' | grep -c "$1")
  check "$2" "$3" "$n"
}

section_A() {
  echo "A. Before anything — starting state"
  check "Delay owner == old Roles"            "$OLDROLES"    "$(rd $DELAY 'owner()(address)')"
  check "Delay guard unset"                   "$ZERO"        "$(rd $DELAY 'guard()(address)')"
  check "Delay txNonce"                       "$START_NONCE" "$(rd $DELAY 'txNonce()(uint256)')"
  check "Delay queueNonce (queue empty)"      "$START_NONCE" "$(rd $DELAY 'queueNonce()(uint256)')"
  check "Delay txCooldown (7 days)"           "604800"       "$(rd $DELAY 'txCooldown()(uint256)')"
  check "Delay txExpiration"                  "172800"       "$(rd $DELAY 'txExpiration()(uint256)')"
  check "Delay avatar == Term DAO"            "$TERMDAO"     "$(rd $DELAY 'avatar()(address)')"
  check "Delay target == Term DAO"            "$TERMDAO"     "$(rd $DELAY 'target()(address)')"
  check "Delay modules == [Proposer Safe]"    "$PROPOSER"    "$(modules $DELAY)"
  check "Term DAO slot 0 == Safe v1.4.1"      "0x000000000000000000000000${SINGLETON#0x}" "$(st $TERMDAO 0)"
  echo "  the four reads that decide the batch"
  check "old Roles owner == Term DAO"         "$TERMDAO"     "$(rd $OLDROLES 'owner()(address)')"
  contains "Term DAO ring contains the Delay" "$DELAY"       "$(modules $TERMDAO)"
  local n; n=$(cast code $OLDROLES --rpc-url "$RPC" 2>/dev/null | tr 'A-F' 'a-f' | grep -c 639518aaac)
  check "old Roles has callTargetFunctionWithRole" "1"       "$n"
  local t; t=$(st $OLDROLES $S_TARGETS_DELAY)
  if [[ "$(norm "$t")" != "$(norm "$W_ZERO")" && "$t" != "ERR" ]]; then ok "old Roles role 1 targets[Delay] non-zero" "$t"
  else bad "old Roles role 1 targets[Delay] non-zero" "${t:-<none>}" "non-zero (else add the scope/revoke pair)"; fi
  printf '  ----  %-46s %s\n' "old Roles module ring (fixes prevModule)" "$(modules $OLDROLES)"
  local dn; dn=$(rd $TERMDAO 'nonce()(uint256)')
  if [[ -n "$TERMDAO_NONCE" ]]; then check "Term DAO nonce" "$TERMDAO_NONCE" "$dn"
  else note "Term DAO nonce — RECORD THIS" "reads $dn; re-run with TERMDAO_NONCE=$dn for section I"; fi
}

section_B() {
  echo "B. After step 1 — PauseGuard"
  have "PauseGuard checks" "$PAUSEGUARD" PAUSEGUARD || return
  check "supportsInterface(0xe6d7a83a)" "true"  "$(rd $PAUSEGUARD 'supportsInterface(bytes4)(bool)' 0xe6d7a83a)"
  check "supportsInterface(0x01ffc9a7)" "true"  "$(rd $PAUSEGUARD 'supportsInterface(bytes4)(bool)' 0x01ffc9a7)"
  check "paused"                        "false" "$(rd $PAUSEGUARD 'paused()(bool)')"
  check "pauser == PauseSafe"           "$PAUSESAFE" "$(rd $PAUSEGUARD 'pauser()(address)')"
  local admin; admin=$(rd $PAUSEGUARD 'admin()(address)')
  if [[ -n "$admin" ]]; then check "admin == Admin Safe" "$ADMINSAFE" "$admin"
  else check "ADMIN_ROLE held by Admin Safe" "true" \
        "$(rd $PAUSEGUARD 'hasRole(bytes32,address)(bool)' "$(cast keccak ADMIN_ROLE)" $ADMINSAFE)"; fi
  differs "not the ownerless PauseGuard" "$PAUSEGUARD" "$OWNERLESS_PAUSEGUARD"
  if [[ -n "$OWNERLESS_PAUSEGUARD" ]]; then
    check "pauser matches ownerless guard's" "$(rd $OWNERLESS_PAUSEGUARD 'pauser()(address)')" "$(rd $PAUSEGUARD 'pauser()(address)')"
    check "admin matches ownerless guard's"  "$(rd $OWNERLESS_PAUSEGUARD 'admin()(address)')"  "$(rd $PAUSEGUARD 'admin()(address)')"
  fi
  echo "  the shared PauseSafe, unchanged by this deployment"
  check "PauseSafe threshold"           "2"     "$(rd $PAUSESAFE 'getThreshold()(uint256)')"
  check "PauseSafe owner count"         "9"     "$(owners $PAUSESAFE | wc -l | tr -d ' ')"
  printf '  ----  %-46s %s\n' "PauseSafe nonce" "$(rd $PAUSESAFE 'nonce()(uint256)')"
  expect_call_ok "pause() from PauseSafe"     $PAUSEGUARD 'pause()'   --from $PAUSESAFE
  expect_revert  "pause() from Admin Safe"    $PAUSEGUARD 'pause()'   --from $ADMINSAFE
  expect_revert  "unpause() from PauseSafe"   $PAUSEGUARD 'unpause()' --from $PAUSESAFE
  expect_revert  "setPauser() from PauseSafe" $PAUSEGUARD 'setPauser(address)' $ADMINSAFE --from $PAUSESAFE
}

section_C() {
  echo "C. After step 2 — DelayOwnerSafe"
  have "DelayOwnerSafe checks" "$DELAYOWNER" DELAYOWNER || return
  check "VERSION"                        '"1.4.1"' "$(rd $DELAYOWNER 'VERSION()(string)')"
  check "slot 0 == Term DAO slot 0"      "$(st $TERMDAO 0)" "$(st $DELAYOWNER 0)"
  check "threshold"                      "2"       "$(rd $DELAYOWNER 'getThreshold()(uint256)')"
  check "owner count"                    "4"       "$(owners $DELAYOWNER | wc -l | tr -d ' ')"
  check "owners == Proposer Safe signers" "$(owners $PROPOSER | tr '\n' ',')" "$(owners $DELAYOWNER | tr '\n' ',')"
  check "modules == [] for now"          ""        "$(modules $DELAYOWNER)"
  check "nonce"                          "0"       "$(rd $DELAYOWNER 'nonce()(uint256)')"
}

section_D() {
  echo "D. After step 3 — SetTxNonceGuard"
  have "SetTxNonceGuard checks" "$SETGUARD" SETGUARD || return
  check "delay() == this Delay"          "$DELAY" "$(rd $SETGUARD 'delay()(address)')"
  check "supportsInterface(0xe6d7a83a)"  "true"   "$(rd $SETGUARD 'supportsInterface(bytes4)(bool)' 0xe6d7a83a)"
  check "supportsInterface(0x01ffc9a7)"  "true"   "$(rd $SETGUARD 'supportsInterface(bytes4)(bool)' 0x01ffc9a7)"
  differs "not the ownerless SetTxNonceGuard" "$SETGUARD" "$OWNERLESS_SETGUARD"
}

section_E() {
  echo "E. After step 4 — NewGovernor"
  have "NewGovernor checks" "$NEWGOV" NEWGOV || return
  check "votingPeriod (5 days)"    "432000"                  "$(rd $NEWGOV 'votingPeriod()(uint256)')"
  check "votingDelay"              "0"                       "$(rd $NEWGOV 'votingDelay()(uint256)')"
  check "proposalThreshold"        "1000000000000000000000"  "$(rd $NEWGOV 'proposalThreshold()(uint256)')"
  check "token == TERM"            "$TERM"                   "$(rd $NEWGOV 'token()(address)')"
  check "name"                     '"TermFinanceGovernor"'   "$(rd $NEWGOV 'name()(string)')"
  check "quorumNumerator"          "1"                       "$(rd $NEWGOV 'quorumNumerator()(uint256)')"
  check "quorumDenominator"        "100"                     "$(rd $NEWGOV 'quorumDenominator()(uint256)')"
  check "COUNTING_MODE"            '"support=bravo&quorum=for,abstain"' "$(rd $NEWGOV 'COUNTING_MODE()(string)')"
  check "CLOCK_MODE"               '"mode=timestamp&from=default"'      "$(rd $NEWGOV 'CLOCK_MODE()(string)')"
  expect_revert "timelock() absent" $NEWGOV 'timelock()(address)'
  check "ether balance"            "0"                       "$(cast balance $NEWGOV --rpc-url "$RPC" 2>/dev/null)"
  check "TERM balance"             "0"                       "$(rd $TERM 'balanceOf(address)(uint256)' $NEWGOV)"
  check "old Governor votingPeriod (for contrast)" "604800"   "$(rd $OLDGOV 'votingPeriod()(uint256)')"
  local ts; ts=$(cast block latest --field timestamp --rpc-url "$RPC" 2>/dev/null)
  [[ -n "$ts" ]] && check "quorum at now-1h" "1000000000000000000000000" "$(rd $NEWGOV 'quorum(uint256)(uint256)' $((ts-3600)))"
  local nz=""
  for s in 0 1 2 4 5 6 7; do
    [[ "$(norm "$(st $NEWGOV $s)")" != "$(norm "$W_ZERO")" ]] && nz="$nz $s"
  done
  check "storage slots 0,1,2,4-7 empty" "" "$nz"
  printf '  ----  %-46s %s\n' "slot 3 (_name)" "$(st $NEWGOV 3)"
}

section_F() {
  echo "F. After step 5 — NewRoles"
  have "NewRoles checks" "$NEWROLES" NEWROLES || return
  check "owner == Term DAO"              "$TERMDAO"   "$(rd $NEWROLES 'owner()(address)')"
  check "avatar == Term DAO"             "$TERMDAO"   "$(rd $NEWROLES 'avatar()(address)')"
  check "multisend == MultiSendCallOnly" "$MULTISEND" "$(rd $NEWROLES 'multisend()(address)')"
  if [[ -n "$DELAYOWNER" ]]; then check "target == DelayOwnerSafe" "$DELAYOWNER" "$(rd $NEWROLES 'target()(address)')"
  else note "target == DelayOwnerSafe" "set \$DELAYOWNER first; reads $(rd $NEWROLES 'target()(address)')"; fi
  if [[ -n "$NEWGOV" ]]; then
    check "defaultRoles(NewGovernor) == 1" "1"    "$(rd $NEWROLES 'defaultRoles(address)(uint16)' $NEWGOV)"
    check "NewGovernor enabled as module"  "true" "$(rd $NEWROLES 'isModuleEnabled(address)(bool)' $NEWGOV)"
    check "members[NewGovernor] == 1"      "$W_ONE" "$(st $NEWROLES "$(cast index address $NEWGOV $S_MEMBERS_BASE)")"
  else note "NewGovernor-keyed checks" "set \$NEWGOV first"; fi
  local g; g=$(rd $NEWROLES 'guard()(address)')
  if [[ -n "$SETGUARD" ]]; then check "guard == SetTxNonceGuard" "$SETGUARD" "$g"
  else note "guard == SetTxNonceGuard" "set \$SETGUARD first; guard() reads $g"; fi
  [[ -n "$g" && "$(norm "$g")" != "$(norm "$ZERO")" ]] && \
    check "installed guard's delay() == Delay" "$DELAY" "$(rd "$g" 'delay()(address)')"
  check "targets[Delay] == Function (2)" "$W_TWO"      "$(st $NEWROLES $S_TARGETS_DELAY)"
  check "functions[Delay|setTxNonce]"    "$W_FUNCTION" "$(st $NEWROLES $S_FUNCTIONS_SETTXNONCE)"
  echo "  the proxy and the mastercopy it delegates to"
  check "proxy is EIP-1167 -> mastercopy"    "$PROXYCODE"      "$(cast code $NEWROLES --rpc-url "$RPC" 2>/dev/null)"
  check "mastercopy codehash (audited build)" "$MASTERCODEHASH" "$(ch $MASTERCOPY)"
  check "Permissions library codehash"        "$PERMCODEHASH"   "$(ch $PERMLIB)"
  check "mastercopy locked (owner==0x..01)"   "$SENTINEL"       "$(rd $MASTERCOPY 'owner()(address)')"
  in_code 639518aaac      "callTargetFunctionWithRole absent"  0
  in_code 63468721a7      "execTransactionFromModule present"  1
  in_code 635229073f      "execTransactionFromModuleReturnData" 1
  in_code "73$PERMISSIONS" "Permissions library linked"        1
  differs "not the ownerless NewRoles proxy" "$NEWROLES" "$OWNERLESS_NEWROLES"
  note "fork-only: setTxNonce allowed / others denied" "see section F of the plan"
}

section_G() {
  echo "G. After step 6 — NewRoles enabled, still inert"
  if [[ -n "$DELAYOWNER" && -n "$NEWROLES" ]]; then
    check "DelayOwnerSafe modules == [NewRoles]" "$NEWROLES" "$(modules $DELAYOWNER)"
  else note "DelayOwnerSafe modules == [NewRoles]" "set \$DELAYOWNER and \$NEWROLES first"; fi
  check "Delay owner still old Roles" "$OLDROLES" "$(rd $DELAY 'owner()(address)')"
}

section_H() {
  echo "H. After step 7 — the batch is queued, not executed"
  check "Delay queueNonce"            "$((START_NONCE+1))" "$(rd $DELAY 'queueNonce()(uint256)')"
  check "Delay txNonce (nothing ran)" "$START_NONCE"       "$(rd $DELAY 'txNonce()(uint256)')"
  check "Delay owner still old Roles" "$OLDROLES"          "$(rd $DELAY 'owner()(address)')"
  check "old Roles members[Term DAO] still 0" "$W_ZERO"    "$(st $OLDROLES $S_OLDROLES_MEMBER_TERMDAO)"
  local h; h=$(rd $DELAY 'txHash(uint256)(bytes32)' $START_NONCE)
  if [[ -n "$BATCH_TXHASH" ]]; then check "txHash($START_NONCE)" "$BATCH_TXHASH" "$h"
  else note "txHash($START_NONCE)" "set \$BATCH_TXHASH to compare; reads $h"; fi
  if [[ -n "$BATCH_CALLDATA" ]]; then
    check "getTransactionHash(batch)" "$h" \
      "$(rd $DELAY 'getTransactionHash(address,uint256,bytes,uint8)(bytes32)' $MULTISEND 0 "$BATCH_CALLDATA" 1)"
  else note "getTransactionHash(batch)" "set \$BATCH_CALLDATA to re-derive the hash"; fi
  local t0; t0=$(rd $DELAY 'txCreatedAt(uint256)(uint256)' $START_NONCE); t0=${t0%% *}
  when() { date -r "$1" '+%F %T %Z' 2>/dev/null || date -d "@$1" '+%F %T %Z' 2>/dev/null || echo "$1"; }
  [[ -n "$t0" && "$t0" != 0 ]] && printf '  ----  %-46s %s → %s\n' "execution window (7d cooldown)" \
    "$(when $((t0+604800)))" "$(when $((t0+777600)))"
}

section_I() {
  echo "I. After step 8 — the migration landed"
  if [[ -n "$DELAYOWNER" ]]; then check "Delay owner == DelayOwnerSafe" "$DELAYOWNER" "$(rd $DELAY 'owner()(address)')"
  else note "Delay owner == DelayOwnerSafe" "set \$DELAYOWNER first; reads $(rd $DELAY 'owner()(address)')"; fi
  check "Delay txNonce"                   "$((START_NONCE+1))" "$(rd $DELAY 'txNonce()(uint256)')"
  check "Delay queueNonce == txNonce"     "$(rd $DELAY 'txNonce()(uint256)')" "$(rd $DELAY 'queueNonce()(uint256)')"
  contains "Term DAO ring still has the Delay" "$DELAY" "$(modules $TERMDAO)"
  local ring; ring=$(modules $TERMDAO)
  if [[ "$(norm "$ring")" != *"$(norm "$OLDROLES")"* ]]; then ok "old Roles absent from Term DAO ring" "$ring"
  else bad "old Roles absent from Term DAO ring" "$ring" "no old Roles"; fi
  local oring; oring=$(modules $OLDROLES)
  if [[ "$(norm "$oring")" != *"$(norm "$TERMDAO")"* ]]; then ok "Term DAO absent from old Roles ring" "${oring:-<empty>}"
  else bad "Term DAO absent from old Roles ring" "$oring" "no Term DAO"; fi
  check "old Roles grant to Term DAO closed" "$W_ZERO" "$(st $OLDROLES $S_OLDROLES_MEMBER_TERMDAO)"
  local dn; dn=$(rd $TERMDAO 'nonce()(uint256)')
  if [[ -n "$TERMDAO_NONCE" ]]; then check "Term DAO nonce unchanged" "$TERMDAO_NONCE" "$dn"
  else note "Term DAO nonce unchanged" "set \$TERMDAO_NONCE from section A; reads $dn"; fi
}

section_J() {
  echo "J. After step 9 — the guard, and the live veto path"
  local g; g=$(rd $DELAY 'guard()(address)')
  if [[ -n "$PAUSEGUARD" ]]; then check "Delay guard == this PauseGuard" "$PAUSEGUARD" "$g"
  else note "Delay guard == this PauseGuard" "set \$PAUSEGUARD first; reads $g"; fi
  differs "installed guard is not the ownerless one" "$g" "$OWNERLESS_PAUSEGUARD"
  note "fork-only: execution / pause / veto / isolation" "four paths, section J of the plan"
}

section_K() {
  echo "K. After step 10 — fallback handler cleared"
  check "Proposer Safe fallback handler" "$W_ZERO" "$(st $PROPOSER $S_FALLBACK)"
}

section_L() {
  echo "L. Final sweep — full target state"
  section_I
  section_J
  section_K
  echo "  Delay"
  check "Delay modules == [Proposer Safe]" "$PROPOSER" "$(modules $DELAY)"
  check "Delay txCooldown"                 "604800"    "$(rd $DELAY 'txCooldown()(uint256)')"
  check "Delay txExpiration"               "172800"    "$(rd $DELAY 'txExpiration()(uint256)')"
  check "Delay avatar == Term DAO"         "$TERMDAO"  "$(rd $DELAY 'avatar()(address)')"
  check "Delay target == Term DAO"         "$TERMDAO"  "$(rd $DELAY 'target()(address)')"
  echo "  NewRoles"; section_F
  echo "  NewGovernor"; section_E
  echo "  SetTxNonceGuard"; section_D
  echo "  DelayOwnerSafe"; section_C
  echo "  PauseGuard"
  if [[ -n "$PAUSEGUARD" ]]; then
    check "PauseGuard paused"              "false"      "$(rd $PAUSEGUARD 'paused()(bool)')"
    check "PauseGuard pauser == PauseSafe" "$PAUSESAFE" "$(rd $PAUSEGUARD 'pauser()(address)')"
  fi
}

want=${1:-}
case "$want" in
  A|B|C|D|E|F|G|H|I|J|K|L) "section_$want" ;;
  all) for s in A B C D E F G H I J K L; do "section_$s"; echo; done ;;
esac

echo
printf '%s passed, %s failed, %s skipped\n' "$pass" "$fail" "$skip"
[[ $fail -eq 0 ]]
