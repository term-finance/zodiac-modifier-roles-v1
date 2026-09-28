// SPDX-License-Identifier: LGPL-3.0-only
// Pinned to the compiler the deployed Governor was built with
// (0x2B715634134220ffeEE9458b4e34E41A41418607, fully verified on Blockscout:
// solc 0.8.20, optimizer off, EVM paris). Any other compiler fails here.
pragma solidity 0.8.20;

import {TermFinanceGovernor, IVotes} from "../vendor/TermFinanceGovernor/contracts/TermFinanceGovernor.sol";

/// @dev Adds helpers that build the veto proposal and hand it to the real
/// propose, execute and hashProposal, and nothing else. TermFinanceGovernor
/// is inherited unmodified from its verified source
/// (certora/vendor/TermFinanceGovernor), so every rule runs against the
/// deployed Governor code.
///
/// The veto proposal is the one the runbook uses: a single action calling the
/// Roles Modifier with
/// `execTransactionWithRole(delay, 0, setTxNonce(n), Call, 1, true)`.
contract TermFinanceGovernorHarness is TermFinanceGovernor {
    constructor(IVotes _token) TermFinanceGovernor(_token) {}

    /// The calldata the proposal sends to the Roles Modifier.
    function vetoCalldata(address delay, uint256 n) public pure returns (bytes memory) {
        return abi.encodeWithSignature(
            "execTransactionWithRole(address,uint256,bytes,uint8,uint16,bool)",
            delay,
            uint256(0),
            abi.encodeWithSignature("setTxNonce(uint256)", n),
            uint8(0), // Enum.Operation.Call
            uint16(1),
            true
        );
    }

    /// The veto proposal's three arrays, as propose and execute take them.
    function vetoProposal(address roles, address delay, uint256 n)
        public
        pure
        returns (address[] memory targets, uint256[] memory values, bytes[] memory calldatas)
    {
        targets = new address[](1);
        targets[0] = roles;
        values = new uint256[](1);
        values[0] = 0;
        calldatas = new bytes[](1);
        calldatas[0] = vetoCalldata(delay, n);
    }

    /// The real propose, called with the veto proposal. msg.sender is the
    /// caller of this function, as it would be for propose itself.
    function proposeVeto(address roles, address delay, uint256 n, string memory description)
        external
        returns (uint256)
    {
        (address[] memory targets, uint256[] memory values, bytes[] memory calldatas) =
            vetoProposal(roles, delay, n);
        return propose(targets, values, calldatas, description);
    }

    /// The real execute, called with the veto proposal.
    function executeVeto(address roles, address delay, uint256 n, bytes32 descriptionHash)
        external
        payable
        returns (uint256)
    {
        (address[] memory targets, uint256[] memory values, bytes[] memory calldatas) =
            vetoProposal(roles, delay, n);
        return execute(targets, values, calldatas, descriptionHash);
    }

    /// The veto proposal's id, from the real hashProposal.
    function vetoProposalId(address roles, address delay, uint256 n, bytes32 descriptionHash)
        external
        pure
        returns (uint256)
    {
        (address[] memory targets, uint256[] memory values, bytes[] memory calldatas) =
            vetoProposal(roles, delay, n);
        return hashProposal(targets, values, calldatas, descriptionHash);
    }

    /// Whether propose accepts `description` from `proposer`
    /// (Governor.sol:769, the `#proposer=` suffix check).
    function descriptionAllowedFor(address proposer, string memory description) external view returns (bool) {
        return _isValidDescriptionForProposer(proposer, description);
    }

    /// keccak256 of a description, as propose hashes it.
    function descriptionHashOf(string memory description) external pure returns (bytes32) {
        return keccak256(bytes(description));
    }
}
