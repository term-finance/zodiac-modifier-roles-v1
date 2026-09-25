// SPDX-License-Identifier: LGPL-3.0-only
// Pinned to the compiler the deployed v1.3.0 singleton was built with
// (0xd9Db270c1B5E3Bd161E8c8503c55cEABeE709552, byte-identical to this package's
// artifact). 0.7.6 wraps on overflow where 0.8 reverts, so proving against a
// 0.8 build would be proving different bytecode. Any other compiler fails here.
pragma solidity 0.7.6;

import "@gnosis.pm/safe-contracts/contracts/GnosisSafe.sol";

/// @dev Exposes GnosisSafe v1.3.0's internal settings as external view
/// getters for Certora specs, and nothing else. GnosisSafe is inherited
/// unmodified, so every rule verified here runs against the real v1.3.0 code:
/// the version the Proposer Safe and the Ownerless Safe use on chain.
contract GnosisSafeHarness is GnosisSafe {
    using GnosisSafeMath for uint256;
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

    /// The raw 256-bit word in the fallback handler slot. fallback() treats
    /// the slot as set whenever this word is non-zero (FallbackManager.sol:37,
    /// `if iszero(handler)`), so "no handler" has to be stated on the raw word,
    /// not on an address-typed read, which drops the upper 96 bits.
    function fallbackHandlerSlotWord() external view returns (uint256 w) {
        bytes32 slot = FALLBACK_HANDLER_STORAGE_SLOT;
        // solhint-disable-next-line no-inline-assembly
        assembly {
            w := sload(slot)
        }
    }

    /// The address fallback() calls: the slot word's low 160 bits, which is
    /// all the CALL opcode uses.
    function fallbackHandlerAddress() external view returns (address) {
        bytes32 slot = FALLBACK_HANDLER_STORAGE_SLOT;
        uint256 w;
        // solhint-disable-next-line no-inline-assembly
        assembly {
            w := sload(slot)
        }
        return address(uint160(w));
    }

    /// Whether the raw handler slot word is exactly `handler`, upper 96 bits
    /// included, so specs need not compare an address to a uint256.
    function fallbackHandlerIs(address handler) external view returns (bool) {
        bytes32 slot = FALLBACK_HANDLER_STORAGE_SLOT;
        uint256 w;
        // solhint-disable-next-line no-inline-assembly
        assembly {
            w := sload(slot)
        }
        return w == uint256(uint160(handler));
    }

    /// One pass of checkNSignatures' signature loop, copied verbatim from
    /// GnosisSafe.sol lines 256-301 (signatureSplit through the GS026 check),
    /// with the loop's `i` and `lastOwner` as inputs and `currentOwner` as the
    /// output. The real loop is
    /// `for (i = 0; i < requiredSignatures; i++) { <this body> lastOwner = currentOwner; }`,
    /// so proving this body for any `i` and `lastOwner` covers every pass.
    function checkNSignaturesLoopBody(
        bytes32 dataHash,
        bytes memory data,
        bytes memory signatures,
        uint256 requiredSignatures,
        uint256 i,
        address lastOwner
    ) public view returns (address currentOwner) {
        uint8 v;
        bytes32 r;
        bytes32 s;
        // ---- verbatim from GnosisSafe.sol:256-301 ----
        (v, r, s) = signatureSplit(signatures, i);
        if (v == 0) {
            // If v is 0 then it is a contract signature
            // When handling contract signatures the address of the contract is encoded into r
            currentOwner = address(uint160(uint256(r)));

            // Check that signature data pointer (s) is not pointing inside the static part of the signatures bytes
            // This check is not completely accurate, since it is possible that more signatures than the threshold are send.
            // Here we only check that the pointer is not pointing inside the part that is being processed
            require(uint256(s) >= requiredSignatures.mul(65), "GS021");

            // Check that signature data pointer (s) is in bounds (points to the length of data -> 32 bytes)
            require(uint256(s).add(32) <= signatures.length, "GS022");

            // Check if the contract signature is in bounds: start of data is s + 32 and end is start + signature length
            uint256 contractSignatureLen;
            // solhint-disable-next-line no-inline-assembly
            assembly {
                contractSignatureLen := mload(add(add(signatures, s), 0x20))
            }
            require(uint256(s).add(32).add(contractSignatureLen) <= signatures.length, "GS023");

            // Check signature
            bytes memory contractSignature;
            // solhint-disable-next-line no-inline-assembly
            assembly {
                // The signature data for contract signatures is appended to the concatenated signatures and the offset is stored in s
                contractSignature := add(add(signatures, s), 0x20)
            }
            require(ISignatureValidator(currentOwner).isValidSignature(data, contractSignature) == EIP1271_MAGIC_VALUE, "GS024");
        } else if (v == 1) {
            // If v is 1 then it is an approved hash
            // When handling approved hashes the address of the approver is encoded into r
            currentOwner = address(uint160(uint256(r)));
            // Hashes are automatically approved by the sender of the message or when they have been pre-approved via a separate transaction
            require(msg.sender == currentOwner || approvedHashes[currentOwner][dataHash] != 0, "GS025");
        } else if (v > 30) {
            // If v > 30 then default va (27,28) has been adjusted for eth_sign flow
            // To support eth_sign and similar we adjust v and hash the messageHash with the Ethereum message prefix before applying ecrecover
            currentOwner = ecrecover(keccak256(abi.encodePacked("\x19Ethereum Signed Message:\n32", dataHash)), v - 4, r, s);
        } else {
            // Default is the ecrecover flow with the provided data hash
            // Use ecrecover with the messageHash for EOA signatures
            currentOwner = ecrecover(dataHash, v, r, s);
        }
        require(currentOwner > lastOwner && owners[currentOwner] != address(0) && currentOwner != SENTINEL_OWNERS, "GS026");
        // ---- end verbatim ----
    }

    /// The `v` byte of signature `pos`, as the loop body reads it.
    function signatureTypeAt(bytes memory signatures, uint256 pos) public pure returns (uint8 v) {
        (v, , ) = signatureSplit(signatures, pos);
    }

    /// The function selector at the start of `data` (zero if shorter than 4
    /// bytes), for rules that have the Safe call one of its own functions.
    function selectorOf(bytes memory data) public pure returns (uint32) {
        if (data.length < 4) return 0;
        bytes4 sel;
        // solhint-disable-next-line no-inline-assembly
        assembly {
            sel := mload(add(data, 0x20))
        }
        return uint32(sel);
    }
}
