/*
 * TERM's total supply: TermToken's write functions are exactly nineteen known
 * functions, and its total supply changes only through mint and burn, which
 * only the DEFAULT_ADMIN_ROLE holder can call and which revert while minting
 * or burning is paused, and upgradeToAndCall, which only the UPGRADER_ROLE
 * holder can call. Only the PAUSER_ROLE holder can pause or unpause minting
 * and burning.
 *
 * TermToken is the implementation the TERM proxy is to be upgraded to
 * (certora/vendor/TermToken/src-triage), under TermTokenHarness, which adds
 * only view getters.
 */

methods {
    function totalSupply() external returns (uint256) envfree;
    function hasRole(bytes32, address) external returns (bool) envfree;
    function DEFAULT_ADMIN_ROLE() external returns (bytes32) envfree;
    function UPGRADER_ROLE() external returns (bytes32) envfree;
    function PAUSER_ROLE() external returns (bytes32) envfree;
    function mintingNotPaused() external returns (bool) envfree;
    function burningNotPaused() external returns (bool) envfree;
    function initializedVersion() external returns (uint64) envfree;
    function totalCheckpointsLength() external returns (uint256) envfree;
    function totalCheckpointAt(uint256) external returns (uint48, uint208) envfree;
    function latestTotalCheckpointKey() external returns (uint48) envfree;

    // The calls to the new implementation in upgradeToAndCall.
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

definition isUpgrade(method f) returns bool =
    f.selector == sig:upgradeToAndCall(address, bytes).selector;

definition isInitialize(method f) returns bool =
    f.selector == sig:initialize(address, address, address, uint256, address).selector;

/*
 * TermToken has no write functions besides these nineteen. It declares no
 * fallback and no receive.
 *   ERC-20               transfer, transferFrom, approve, permit
 *   votes                delegate, delegateBySig
 *   supply               mint, burn
 *   pausing              pause, unpause, pauseMinting, unpauseMinting,
 *                        pauseBurning, unpauseBurning
 *   access control       grantRole, revokeRole, renounceRole
 *   upgrade and setup    upgradeToAndCall, initialize
 */
rule termTokenWriteFunctionsAreTheKnownNineteen(method f, calldataarg args)
    filtered { f -> !f.isView && !f.isPure }
{
    env e;

    f@withrevert(e, args);

    assert isErc20(f) || isVotes(f) || isMint(f) || isBurn(f) || isPausing(f) ||
        isAccessControl(f) || isUpgrade(f) || isInitialize(f),
        "TermToken has a write function that is not one of the known nineteen";
}

/* ------------------------------------------------------------------------
 * 2. The total supply moves only through mint and burn
 * --------------------------------------------------------------------- */

/*
 * Over every write function, TERM's total supply changes only through mint or
 * burn. Left out, each with its own rule:
 *   upgradeToAndCall    runs the new implementation's code
 *                       (onlyTheUpgraderCanUpgrade);
 *   initialize          reverts once initialized
 *                       (initializeAlwaysRevertsOnceInitialized).
 */
rule totalSupplyOnlyChangesThroughMintOrBurn(method f, calldataarg args)
    filtered { f -> !f.isView && !f.isPure && !isUpgrade(f) && !isInitialize(f) }
{
    env e;
    uint256 supplyBefore = totalSupply();

    f(e, args);

    assert totalSupply() != supplyBefore => isMint(f) || isBurn(f),
        "TERM's total supply changed through a function other than mint and burn";
}

/*
 * Over every write function except upgradeToAndCall, a total-supply
 * checkpoint keyed before the current timepoint keeps its key and value, and
 * the checkpoints are never shortened. A mint or burn writes one checkpoint,
 * at the current timepoint: Checkpoints._insert overwrites the latest
 * checkpoint when its key is the current timepoint, appends one otherwise,
 * and reverts when the latest key is later. getPastTotalSupply at a past
 * timepoint reads only checkpoints keyed at or before it, so it never
 * changes either, and neither does the quorum for a proposal, read at its
 * snapshot. The checkpoints are read by Solidity indexing, not through the
 * lookup.
 */
rule supplyCheckpointsOnlyChangeAtTheCurrentTimepoint(method f, calldataarg args, uint256 i)
    filtered { f -> !f.isView && !f.isPure && !isUpgrade(f) }
{
    env e;
    require to_mathint(e.block.timestamp) < 2^48;

    uint256 lengthBefore = totalCheckpointsLength();
    require i < lengthBefore;
    uint48 keyBefore;
    uint208 valueBefore;
    keyBefore, valueBefore = totalCheckpointAt(i);
    require keyBefore < e.block.timestamp;

    f(e, args);

    uint48 keyAfter;
    uint208 valueAfter;
    keyAfter, valueAfter = totalCheckpointAt(i);

    assert totalCheckpointsLength() >= lengthBefore,
        "a function shortened TERM's total-supply checkpoints";
    assert keyAfter == keyBefore && valueAfter == valueBefore,
        "a function changed a total-supply checkpoint keyed before the current timepoint";
}

/*
 * Over every write function except upgradeToAndCall, at most one
 * total-supply checkpoint is appended, and when one is, it is keyed at the
 * current timepoint. With supplyCheckpointsOnlyChangeAtTheCurrentTimepoint,
 * every checkpoint keyed before the current timepoint is the same after the
 * call, and every checkpoint added is keyed at the current timepoint.
 */
rule supplyCheckpointsGrowOnlyAtTheCurrentTimepoint(method f, calldataarg args)
    filtered { f -> !f.isView && !f.isPure && !isUpgrade(f) }
{
    env e;
    require to_mathint(e.block.timestamp) < 2^48;
    uint256 lengthBefore = totalCheckpointsLength();

    f(e, args);

    uint256 lengthAfter = totalCheckpointsLength();
    assert to_mathint(lengthAfter) <= lengthBefore + 1,
        "a function appended more than one total-supply checkpoint";
    assert lengthAfter > lengthBefore => latestTotalCheckpointKey() == e.block.timestamp,
        "a function appended a total-supply checkpoint keyed at another timepoint";
}

/*
 * With minting unpaused, a DEFAULT_ADMIN_ROLE holder's mint can append a
 * total-supply checkpoint, so the rule above is not vacuous.
 */
rule supplyCheckpointsCanGrowAtTheCurrentTimepoint(uint256 amount) {
    env e;
    require to_mathint(e.block.timestamp) < 2^48;
    require hasRole(DEFAULT_ADMIN_ROLE(), e.msg.sender);
    require mintingNotPaused();
    uint256 lengthBefore = totalCheckpointsLength();

    mint@withrevert(e, amount);

    satisfy !lastReverted && totalCheckpointsLength() > lengthBefore,
        "a mint cannot append a total-supply checkpoint";
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
 * 3. mint, burn and upgradeToAndCall
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
 * 4. Pausing and unpausing minting and burning
 * --------------------------------------------------------------------- */

/*
 * Over every write function except upgradeToAndCall, mintingNotPaused and
 * burningNotPaused change only through pauseMinting, unpauseMinting,
 * pauseBurning and unpauseBurning.
 */
rule mintingAndBurningPausesOnlyChangeThroughThePausingFunctions(method f, calldataarg args)
    filtered { f -> !f.isView && !f.isPure && !isUpgrade(f) }
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
