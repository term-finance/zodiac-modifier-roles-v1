/*
 * Governor proposal threshold: any caller whose votes at clock() - 1 are
 * below the proposal threshold cannot create a proposal, for any targets,
 * values, calldatas and description.
 *
 * The Governor is the deployed TermFinanceGovernor under
 * TermFinanceGovernorHarness, with its token linked to TermToken. The
 * Governor's vote count is summarized as an arbitrary value per account and
 * timepoint; governorVotesAreTermPastVotes (GV-4) shows it is TERM's
 * getPastVotes.
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
