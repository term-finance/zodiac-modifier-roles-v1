// SPDX-License-Identifier: LGPL-3.0-only
pragma solidity >=0.7.0 <0.9.0;

import "@gnosis.pm/safe-contracts/contracts/GnosisSafe.sol";

/// @dev Exposes GnosisSafe v1.3.0's internal settings as external view
/// getters for Certora specs, and nothing else. GnosisSafe is inherited
/// unmodified, so every rule verified here runs against the real v1.3.0 code:
/// the version the Proposer Safe and the Ownerless Safe use on chain.
contract GnosisSafeHarness is GnosisSafe {
    function moduleEntry(address module) external view returns (address) {
        return modules[module];
    }

    function ownerEntry(address owner) external view returns (address) {
        return owners[owner];
    }

    function thresholdValue() external view returns (uint256) {
        return threshold;
    }

    function guardAddress() external view returns (address g) {
        bytes32 slot = GUARD_STORAGE_SLOT;
        // solhint-disable-next-line no-inline-assembly
        assembly {
            g := sload(slot)
        }
    }

    function fallbackHandlerAddress() external view returns (address h) {
        bytes32 slot = FALLBACK_HANDLER_STORAGE_SLOT;
        // solhint-disable-next-line no-inline-assembly
        assembly {
            h := sload(slot)
        }
    }
}
