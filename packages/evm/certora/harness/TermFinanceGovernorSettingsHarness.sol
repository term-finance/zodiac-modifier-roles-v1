// SPDX-License-Identifier: LGPL-3.0-only
// Pinned to solc 0.8.20, the compiler the deployed Governor
// (0x2B715634134220ffeEE9458b4e34E41A41418607) was built with.
pragma solidity 0.8.20;

import {TermFinanceGovernor, IVotes} from "../vendor/TermFinanceGovernor/contracts/TermFinanceGovernor.sol";

/// @dev Adds view getters over the Governor's settings, and nothing else, so
/// its write functions are exactly the deployed Governor's.
/// TermFinanceGovernor is inherited unmodified from its verified source
/// (certora/vendor/TermFinanceGovernor).
contract TermFinanceGovernorSettingsHarness is TermFinanceGovernor {
    constructor(IVotes _token) TermFinanceGovernor(_token) {}

    /// CVL cannot compare strings, so the string settings are compared by hash.
    function nameHash() external view returns (bytes32) {
        return keccak256(bytes(name()));
    }

    function versionHash() external view returns (bytes32) {
        return keccak256(bytes(version()));
    }

    function countingModeHash() external pure returns (bytes32) {
        return keccak256(bytes(COUNTING_MODE()));
    }

    /// The address onlyGovernance admits: the Governor itself, as there is no
    /// timelock.
    function executor() external view returns (address) {
        return _executor();
    }

    /// The voting threshold: whether a proposal's votes pass it
    /// (GovernorCountingSimple.sol:67-71).
    function voteSucceeded(uint256 proposalId) external view returns (bool) {
        return _voteSucceeded(proposalId);
    }
}
