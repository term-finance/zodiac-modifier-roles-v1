#!/usr/bin/env bash
# Usage: build_batch.sh <DelayOwnerSafe>
set -euo pipefail
DELAYOWNER=$1
OWNERLESS=0xb8A1dF43c1c88b13937C0c5CEBbAd15830cAeC03
OLDROLES=0x405b47354CF06A25DE1DDb35EC65F03939E2e8D2
DELAY=0x0C19d8A404079d71E5CA3e32fE3f758Ab543ACdf
SENTINEL=0x0000000000000000000000000000000000000001
MULTISEND=0x40A2aCCbd92BCA938b02010E17A5b8929b49130D

pack() { # $1 = to, $2 = calldata  ->  00 ‖ to ‖ value(32) ‖ len(32) ‖ data
  local hex=${2#0x}
  printf "00%s%064x%064x%s" "$(echo "${1#0x}" | tr 'A-F' 'a-f')" 0 $(( ${#hex} / 2 )) "$hex"
}

INNER1=$(cast calldata 'enableModule(address)' $OWNERLESS)
INNER2=$(cast calldata 'assignRoles(address,uint16[],bool[])' $OWNERLESS '[1]' '[true]')
INNER3=$(cast calldata 'callTargetFunctionWithRole(address,bytes,uint16)' $DELAY "$(cast calldata 'transferOwnership(address)' $DELAYOWNER)" 1)
INNER4=$(cast calldata 'assignRoles(address,uint16[],bool[])' $OWNERLESS '[1]' '[false]')
INNER5=$(cast calldata 'disableModule(address,address)' $SENTINEL $OWNERLESS)
INNER6=$(cast calldata 'disableModule(address,address)' $SENTINEL $OLDROLES)
INNER7=$(cast calldata 'setFallbackHandler(address)' 0x0000000000000000000000000000000000000000)

BATCH=0x$(pack $OLDROLES  $INNER1)$(pack $OLDROLES $INNER2)$(pack $OLDROLES $INNER3)$(pack $OLDROLES $INNER4)$(pack $OLDROLES $INNER5)$(pack $OWNERLESS $INNER6)$(pack $OWNERLESS $INNER7)
MSDATA=$(cast calldata 'multiSend(bytes)' $BATCH)
STEP8=$(cast calldata 'execTransactionFromModule(address,uint256,bytes,uint8)' $MULTISEND 0 $MSDATA 1)
STEP9=$(cast calldata 'executeNextTx(address,uint256,bytes,uint8)' $MULTISEND 0 $MSDATA 1)
HASH=$(cast keccak "0x$(echo ${MULTISEND#0x} | tr 'A-F' 'a-f')$(printf %064x 0)${MSDATA#0x}01")

for i in 1 2 3 4 5 6 7; do v=INNER$i; echo "inner $i: ${!v}"; done
echo; echo "batch bytes ($(( (${#BATCH}-2)/2 )) bytes): $BATCH"
echo; echo "multiSend calldata: $MSDATA"
echo; echo "STEP 8 Delay.execTransactionFromModule calldata: $STEP8"
echo; echo "STEP 9 Delay.executeNextTx calldata:             $STEP9"
echo; echo "expected txHash: $HASH"
