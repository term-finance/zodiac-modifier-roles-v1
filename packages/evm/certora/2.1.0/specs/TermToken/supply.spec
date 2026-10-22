/*
 * TERM's total supply: TermToken's write functions are exactly thirty known
 * functions, and its total supply changes only through mint and burn, which
 * only the DEFAULT_ADMIN_ROLE holder can call and which revert while minting
 * or burning is paused, upgradeToAndCall, which only the UPGRADER_ROLE holder
 * can call, and send and lzReceive, which revert while no LayerZero peer is
 * set, and only the owner can set one. Only the PAUSER_ROLE holder can pause
 * or unpause minting and burning.
 *
 * TermToken is term-token PR #24 (certora/vendor/TermToken/src-pr24) under
 * TermTokenHarness, which adds only view getters.
 */

methods {
    function totalSupply() external returns (uint256) envfree;
    function hasRole(bytes32, address) external returns (bool) envfree;
    function DEFAULT_ADMIN_ROLE() external returns (bytes32) envfree;
    function UPGRADER_ROLE() external returns (bytes32) envfree;
    function PAUSER_ROLE() external returns (bytes32) envfree;
    function mintingNotPaused() external returns (bool) envfree;
    function burningNotPaused() external returns (bool) envfree;
    function owner() external returns (address) envfree;
    function peers(uint32) external returns (bytes32) envfree;
    function endpoint() external returns (address) envfree;
    function initializedVersion() external returns (uint64) envfree;
    function totalCheckpointsAreOrdered() external returns (bool) envfree;

    // The endpoint's lzToken, which send pays any lzToken fee in.
    function _.lzToken() external => lzTokenSummary() expect address;

    // The calls to the endpoint, the lzToken, the message inspector and the
    // pre-crime, and the new implementation in upgradeToAndCall. None of them
    // writes TERM's own storage.
    unresolved external in TermTokenHarness._ => DISPATCH [] default HAVOC_ECF;
}

/* ------------------------------------------------------------------------
 * 1. Every write function is accounted for
 * --------------------------------------------------------------------- */

definition isErc20(method f) returns bool =
    f.selector == sig:transfer(address, uint256).selector ||
    f.selector == sig:transferFrom(address, address, uint256).selector ||
    f.selector == sig:approve(address, uint256).selector ||
    f.selector == sig:permit(address, address, uint256, uint256, uint8, bytes32, bytes32).selector;

definition isVotes(method f) returns bool =
    f.selector == sig:delegate(address).selector ||
    f.selector == sig:delegateBySig(address, uint256, uint256, uint8, bytes32, bytes32).selector;

definition isMint(method f) returns bool =
    f.selector == sig:mint(uint256).selector;

definition isBurn(method f) returns bool =
    f.selector == sig:burn(uint256).selector;

/// The four functions that pause and unpause minting and burning.
definition isMintBurnPausing(method f) returns bool =
    f.selector == sig:pauseMinting().selector ||
    f.selector == sig:unpauseMinting().selector ||
    f.selector == sig:pauseBurning().selector ||
    f.selector == sig:unpauseBurning().selector;

definition isPausing(method f) returns bool =
    f.selector == sig:pause().selector ||
    f.selector == sig:unpause().selector ||
    isMintBurnPausing(f);

definition isAccessControl(method f) returns bool =
    f.selector == sig:grantRole(bytes32, address).selector ||
    f.selector == sig:revokeRole(bytes32, address).selector ||
    f.selector == sig:renounceRole(bytes32, address).selector;

definition isOwnable(method f) returns bool =
    f.selector == sig:transferOwnership(address).selector ||
    f.selector == sig:renounceOwnership().selector;

/// setEnforcedOptions((uint32,uint16,bytes)[]) takes a struct array, so it is
/// matched by its selector.
definition isLayerZeroConfig(method f) returns bool =
    f.selector == sig:setPeer(uint32, bytes32).selector ||
    f.selector == sig:setDelegate(address).selector ||
    f.selector == sig:setMsgInspector(address).selector ||
    f.selector == sig:setPreCrime(address).selector ||
    f.selector == 0xb98bd070;

/// send((uint32,bytes32,uint256,uint256,bytes,bytes,bytes),(uint256,uint256),address)
definition isSend(method f) returns bool =
    f.selector == 0xc7c7f5b3;

/// lzReceive((uint32,bytes32,uint64),bytes32,bytes,address,bytes)
definition isLzReceive(method f) returns bool =
    f.selector == 0x13137d65;

/// lzReceiveSimulate((uint32,bytes32,uint64),bytes32,bytes,address,bytes)
definition isLzReceiveSimulate(method f) returns bool =
    f.selector == 0xd045a0dc;

/// lzReceiveAndRevert(((uint32,bytes32,uint64),uint32,address,bytes32,uint256,address,bytes,bytes)[])
definition isLzReceiveAndRevert(method f) returns bool =
    f.selector == 0xbd815db0;

definition isLayerZeroMessaging(method f) returns bool =
    isSend(f) || isLzReceive(f) || isLzReceiveSimulate(f) || isLzReceiveAndRevert(f);

definition isUpgrade(method f) returns bool =
    f.selector == sig:upgradeToAndCall(address, bytes).selector;

definition isInitialize(method f) returns bool =
    f.selector == sig:initialize(address, address, address, uint256, address).selector;

/*
 * TermToken has no write functions besides these thirty. It declares no
 * fallback and no receive.
 *   ERC-20               transfer, transferFrom, approve, permit
 *   votes                delegate, delegateBySig
 *   supply               mint, burn
 *   pausing              pause, unpause, pauseMinting, unpauseMinting,
 *                        pauseBurning, unpauseBurning
 *   access control       grantRole, revokeRole, renounceRole
 *   ownership            transferOwnership, renounceOwnership
 *   LayerZero config     setPeer, setDelegate, setEnforcedOptions,
 *                        setMsgInspector, setPreCrime
 *   LayerZero messaging  send, lzReceive, lzReceiveSimulate,
 *                        lzReceiveAndRevert
 *   upgrade and setup    upgradeToAndCall, initialize
 */
rule termTokenWriteFunctionsAreTheKnownThirty(method f, calldataarg args)
    filtered { f -> !f.isView && !f.isPure }
{
    env e;

    f@withrevert(e, args);

    assert isErc20(f) || isVotes(f) || isMint(f) || isBurn(f) || isPausing(f) ||
        isAccessControl(f) || isOwnable(f) || isLayerZeroConfig(f) ||
        isLayerZeroMessaging(f) || isUpgrade(f) || isInitialize(f),
        "TermToken has a write function that is not one of the known thirty";
}

/* ------------------------------------------------------------------------
 * 2. The total supply moves only through mint, burn, send and lzReceive
 * --------------------------------------------------------------------- */

/*
 * Over every write function, TERM's total supply changes only through mint,
 * burn, send or lzReceive. Left out, each with its own rule:
 *   upgradeToAndCall    runs the new implementation's code
 *                       (onlyTheUpgraderCanUpgrade);
 *   initialize          reverts once initialized
 *                       (initializeAlwaysRevertsOnceInitialized);
 *   lzReceiveSimulate   mints, but only for TERM itself
 *                       (lzReceiveSimulateOnlyCallableByItself);
 *   lzReceiveAndRevert  always reverts (lzReceiveAndRevertAlwaysReverts).
 */
rule totalSupplyOnlyChangesThroughMintBurnSendOrLzReceive(method f, calldataarg args)
    filtered {
        f -> !f.isView && !f.isPure && !isUpgrade(f) && !isInitialize(f) &&
            !isLzReceiveSimulate(f) && !isLzReceiveAndRevert(f)
    }
{
    env e;
    uint256 supplyBefore = totalSupply();

    f(e, args);

    assert totalSupply() != supplyBefore => isMint(f) || isBurn(f) || isSend(f) || isLzReceive(f),
        "TERM's total supply changed through a function other than mint, burn, send and lzReceive";
}

/*
 * Over every write function except upgradeToAndCall, TERM's total supply at
 * a past timepoint never changes. A mint or burn writes a checkpoint at the
 * current timepoint, never an earlier one. So the quorum for a proposal,
 * read at its snapshot, is fixed once the proposal is made.
 * lzReceiveAndRevert is left out: it always reverts
 * (lzReceiveAndRevertAlwaysReverts).
 *
 * The checkpoints start in strictly increasing key order. Checkpoints._insert
 * keeps them so: it reverts on a key earlier than the latest, and overwrites
 * the latest checkpoint on an equal key. Without this, starting storage with
 * two checkpoints at one key lets the binary search return a different one
 * once the array grows.
 */
rule pastTotalSupplyNeverChanges(method f, calldataarg args, uint256 timepoint)
    filtered { f -> !f.isView && !f.isPure && !isUpgrade(f) && !isLzReceiveAndRevert(f) }
{
    env e;
    env eView;
    require eView.block.timestamp == e.block.timestamp;
    require eView.msg.value == 0;
    require to_mathint(e.block.timestamp) < 2^48;
    require timepoint < e.block.timestamp;
    require totalCheckpointsAreOrdered();

    uint256 pastSupplyBefore = getPastTotalSupply(eView, timepoint);

    f(e, args);

    assert getPastTotalSupply(eView, timepoint) == pastSupplyBefore,
        "a function changed TERM's total supply at a past timepoint";
}

/*
 * Once TERM is initialized, initialize always reverts, so its mint cannot
 * run again.
 */
rule initializeAlwaysRevertsOnceInitialized(
    address defaultAdmin, address pauser, address upgrader, uint256 tokenMintSupply, address mintAddress
) {
    env e;
    require initializedVersion() > 0;

    initialize@withrevert(e, defaultAdmin, pauser, upgrader, tokenMintSupply, mintAddress);

    assert lastReverted, "initialize ran on an initialized TermToken";
}

/* ------------------------------------------------------------------------
 * 3. lzReceiveSimulate's mint never persists
 * --------------------------------------------------------------------- */

/*
 * A successful lzReceiveSimulate came from TERM itself. It mints without a
 * peer check (OFTCore.sol:279).
 */
rule lzReceiveSimulateOnlyCallableByItself(method f, calldataarg args)
    filtered { f -> isLzReceiveSimulate(f) }
{
    env e;

    f@withrevert(e, args);

    assert !lastReverted => e.msg.sender == currentContract,
        "lzReceiveSimulate succeeded for a caller other than TERM";
}

/*
 * TERM can call lzReceiveSimulate on itself, so the rule above is not
 * vacuous.
 */
rule lzReceiveSimulateRunsForItself(method f, calldataarg args)
    filtered { f -> isLzReceiveSimulate(f) }
{
    env e;
    require e.msg.sender == currentContract;

    f@withrevert(e, args);

    satisfy !lastReverted, "TERM cannot call lzReceiveSimulate on itself";
}

/// Whether TERM has made a call to itself.
persistent ghost bool callsItself;

hook CALL(uint g, address addr, uint value, uint argsOffset, uint argsLength,
          uint retOffset, uint retLength) uint rc {
    if (addr == currentContract) {
        callsItself = true;
    }
}

/// The endpoint's lzToken.
ghost address lzTokenAddress;

function lzTokenSummary() returns address {
    return lzTokenAddress;
}

/*
 * No write function except lzReceiveAndRevert and upgradeToAndCall makes a
 * call to TERM. upgradeToAndCall runs the new implementation's code, which
 * only the UPGRADER_ROLE holder can install (onlyTheUpgraderCanUpgrade).
 * The endpoint and its lzToken are other contracts than TERM.
 */
rule termTokenOnlyCallsItselfFromLzReceiveAndRevert(method f, calldataarg args)
    filtered { f -> !f.isView && !f.isPure && !isLzReceiveAndRevert(f) && !isUpgrade(f) }
{
    env e;
    require endpoint() != currentContract;
    require lzTokenAddress != currentContract;
    require !callsItself;

    f@withrevert(e, args);

    assert !callsItself, "a function other than lzReceiveAndRevert called TERM";
}

/*
 * Every call to lzReceiveAndRevert reverts, so its calls to lzReceiveSimulate
 * never persist.
 */
rule lzReceiveAndRevertAlwaysReverts(method f, calldataarg args)
    filtered { f -> isLzReceiveAndRevert(f) }
{
    env e;

    f@withrevert(e, args);

    assert lastReverted, "lzReceiveAndRevert succeeded";
}

/* ------------------------------------------------------------------------
 * 4. mint, burn and upgradeToAndCall
 * --------------------------------------------------------------------- */

/*
 * A successful mint or burn came from a DEFAULT_ADMIN_ROLE holder.
 */
rule onlyTheDefaultAdminCanMintOrBurn(method f, calldataarg args)
    filtered { f -> isMint(f) || isBurn(f) }
{
    env e;
    bool callerIsAdmin = hasRole(DEFAULT_ADMIN_ROLE(), e.msg.sender);

    f@withrevert(e, args);

    assert !lastReverted => callerIsAdmin,
        "mint or burn succeeded for a caller without DEFAULT_ADMIN_ROLE";
}

/*
 * While minting is paused, mint always reverts, whoever calls it.
 */
rule mintRevertsWhileMintingPaused(uint256 amount) {
    env e;
    require !mintingNotPaused();

    mint@withrevert(e, amount);

    assert lastReverted, "mint succeeded while minting was paused";
}

/*
 * While burning is paused, burn always reverts, whoever calls it.
 */
rule burnRevertsWhileBurningPaused(uint256 amount) {
    env e;
    require !burningNotPaused();

    burn@withrevert(e, amount);

    assert lastReverted, "burn succeeded while burning was paused";
}

/*
 * With minting unpaused, a DEFAULT_ADMIN_ROLE holder's mint can succeed and
 * raise the total supply, so neither onlyTheDefaultAdminCanMintOrBurn nor
 * mintRevertsWhileMintingPaused is vacuous for mint.
 */
rule defaultAdminCanMint(uint256 amount) {
    env e;
    require hasRole(DEFAULT_ADMIN_ROLE(), e.msg.sender);
    require mintingNotPaused();
    uint256 supplyBefore = totalSupply();

    mint@withrevert(e, amount);

    satisfy !lastReverted && totalSupply() > supplyBefore,
        "the DEFAULT_ADMIN_ROLE holder cannot mint";
}

/*
 * With burning unpaused, a DEFAULT_ADMIN_ROLE holder's burn can succeed and
 * lower the total supply, so neither onlyTheDefaultAdminCanMintOrBurn nor
 * burnRevertsWhileBurningPaused is vacuous for burn.
 */
rule defaultAdminCanBurn(uint256 amount) {
    env e;
    require hasRole(DEFAULT_ADMIN_ROLE(), e.msg.sender);
    require burningNotPaused();
    uint256 supplyBefore = totalSupply();

    burn@withrevert(e, amount);

    satisfy !lastReverted && totalSupply() < supplyBefore,
        "the DEFAULT_ADMIN_ROLE holder cannot burn";
}

/*
 * A successful upgradeToAndCall came from an UPGRADER_ROLE holder. The role
 * is read before the call: once the new implementation runs, it can change
 * anything.
 */
rule onlyTheUpgraderCanUpgrade(address newImplementation, bytes data) {
    env e;
    bool callerIsUpgrader = hasRole(UPGRADER_ROLE(), e.msg.sender);

    upgradeToAndCall@withrevert(e, newImplementation, data);

    assert !lastReverted => callerIsUpgrader,
        "upgradeToAndCall succeeded for a caller without UPGRADER_ROLE";
}

/*
 * An UPGRADER_ROLE holder's upgradeToAndCall can succeed, so the rule above
 * is not vacuous.
 */
rule upgraderCanUpgrade(address newImplementation, bytes data) {
    env e;
    require hasRole(UPGRADER_ROLE(), e.msg.sender);

    upgradeToAndCall@withrevert(e, newImplementation, data);

    satisfy !lastReverted, "the UPGRADER_ROLE holder cannot upgrade";
}

/* ------------------------------------------------------------------------
 * 5. Pausing and unpausing minting and burning
 * --------------------------------------------------------------------- */

/*
 * Over every write function except upgradeToAndCall, mintingNotPaused and
 * burningNotPaused change only through pauseMinting, unpauseMinting,
 * pauseBurning and unpauseBurning. lzReceiveAndRevert is left out: it always
 * reverts (lzReceiveAndRevertAlwaysReverts).
 */
rule mintingAndBurningPausesOnlyChangeThroughThePausingFunctions(method f, calldataarg args)
    filtered { f -> !f.isView && !f.isPure && !isUpgrade(f) && !isLzReceiveAndRevert(f) }
{
    env e;
    bool mintingNotPausedBefore = mintingNotPaused();
    bool burningNotPausedBefore = burningNotPaused();

    f(e, args);

    assert (mintingNotPaused() != mintingNotPausedBefore || burningNotPaused() != burningNotPausedBefore)
        => isMintBurnPausing(f),
        "a function other than pauseMinting, unpauseMinting, pauseBurning and unpauseBurning paused or unpaused minting or burning";
}

/*
 * A successful pauseMinting, unpauseMinting, pauseBurning or unpauseBurning
 * came from a PAUSER_ROLE holder.
 */
rule onlyThePauserCanPauseOrUnpauseMintingAndBurning(method f, calldataarg args)
    filtered { f -> isMintBurnPausing(f) }
{
    env e;
    bool callerIsPauser = hasRole(PAUSER_ROLE(), e.msg.sender);

    f@withrevert(e, args);

    assert !lastReverted => callerIsPauser,
        "minting or burning was paused or unpaused by a caller without PAUSER_ROLE";
}

/*
 * Each of the four can succeed for a PAUSER_ROLE holder and flip its flag,
 * so the two rules above are not vacuous.
 */
rule pauserCanPauseAndUnpauseMintingAndBurning(method f, calldataarg args)
    filtered { f -> isMintBurnPausing(f) }
{
    env e;
    require hasRole(PAUSER_ROLE(), e.msg.sender);
    bool mintingNotPausedBefore = mintingNotPaused();
    bool burningNotPausedBefore = burningNotPaused();

    f@withrevert(e, args);

    satisfy !lastReverted &&
        (mintingNotPaused() != mintingNotPausedBefore || burningNotPaused() != burningNotPausedBefore),
        "the PAUSER_ROLE holder cannot pause or unpause minting or burning";
}

/* ------------------------------------------------------------------------
 * 6. send and lzReceive need a LayerZero peer
 * --------------------------------------------------------------------- */

/// Each chain's LayerZero peer, kept in step with OAppCore's peers mapping.
ghost mapping(uint32 => bytes32) peerOf;

hook Sload bytes32 peer peers[KEY uint32 eid] {
    require peerOf[eid] == peer;
}

hook Sstore peers[KEY uint32 eid] bytes32 peer {
    peerOf[eid] = peer;
}

/*
 * With no peer set for any chain, send always reverts. Its burn comes first
 * (OFTCore.sol:167), but the peer lookup in _lzSend then reverts
 * (OAppSender.sol:87, OAppCore.sol:56), which undoes it.
 */
rule sendRevertsWithoutAPeer(method f, calldataarg args)
    filtered { f -> isSend(f) }
{
    env e;
    require forall uint32 eid. peerOf[eid] == to_bytes32(0);

    f@withrevert(e, args);

    assert lastReverted, "send succeeded with no peer set";
}

/*
 * With no peer set for any chain, lzReceive always reverts: it checks the
 * message's sender against the peer for its source chain
 * (OAppReceiver.sol:96).
 */
rule lzReceiveRevertsWithoutAPeer(method f, calldataarg args)
    filtered { f -> isLzReceive(f) }
{
    env e;
    require forall uint32 eid. peerOf[eid] == to_bytes32(0);

    f@withrevert(e, args);

    assert lastReverted, "lzReceive succeeded with no peer set";
}

/*
 * With a peer set, send can succeed and lower the total supply, so
 * sendRevertsWithoutAPeer is not vacuous.
 */
rule sendBurnsWithAPeer(method f, calldataarg args)
    filtered { f -> isSend(f) }
{
    env e;
    uint256 supplyBefore = totalSupply();

    f@withrevert(e, args);

    satisfy !lastReverted && totalSupply() < supplyBefore, "send cannot burn TERM";
}

/*
 * With a peer set, lzReceive can succeed and raise the total supply, so
 * lzReceiveRevertsWithoutAPeer is not vacuous.
 */
rule lzReceiveMintsWithAPeer(method f, calldataarg args)
    filtered { f -> isLzReceive(f) }
{
    env e;
    uint256 supplyBefore = totalSupply();

    f@withrevert(e, args);

    satisfy !lastReverted && totalSupply() > supplyBefore, "lzReceive cannot mint TERM";
}

definition isSetPeer(method f) returns bool =
    f.selector == sig:setPeer(uint32, bytes32).selector;

/*
 * Over every write function except upgradeToAndCall, a chain's peer changes
 * only through setPeer. lzReceiveAndRevert is left out: it always reverts
 * (lzReceiveAndRevertAlwaysReverts).
 */
rule peersOnlyChangeThroughSetPeer(method f, calldataarg args, uint32 eid)
    filtered { f -> !f.isView && !f.isPure && !isUpgrade(f) && !isLzReceiveAndRevert(f) }
{
    env e;
    bytes32 peerBefore = peers(eid);

    f(e, args);

    assert peers(eid) != peerBefore => isSetPeer(f),
        "a function other than setPeer changed a LayerZero peer";
}

/*
 * A successful setPeer came from the owner.
 */
rule onlyTheOwnerCanSetAPeer(uint32 eid, bytes32 peer) {
    env e;
    address ownerBefore = owner();

    setPeer@withrevert(e, eid, peer);

    assert !lastReverted => e.msg.sender == ownerBefore,
        "setPeer succeeded for a caller other than the owner";
}

/*
 * The owner's setPeer can succeed and set the peer, so the rule above is not
 * vacuous.
 */
rule ownerCanSetAPeer(uint32 eid, bytes32 peer) {
    env e;
    require e.msg.sender == owner();

    setPeer@withrevert(e, eid, peer);

    satisfy !lastReverted && peers(eid) == peer, "the owner cannot set a LayerZero peer";
}
