/*
 * TermFinanceGovernor: nobody below the proposal threshold can create a
 * proposal of any kind.
 *
 * GV-1 (specs/Governor/veto.spec) shows a holder with at least 1,000 TERM of
 * votes at clock() - 1 can propose the veto. This is the other direction: for
 * any caller whose votes at clock() - 1 are below the threshold, and for any
 * targets, values, calldatas and description, propose reverts
 * (GovernorInsufficientProposerVotes, Governor.sol:296-303), so no proposal is
 * recorded. The Governor calling propose on itself through relay is one such
 * caller, with its own votes.
 *
 * The contracts are the deployed code: TermFinanceGovernor
 * 0x2B715634134220ffeEE9458b4e34E41A41418607 through TermFinanceGovernorHarness,
 * with its token linked to TermToken, as in veto.spec.
 *
 * Modelling notes.
 *   - The Governor's vote count, _getVotes (GovernorVotes.sol:57-63), is
 *     summarised as an arbitrary value per account and timepoint, and the rule
 *     requires that value to be below the threshold at clock() - 1. Running
 *     TERM's checkpoint lookup inside propose is what made the first version
 *     of this rule time out. GV-4 `governorVotesAreTermPastVotes` (veto.spec)
 *     shows the Governor's getVotes is TERM's getPastVotes, so the summarised
 *     value is TERM's past votes.
 *   - _isValidDescriptionForProposer (Governor.sol:292) is summarised as an
 *     arbitrary boolean. It is a view function and runs before the threshold
 *     check: if it returns false, propose reverts with
 *     GovernorRestrictedProposer; if true, it goes on to the threshold check.
 *     Either way the rule's claim, that propose reverts, is unaffected, and
 *     the description-suffix parsing it does is no longer in the proof.
 *   - clock() reads TERM's clock through `_token`. The DISPATCH entry sends
 *     that call to TermToken, where it returns the block timestamp.
 */

using TermToken as termToken;

methods {
    function proposalThreshold() external returns (uint256) envfree;

    function GovernorVotes._getVotes(address account, uint256 timepoint, bytes memory) internal returns (uint256)
        => votesAt[account][timepoint];

    function Governor._isValidDescriptionForProposer(address, string memory) internal returns (bool) => NONDET;

    unresolved external in TermFinanceGovernorHarness._ => DISPATCH [
        TermToken.clock()
    ] default HAVOC_ALL;
}

/// The Governor's vote count for an account at a timepoint.
ghost mapping(address => mapping(uint256 => uint256)) votesAt;

rule callerBelowProposalThresholdCannotPropose(
    address[] targets, uint256[] values, bytes[] calldatas, string proposalText
) {
    env e;
    // TERM's clock is the block timestamp (TermToken.sol:81-83).
    require e.block.timestamp > 0;
    require to_mathint(e.block.timestamp) < 2^48;

    require votesAt[e.msg.sender][assert_uint256(e.block.timestamp - 1)] < proposalThreshold();

    propose@withrevert(e, targets, values, calldatas, proposalText);

    assert lastReverted,
        "a caller below the proposal threshold created a proposal";
}
