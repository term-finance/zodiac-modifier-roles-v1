/*
 * TermFinanceGovernor: TERM holders can propose the veto, and once it has
 * passed, anyone can execute it and the Roles Modifier forwards it to the
 * DelayOwnerSafe.
 *
 * The veto is the runbook's proposal: one action, calling the Roles Modifier
 * with execTransactionWithRole(Delay, 0, setTxNonce(n), Call, 1, true).
 *
 * The contracts are the deployed code:
 *   Governor        TermFinanceGovernor 0x2B715634134220ffeEE9458b4e34E41A41418607,
 *                   verified source in certora/vendor/TermFinanceGovernor
 *                   (OpenZeppelin v5.2.0, solc 0.8.20)
 *   TERM            TermToken, the implementation 0xeC222d8AfB8b4E78C418ebc1ab2cA181f19FbadC
 *                   behind the TERM proxy 0xC3d21f79C3120A4fFda7A535f8005a7c297799bF,
 *                   verified source in certora/vendor/TermToken (solc 0.8.20)
 *   Roles Modifier  contracts/Roles.sol, which verify_fv_source.sh ties to
 *                   the deployed mastercopy
 *   guard           contracts/helpers/SetTxNonceGuard.sol
 * except the DelayOwnerSafe, which is RecordingAvatar: it records the module
 * call Roles makes and returns true. GV-3 (specs/SafeV141/vetoLandsOnDelay.spec)
 * shows the real Safe v1.4.1 returns true for that call and sets the Delay's
 * txNonce; RecordingAvatar's header says why the two are separate rules. The
 * Delay is DelayTarget, the vendored Delay v1.0.1, used here only as the
 * address and selector the veto names.
 *
 * Modelling notes.
 *   - On chain TERM is an ERC1967 proxy that delegatecalls TermToken. Here
 *     the Governor's token is linked straight to TermToken; the proxy adds
 *     nothing but the delegatecall.
 *   - The Governor's call to its proposal's target is a low-level call to an
 *     address taken from calldata, which the Prover cannot resolve on its
 *     own. The DISPATCH entry routes it to Roles' execTransactionWithRole,
 *     where it lands on chain. Any other unresolved call is havoced
 *     (HAVOC_ALL), which can only make these rules harder to pass, never
 *     easier. Roles' guard and target are linked in the conf.
 *   - The Governor reads TERM through its immutable `_token`, which the conf
 *     links to TermToken. The Prover resolves some of those calls from the
 *     link but not all: the first run left propose's getPastVotes call
 *     unresolved, havoced it to return no data, and the Governor's ABI decoder
 *     reverted. The Governor's DISPATCH list therefore also sends clock,
 *     getPastVotes and getPastTotalSupply to TermToken, where every call
 *     through `_token` lands on chain.
 *   - The Prover replaces most compiler-generated copy loops with a single
 *     copy, but not the ones in propose, where its memory analysis fails at
 *     the description-suffix assembly (Governor.sol:827). It unrolls those
 *     instead, 4 times by default, which is too few to copy the 292-byte
 *     veto calldata, so no execution of propose could succeed and GV-1 held
 *     vacuously (job 94639ac2). The conf unrolls copy loops 32 times
 *     (`-copyLoopUnroll 32`). That covers the calldata and any description
 *     up to 1,024 bytes, the limit optimistic hashing already places on the
 *     description (`hashing_length_bound`).
 */

using TermToken as termToken;
using RolesHarness as roles;
using SetTxNonceGuard as setTxNonceGuard;
using RecordingAvatar as avatar;
using DelayTarget as delay;

methods {
    function proposalSnapshot(uint256) external returns (uint256) envfree;
    function proposalDeadline(uint256) external returns (uint256) envfree;
    function proposalProposer(uint256) external returns (address) envfree;
    function proposalThreshold() external returns (uint256) envfree;
    function votingPeriod() external returns (uint256) envfree;
    function vetoProposalId(address, address, uint256, bytes32) external returns (uint256) envfree;
    function descriptionHashOf(string) external returns (bytes32) envfree;
    function descriptionAllowedFor(address, string) external returns (bool) envfree;

    function roles.memberOf(uint16, address) external returns (bool) envfree;
    function roles.moduleEntry(address) external returns (address) envfree;
    function roles.clearanceOf(uint16, address) external returns (RolesHarness.Clearance) envfree;
    function roles.functionScopeConfigForSelector(uint16, address, uint32) external returns (uint256) envfree;
    function roles.unpackFunctionOptions(uint256) external returns (RolesHarness.ExecutionOptions, bool, uint256) envfree;
    function roles.multisend() external returns (address) envfree;
    function roles.guard() external returns (address) envfree;
    function roles.target() external returns (address) envfree;

    function setTxNonceGuard.delay() external returns (address) envfree;

    function avatar.callCount() external returns (uint256) envfree;
    function avatar.lastCaller() external returns (address) envfree;
    function avatar.lastTo() external returns (address) envfree;
    function avatar.lastValue() external returns (uint256) envfree;
    function avatar.lastDataLength() external returns (uint256) envfree;
    function avatar.lastDataSelector() external returns (uint32) envfree;
    function avatar.lastDataWord() external returns (uint256) envfree;
    function avatar.lastOperation() external returns (uint8) envfree;

    // The Governor's call to its proposal's target (Governor.sol:447-458),
    // and its reads of TERM through `_token` that the link leaves unresolved
    // (GovernorVotes.sol:35 and :62, TermFinanceGovernor.sol:44).
    unresolved external in TermFinanceGovernorHarness._ => DISPATCH [
        RolesHarness.execTransactionWithRole(address, uint256, bytes, Enum.Operation, uint16, bool),
        TermToken.clock(),
        TermToken.getPastVotes(address, uint256),
        TermToken.getPastTotalSupply(uint256)
    ] default HAVOC_ALL;
}

/// Head of the Roles Modifier's module list.
definition SENTINEL() returns address = 0x1;

/// The role the veto runs under.
definition ROLE() returns uint16 = 1;

/*
 * The deployed wiring of the veto path through the Roles Modifier, as the
 * runbook sets it up and the verification plan checks it on chain:
 *   - SetTxNonceGuard is Roles' guard and is pointed at this Delay;
 *   - role 1 is scoped to the Delay (scopeTarget) with setTxNonce allowed
 *     and no value or delegatecall (scopeAllowFunction, options None);
 *   - the Governor is an enabled module on Roles and a member of role 1;
 *   - Roles' target is the DelayOwnerSafe, here RecordingAvatar.
 * The DelayOwnerSafe's side (Roles is a module on it, and it owns the Delay)
 * is GV-3's.
 */
function vetoPathWired() {
    require roles.guard() == setTxNonceGuard;
    require setTxNonceGuard.delay() == delay;

    require roles.target() == avatar;
    require delay != roles;
    require delay != roles.multisend();
    require roles.moduleEntry(SENTINEL()) == SENTINEL();

    require roles.clearanceOf(ROLE(), delay) == RolesHarness.Clearance.Function;
    uint256 scope = roles.functionScopeConfigForSelector(
        ROLE(), delay, sig:DelayTarget.setTxNonce(uint256).selector
    );
    RolesHarness.ExecutionOptions options; bool isWildcarded; uint256 length;
    options, isWildcarded, length = roles.unpackFunctionOptions(scope);
    require options == RolesHarness.ExecutionOptions.None;
    require isWildcarded;

    // The module list's head 0x1 cannot send transactions; the Prover must
    // not place the Governor there.
    require currentContract != SENTINEL();
    require roles.moduleEntry(currentContract) != 0;
    require roles.memberOf(ROLE(), currentContract);
}

/*
 * Any address with at least the proposal threshold of TERM votes (1,000 TERM)
 * at clock() - 1 can propose the veto, for any nonce n and any description
 * (up to 1,024 bytes) propose accepts from it, unless that exact proposal
 * already exists. The new proposal records the caller as proposer, and its
 * vote opens at once (votingDelay is 0) and runs for the voting period
 * (22 hours).
 */
rule holderAboveThresholdCanProposeVeto(uint256 n, string proposalText) {
    env e;
    require e.msg.value == 0;
    // TERM's clock is the block timestamp (TermToken.sol:81-83).
    require e.block.timestamp > 0;
    require to_mathint(e.block.timestamp) < 2^48;

    require termToken.getPastVotes(e, e.msg.sender, assert_uint256(e.block.timestamp - 1))
        >= proposalThreshold();
    require descriptionAllowedFor(e.msg.sender, proposalText);

    uint256 id = vetoProposalId(roles, delay, n, descriptionHashOf(proposalText));
    require proposalSnapshot(id) == 0;

    proposeVeto@withrevert(e, roles, delay, n, proposalText);

    assert !lastReverted,
        "a holder with at least the proposal threshold could not propose the veto";
    assert proposalProposer(id) == e.msg.sender,
        "the veto proposal does not record its proposer";
    assert to_mathint(proposalSnapshot(id)) == to_mathint(e.block.timestamp),
        "the veto's vote does not open when it is proposed";
    assert to_mathint(proposalDeadline(id)) == e.block.timestamp + votingPeriod(),
        "the veto's vote does not run for the voting period";
}

/*
 * Once the veto has passed (its state is Succeeded), anyone's execute
 * succeeds, and the Roles Modifier forwards the veto to the DelayOwnerSafe
 * as exactly one module call: execTransactionFromModule(Delay, 0,
 * setTxNonce(n), Call), from Roles, for any n. Holds under the deployed
 * wiring above, with RecordingAvatar returning true for that call; GV-3
 * shows the real Safe v1.4.1 does.
 */
rule passedVetoReachesTheDelayOwnerSafe(uint256 n, bytes32 descriptionHash) {
    env e;
    require e.msg.value == 0;
    vetoPathWired();
    require avatar.callCount() == 0;

    uint256 id = vetoProposalId(roles, delay, n, descriptionHash);
    require state(e, id) == IGovernor.ProposalState.Succeeded;

    executeVeto@withrevert(e, roles, delay, n, descriptionHash);

    assert !lastReverted,
        "a veto that passed could not be executed";
    assert avatar.callCount() == 1,
        "executing the veto did not make exactly one module call on the DelayOwnerSafe";
    assert avatar.lastCaller() == roles,
        "the module call did not come from the Roles Modifier";
    // Operation 0 is Enum.Operation.Call.
    assert avatar.lastTo() == delay && avatar.lastValue() == 0 && avatar.lastOperation() == 0,
        "the module call is not a zero-value Call to the Delay";
    assert avatar.lastDataLength() == 36
        && avatar.lastDataSelector() == sig:DelayTarget.setTxNonce(uint256).selector
        && avatar.lastDataWord() == n,
        "the module call's data is not setTxNonce(n)";
}

/*
 * The Governor's vote count is TERM's: for any account and any timepoint
 * before the current clock, getVotes on the Governor returns TERM's
 * getPastVotes for that account and timepoint. GP-1
 * (specs/Governor/proposalThreshold.spec) states the proposal threshold
 * against the Governor's own vote count; this rule is what makes that count
 * TERM votes.
 */
rule governorVotesAreTermPastVotes(address account, uint256 timepoint) {
    env e;
    require e.msg.value == 0;
    // TERM's clock is the block timestamp (TermToken.sol:81-83).
    require to_mathint(e.block.timestamp) < 2^48;
    require timepoint < e.block.timestamp;

    uint256 governorVotes = getVotes(e, account, timepoint);
    uint256 termVotes = termToken.getPastVotes(e, account, timepoint);

    assert governorVotes == termVotes,
        "the Governor's vote count differs from TERM's past votes";
}
