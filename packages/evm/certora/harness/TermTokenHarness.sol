// SPDX-License-Identifier: LGPL-3.0-only
// Pinned to solc 0.8.20, the compiler the deployed TermToken implementation
// (0xeC222d8AfB8b4E78C418ebc1ab2cA181f19FbadC) was built with.
pragma solidity 0.8.20;

import {TermToken} from "../vendor/TermToken/src-triage/TermToken.sol";
import {Checkpoints} from "@openzeppelin/contracts/utils/structs/Checkpoints.sol";

/// @dev Adds view getters, and nothing else, so its write functions are
/// exactly TermToken's. TermToken is inherited unmodified from the
/// implementation the TERM proxy is to be upgraded to
/// (certora/vendor/TermToken/src-triage).
contract TermTokenHarness is TermToken {
    /// VotesUpgradeable's ERC-7201 storage location, private there
    /// (VotesUpgradeable.sol:49).
    bytes32 private constant VOTES_STORAGE_LOCATION =
        0xe8b26c30fad74198956032a3533d903385d56dd795af560196f9c78d4af40d00;

    /// The Initializable version: 1 once initialize has run on the proxy.
    function initializedVersion() external view returns (uint64) {
        return _getInitializedVersion();
    }

    /// The number of total-supply checkpoints.
    function totalCheckpointsLength() external view returns (uint256) {
        return _votesStorage()._totalCheckpoints._checkpoints.length;
    }

    /// The total-supply checkpoint at position i, read by Solidity indexing,
    /// so it reverts for a position past the end.
    function totalCheckpointAt(uint256 i) external view returns (uint48, uint208) {
        Checkpoints.Checkpoint208 storage checkpoint = _votesStorage()._totalCheckpoints._checkpoints[i];
        return (checkpoint._key, checkpoint._value);
    }

    /// The key of the latest total-supply checkpoint, or 0 when there is none.
    function latestTotalCheckpointKey() external view returns (uint48) {
        Checkpoints.Checkpoint208[] storage checkpoints = _votesStorage()._totalCheckpoints._checkpoints;
        return checkpoints.length == 0 ? 0 : checkpoints[checkpoints.length - 1]._key;
    }

    function _votesStorage() private pure returns (VotesStorage storage $) {
        assembly {
            $.slot := VOTES_STORAGE_LOCATION
        }
    }
}
