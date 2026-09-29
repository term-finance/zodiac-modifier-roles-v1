// SPDX-License-Identifier: LGPL-3.0-only
// Pinned to the compiler the deployed Governor was built with
// (0x2B715634134220ffeEE9458b4e34E41A41418607, fully verified on Blockscout:
// solc 0.8.20, optimizer off, EVM paris). Any other compiler fails here.
pragma solidity 0.8.20;

import {TermFinanceGovernor, IVotes} from "../vendor/TermFinanceGovernor/contracts/TermFinanceGovernor.sol";

/// @dev Adds view getters over the Governor's settings, and nothing else.
/// TermFinanceGovernor is inherited unmodified from its verified source
/// (certora/vendor/TermFinanceGovernor), so every rule runs against the
/// deployed Governor code.
///
/// Kept apart from TermFinanceGovernorHarness on purpose: that harness adds
/// write functions (proposeVeto, executeVeto), and settings.spec quantifies
/// over every write function of the contract it verifies. Every function
/// added here is view or pure, so the write functions of this contract are
/// exactly the deployed Governor's.
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

    /// The address onlyGovernance admits (Governor.sol:224-236). It is the
    /// Governor itself: there is no timelock.
    function executor() external view returns (address) {
        return _executor();
    }
}
