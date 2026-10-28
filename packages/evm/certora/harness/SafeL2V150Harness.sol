// SPDX-License-Identifier: LGPL-3.0-only
// Pinned to solc 0.7.6, the compiler the deployed v1.5.0 SafeL2 singleton
// (0xEdd160fEBBD92E350D4D398fb636302fccd67C7e) was built with.
pragma solidity 0.7.6;

import "@safe-global/safe-smart-account/contracts/SafeL2.sol";
import {SafeMath} from "@safe-global/safe-smart-account/contracts/external/SafeMath.sol";

/// @dev Exposes SafeL2 v1.5.0's internal settings as view getters for the
/// specs, and nothing else. SafeL2 is inherited unmodified.
contract SafeL2V150Harness is SafeL2 {
    using SafeMath for uint256;
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

    function moduleGuardAddress() external view returns (address g) {
        bytes32 slot = MODULE_GUARD_STORAGE_SLOT;
        // solhint-disable-next-line no-inline-assembly
        assembly {
            g := sload(slot)
        }
    }

    /// The raw 256-bit word in the fallback handler slot. fallback() treats
    /// the slot as set whenever this word is non-zero, so "no handler" is
    /// stated on the raw word.
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
    /// Safe.sol lines 307-339 (signatureSplit through the GS026 check), with
    /// the loop's `i` and `lastOwner` as inputs and `currentOwner` as the
    /// output. The real loop is
    /// `for (i = 0; i < requiredSignatures; ++i) { <this body> lastOwner = currentOwner; }`,
    /// so proving this body for any `i` and `lastOwner` covers every pass.
    function checkNSignaturesLoopBody(
        address executor,
        bytes32 dataHash,
        bytes memory signatures,
        uint256 requiredSignatures,
        uint256 i,
        address lastOwner
    ) public view returns (address currentOwner) {
        uint256 v; // Implicit conversion from uint8 to uint256 will be done for v received from signatureSplit(...).
        bytes32 r;
        bytes32 s;
        // ---- verbatim from Safe.sol:307-339 ----
        (v, r, s) = signatureSplit(signatures, i);
        if (v == 0) {
            // If v is 0 then it is a contract signature
            // When handling contract signatures the address of the contract is encoded into r
            currentOwner = address(uint160(uint256(r)));

            // Check that signature data pointer (s) is not pointing inside the static part of the signatures bytes
            // This check is not completely accurate, since it is possible that more signatures than the threshold are sent.
            // Here we only check that the pointer is not pointing inside the part that is being processed
            if (uint256(s) < requiredSignatures.mul(65)) revertWithError("GS021");

            // The contract signature check is extracted to a separate function for better compatibility with formal verification
            // A quote from the Certora team:
            // "The assembly code broke the pointer analysis, which switched the prover in failsafe mode, where it is (a) much slower and (b) computes different hashes than in the normal mode."
            // More info here: https://github.com/safe-global/safe-smart-account/pull/661
            checkContractSignature(currentOwner, dataHash, signatures, uint256(s));
        } else if (v == 1) {
            // If v is 1 then it is an approved hash
            // When handling approved hashes the address of the approver is encoded into r
            currentOwner = address(uint160(uint256(r)));
            // Hashes are automatically approved by the sender of the message or when they have been pre-approved via a separate transaction
            if (executor != currentOwner && approvedHashes[currentOwner][dataHash] == 0) revertWithError("GS025");
        } else if (v > 30) {
            // If v > 30 then default va (27,28) has been adjusted for eth_sign flow
            // To support eth_sign and similar we adjust v and hash the messageHash with the Ethereum message prefix before applying ecrecover
            currentOwner = ecrecover(keccak256(abi.encodePacked("\x19Ethereum Signed Message:\n32", dataHash)), uint8(v - 4), r, s);
        } else {
            // Default is the ecrecover flow with the provided data hash
            // Use ecrecover with the messageHash for EOA signatures
            currentOwner = ecrecover(dataHash, uint8(v), r, s);
        }
        if (currentOwner <= lastOwner || owners[currentOwner] == address(0) || currentOwner == SENTINEL_OWNERS)
            revertWithError("GS026");
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
