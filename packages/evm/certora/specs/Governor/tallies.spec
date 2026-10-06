/*
 * Only votes move a tally: every write function of the Governor except the
 * five voting functions and queue leaves every proposal's tally where it was.
 * queue never succeeds (queueAlwaysReverts, GS-4).
 *
 * The scene is settings.spec's: the deployed TermFinanceGovernor under
 * TermFinanceGovernorSettingsHarness, with its token linked to TermToken.
 */

using TermToken as termToken;

methods {
    function proposalVotes(uint256) external returns (uint256, uint256, uint256) envfree;

    // The Governor's reads of TERM through `_token`, and the arbitrary calls
    // of execute and relay.
    unresolved external in TermFinanceGovernorSettingsHarness._ => DISPATCH [
        TermToken.clock(),
        TermToken.getPastVotes(address, uint256),
        TermToken.getPastTotalSupply(uint256)
    ] default HAVOC_ECF;
}

/// A proposal's three tallies, summed.
function tally(uint256 proposalId) returns mathint {
    uint256 againstVotes;
    uint256 forVotes;
    uint256 abstainVotes;
    againstVotes, forVotes, abstainVotes = proposalVotes(proposalId);
    return againstVotes + forVotes + abstainVotes;
}

/// The five voting functions, covered by voting.spec.
definition isVoting(method f) returns bool =
    f.selector == sig:castVote(uint256, uint8).selector ||
    f.selector == sig:castVoteWithReason(uint256, uint8, string).selector ||
    f.selector == sig:castVoteWithReasonAndParams(uint256, uint8, string, bytes).selector ||
    f.selector == sig:castVoteBySig(uint256, uint8, address, bytes).selector ||
    f.selector == sig:castVoteWithReasonAndParamsBySig(uint256, uint8, address, string, bytes, bytes).selector;

/// queue never succeeds: the Governor has no timelock (GS-4 queueAlwaysReverts).
definition isQueue(method f) returns bool =
    f.selector == sig:queue(address[], uint256[], bytes[], bytes32).selector;

/*
 * Over every write function except the five voting functions and queue, for
 * any caller and arguments, a successful call leaves every tally where it
 * was.
 */
rule nothingButAVoteMovesATally(method f, calldataarg args, uint256 proposalId)
    filtered { f -> !f.isView && !f.isPure && !isVoting(f) && !isQueue(f) }
{
    env e;
    mathint tallyBefore = tally(proposalId);

    f(e, args);

    assert tally(proposalId) == tallyBefore,
        "a function other than a vote moved a tally";
}
