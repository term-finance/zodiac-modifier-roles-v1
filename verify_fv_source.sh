#!/usr/bin/env bash
# Usage: verify_fv_source.sh
#
# Proves that the Roles source the Certora specs verify is the same program as
# the mastercopy the migration deploys.
#
# certora/harness/RolesHarness.sol imports ../../contracts/Roles.sol, so the FV
# covers whatever is in contracts/. This recompiles exactly those files with the
# mastercopy's own solc settings and asserts the runtime bytecode matches the
# deployed mastercopy, ignoring only the trailing metadata hash (which encodes
# comments and file paths, not behaviour).
#
# Exit 0 only if they match. Run it in CI next to the FV job.
#
#   RPC=<rpc> ./verify_fv_source.sh
set -uo pipefail

RPC=${RPC:?set RPC to a mainnet endpoint}
MASTERCOPY=${MASTERCOPY:-0x85388a8cd772b19a468F982Dc264C238856939C9}   # Roles v1.0.0, audited
PERMLIB=${PERMLIB:-0x543d1de69b25420685ef723842d0087d9b731b06}         # linked inside it
EVM=${EVM:-packages/evm}

# solc 0.8.6 — the version the mastercopy was built with. Hardhat caches it.
SOLC=${SOLC:-}
if [[ -z "$SOLC" ]]; then
  SOLC=$(ls -1 "$HOME"/Library/Caches/hardhat-nodejs/compilers-v2/*/solc-*-v0.8.6+commit.11564f7e \
               "$HOME"/.cache/hardhat-nodejs/compilers-v2/*/solc-*-v0.8.6+commit.11564f7e 2>/dev/null | head -1)
fi
[[ -x "$SOLC" ]] || { echo "solc 0.8.6 not found; set \$SOLC (hardhat caches it after a compile)" >&2; exit 2; }

work=$(mktemp -d); trap 'rm -rf "$work"' EXIT

# The audited compilation unit: our two files plus these twelve, all resolved
# from node_modules. Every one is byte-identical to the registry's recorded
# input, so pinning our two files pins the whole program.
python3 - "$EVM" "$PERMLIB" > "$work/in.json" <<'PY'
import json,os,sys
evm,lib=sys.argv[1],sys.argv[2]
deps=["@gnosis.pm/zodiac/contracts/core/Modifier.sol",
      "@gnosis.pm/zodiac/contracts/core/Module.sol",
      "@gnosis.pm/zodiac/contracts/interfaces/IAvatar.sol",
      "@gnosis.pm/zodiac/contracts/factory/FactoryFriendly.sol",
      "@gnosis.pm/zodiac/contracts/guard/Guardable.sol",
      "@gnosis.pm/zodiac/contracts/guard/BaseGuard.sol",
      "@gnosis.pm/zodiac/contracts/interfaces/IGuard.sol",
      "@gnosis.pm/safe-contracts/contracts/common/Enum.sol",
      "@gnosis.pm/safe-contracts/contracts/interfaces/IERC165.sol",
      "@openzeppelin/contracts-upgradeable/access/OwnableUpgradeable.sol",
      "@openzeppelin/contracts-upgradeable/utils/ContextUpgradeable.sol",
      "@openzeppelin/contracts-upgradeable/proxy/utils/Initializable.sol"]
src={}
for f in ("contracts/Roles.sol","contracts/Permissions.sol"):
    src[f]={"content":open(os.path.join(evm,f)).read()}
for d in deps:
    p=os.path.join(evm,"node_modules",d)
    if not os.path.exists(p):
        sys.exit(f"missing dependency {d} — run yarn/npm install in {evm}")
    src[d]={"content":open(p).read()}
json.dump({"language":"Solidity","sources":src,"settings":{
    "optimizer":{"enabled":False,"runs":200},          # the mastercopy's settings
    "metadata":{"useLiteralContent":True},
    "libraries":{"contracts/Permissions.sol":{"Permissions":lib}},
    "outputSelection":{"*":{"*":["evm.deployedBytecode.object"]}}}},sys.stdout)
PY

"$SOLC" --standard-json "$work/in.json" > "$work/out.json" 2>&1
cast code "$MASTERCOPY" --rpc-url "$RPC" 2>/dev/null | tr 'A-F' 'a-f' > "$work/onchain.hex"

python3 - "$work" "$MASTERCOPY" <<'PY'
import json,sys
work,mc=sys.argv[1],sys.argv[2]
def strip_meta(h):
    h=h.strip().lower()
    if h.startswith("0x"): h=h[2:]
    if not h: return ""
    n=int(h[-4:],16)                 # CBOR length lives in the last two bytes
    return h[:-(n*2+4)]
o=json.load(open(f"{work}/out.json"))
errs=[e for e in o.get("errors",[]) if e.get("severity")=="error"]
if errs:
    print("FAIL  source does not compile:")
    for e in errs[:5]: print("   ",e.get("formattedMessage","")[:300])
    sys.exit(1)
got=strip_meta(o["contracts"]["contracts/Roles.sol"]["Roles"]["evm"]["deployedBytecode"]["object"])
want=strip_meta(open(f"{work}/onchain.hex").read())
if not want:
    print(f"FAIL  no code at mastercopy {mc} — wrong chain or bad RPC?"); sys.exit(1)
if got==want:
    print(f"PASS  contracts/ compiles to the deployed mastercopy {mc}")
    print(f"      {len(got)//2} bytes of runtime code, metadata hash excluded")
    print("      the Certora specs therefore verify the code that will be deployed")
    sys.exit(0)
print(f"FAIL  contracts/ does NOT match mastercopy {mc}")
print(f"      compiled {len(got)//2} bytes, on chain {len(want)//2} bytes")
n=min(len(got),len(want)); i=0
while i<n and got[i]==want[i]: i+=1
print(f"      first difference at byte {i//2}")
print("      the FV is proving properties of code that will not be deployed")
sys.exit(1)
PY
