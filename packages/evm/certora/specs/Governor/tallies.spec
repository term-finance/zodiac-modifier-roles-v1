/*
 * TermFinanceGovernor: nothing but a vote moves a tally.
 *
 * Every write function of the Governor except the five voting functions and
 * queue leaves every proposal's tally (againstVotes + forVotes + abstainVotes)
 * where it was. voting.spec shows a vote adds exactly the voter's votes at the
 * proposal's snapshot, so together a tally only ever moves by voters' TERM
 * votes.
 *
 * Rules:
 *
 *   nothingButAVoteMovesATally
 *     every write function but the five voting functions and queue, for any
 *     caller, any arguments and any starting state, leaves every tally where
 *     it was after a successful call
 *
 * With voting.spec this covers every write function of the Governor: the
 * five voting functions are voting.spec's, queue never succeeds (GS-4
 * queueAlwaysReverts, settings.spec), and this rule takes the rest.
 *
 * The scene and methods block are settings.spec's: the deployed
 * TermFinanceGovernor 0x2B715634134220ffeEE9458b4e34E41A41418607 through
 * TermFinanceGovernorSettingsHarness, which adds only view getters, with its
 * token linked to TermToken. There are no ghosts and no internal summaries,
 * which a tally does not need. In voting.spec, which has both, the Prover
 * stopped with an internal error on this rule's relay instance (error code
 * 3447762733); settings.spec's governorSettingsNeverChange covers relay in
 * this scene without one.
 *
 * Modelling notes.
 *   - As in settings.spec, the arbitrary calls of execute and relay are
 *     havoced with HAVOC_ECF: they may do anything to every contract but the
 *     Governor. A call back into the Governor is itself one of the write
 *     functions covered here or in voting.spec.
 */

using TermToken as termToken;

methods {
    function proposalVotes(uint256) external returns (uint256, uint256, uint256) envfree;

    // As in settings.spec: the Governor's reads of TERM through `_token`, and
    // the arbitrary calls of execute and relay.
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

/// The five voting functions (Governor.sol:532-620), voting.spec's subject.
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
 * queue is left out: it has no successful call to check, and the sanity check
 * would flag it as vacuous. This is the shape of governorSettingsNeverChange.
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
