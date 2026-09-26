// SPDX-License-Identifier: LGPL-3.0-only
pragma solidity >=0.7.0 <0.9.0;

import "@gnosis.pm/zodiac/contracts/guard/BaseGuard.sol";

interface IProposerSafeAdmin {
    function setGuard(address guard) external;

    function enableModule(address module) external;
}

/// @title ProposerSafeGuard - Stops the Proposer Safe removing its guard or enabling modules.
/// @dev Attach with `setGuard` on the Proposer Safe. Safe v1.3.0 and v1.4.1
/// call checkTransaction from execTransaction only, never from
/// execTransactionFromModule, so an enabled module would bypass this guard;
/// hence enableModule is blocked. Delegate calls are blocked too, since one
/// could write the guard or module storage directly and undo both locks. Once
/// set, the guard cannot be removed or replaced. The Safe is taken from
/// msg.sender rather than pinned, so the guard has no state and never rejects
/// a Safe it was installed on by mistake with no way to take it off again.
contract ProposerSafeGuard is BaseGuard {
    /// Only plain calls are allowed, not delegate calls
    error UnexpectedOperation();

    /// The Safe's guard cannot be removed or replaced
    error GuardLocked();

    /// The Safe cannot enable modules, which would bypass this guard
    error ModulesLocked();

    /// @dev Reverts on delegate calls and on the Safe calling its own setGuard
    /// or enableModule. Everything else passes, including queueing into the
    /// Delay and the Safe's owner and threshold management.
    /// @param to Destination address of Safe transaction
    /// @param data Data payload of Safe transaction
    /// @param operation Operation type of Safe transaction
    function checkTransaction(
        address to,
        uint256,
        bytes memory data,
        Enum.Operation operation,
        uint256,
        uint256,
        uint256,
        address,
        address payable,
        bytes memory,
        address
    ) external view override {
        if (operation != Enum.Operation.Call) {
            revert UnexpectedOperation();
        }
        if (to != msg.sender || data.length < 4) {
            return;
        }
        bytes4 selector = bytes4(data);
        if (selector == IProposerSafeAdmin.setGuard.selector) {
            revert GuardLocked();
        }
        if (selector == IProposerSafeAdmin.enableModule.selector) {
            revert ModulesLocked();
        }
    }

    function checkAfterExecution(bytes32, bool) external view override {}
}
