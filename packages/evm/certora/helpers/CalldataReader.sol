// SPDX-License-Identifier: LGPL-3.0-only
pragma solidity >=0.7.0 <0.9.0;

/// @dev Reads the argument of a one-argument call that a spec builds as
/// `bytes`, for GV-3 in specs/SafeV141/vetoLandsOnDelay.spec. That scene has
/// no harness exposing such a reader. The helper is kept out of
/// SafeV141Harness, which five other scenes share and whose entry points
/// SE141-1 enumerates.
contract CalldataReader {
    /// The 32-byte word after the 4-byte selector. Reverts if `data` is
    /// shorter than 36 bytes.
    function wordAfterSelector(bytes calldata data) external pure returns (uint256) {
        return abi.decode(data[4:], (uint256));
    }
}
