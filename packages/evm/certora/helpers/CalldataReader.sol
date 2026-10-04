// SPDX-License-Identifier: LGPL-3.0-only
pragma solidity >=0.7.0 <0.9.0;

/// @dev Reads calldata that a spec builds as `bytes`. Kept out of
/// GnosisSafeHarness and SafeV141Harness, whose entry points
/// safeEntryPointsAreAllAccountedFor enumerates.
contract CalldataReader {
    /// The 32-byte word after the 4-byte selector. Reverts if `data` is
    /// shorter than 36 bytes.
    function wordAfterSelector(bytes calldata data) external pure returns (uint256) {
        return abi.decode(data[4:], (uint256));
    }

    /// The 32 bytes of `data` that start `off` bytes in, at any byte offset
    /// (not only word-aligned ones). Reverts if they run past the end of
    /// `data`, so a spec that calls it pins the length first.
    function wordAtByte(bytes calldata data, uint256 off) external pure returns (uint256) {
        return uint256(abi.decode(data[off:off + 32], (bytes32)));
    }

    /// The address that the 32-byte word `off` bytes in encodes. Reverts if
    /// the word is not a clean address (any of its upper 96 bits set), as the
    /// ABI decoder of a 0.8 contract does, and if it runs past the end of
    /// `data`.
    function addressAtByte(bytes calldata data, uint256 off) external pure returns (address) {
        return abi.decode(data[off:off + 32], (address));
    }

    /// Whether `sig` is the one-signature "approved hash" encoding Safe's
    /// checkNSignatures reads for `owner`: 65 bytes, r = the owner's address,
    /// s = 0, v = 1.
    function isApprovedHashSig(bytes calldata sig, address owner) external pure returns (bool) {
        if (sig.length != 65) return false;
        return abi.decode(sig[0:32], (bytes32)) == bytes32(uint256(uint160(owner))) &&
            abi.decode(sig[32:64], (bytes32)) == bytes32(0) &&
            uint8(sig[64]) == 1;
    }
}
