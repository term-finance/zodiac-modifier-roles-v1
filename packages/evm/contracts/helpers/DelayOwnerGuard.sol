// SPDX-License-Identifier: LGPL-3.0-only
pragma solidity >=0.7.0 <0.9.0;

import "@gnosis.pm/zodiac/contracts/guard/BaseGuard.sol";

interface ISafeAdmin {
    function setGuard(address guard) external;

    function enableModule(address module) external;

    function setFallbackHandler(address handler) external;
}

interface IDelayAdmin {
    function transferOwnership(address newOwner) external;

    function renounceOwnership() external;

    function enableModule(address module) external;

    function setGuard(address guard) external;

    function setAvatar(address avatar) external;

    function setTarget(address target) external;
}

/// @title DelayOwnerGuard - Locks the Delay owner Safe's control over itself and the Delay.
/// @dev Attach with `setGuard` on the Safe that owns the Delay modifier. Safe
/// v1.3.0 and v1.4.1 call checkTransaction from execTransaction only, never
/// from execTransactionFromModule, so this guard sees what the owners sign and
/// nothing a module sends. It therefore blocks the Safe from gaining new
/// modules, and blocks delegate calls, which could otherwise write the guard
/// or module storage directly. Once set, the guard cannot be removed or
/// replaced. The Safe itself is taken from msg.sender rather than pinned, so
/// the guard never rejects a Safe it was installed on by mistake with no way
/// to take it off again.
contract DelayOwnerGuard is BaseGuard {
    /// @dev Delay modifier whose ownership, modules, guard and avatar are locked.
    address public immutable delay;

    /// Only plain calls are allowed, not delegate calls
    error UnexpectedOperation();

    /// The Safe's guard cannot be removed or replaced
    error GuardLocked();

    /// The Safe cannot enable modules, which would bypass this guard
    error ModulesLocked();

    /// The Safe's fallback handler cannot be changed
    error FallbackHandlerLocked();

    /// Delay ownership cannot be transferred or renounced
    error DelayOwnershipLocked();

    /// The Delay cannot enable modules
    error DelayModulesLocked();

    /// The Delay's guard cannot be removed or replaced
    error DelayGuardLocked();

    /// The Delay's avatar and target cannot be changed
    error DelayAvatarLocked();

    constructor(address _delay) {
        delay = _delay;
    }

    /// @dev Reverts on delegate calls and on the Safe and Delay admin calls
    /// that would unlock either one. Everything else, including
    /// delay.setTxNonce and the Safe's owner and threshold management, passes.
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
        if (data.length < 4) {
            return;
        }
        bytes4 selector = bytes4(data);

        if (to == msg.sender) {
            if (selector == ISafeAdmin.setGuard.selector) {
                revert GuardLocked();
            }
            if (selector == ISafeAdmin.enableModule.selector) {
                revert ModulesLocked();
            }
            if (selector == ISafeAdmin.setFallbackHandler.selector) {
                revert FallbackHandlerLocked();
            }
        } else if (to == delay) {
            if (
                selector == IDelayAdmin.transferOwnership.selector ||
                selector == IDelayAdmin.renounceOwnership.selector
            ) {
                revert DelayOwnershipLocked();
            }
            if (selector == IDelayAdmin.enableModule.selector) {
                revert DelayModulesLocked();
            }
            if (selector == IDelayAdmin.setGuard.selector) {
                revert DelayGuardLocked();
            }
            if (
                selector == IDelayAdmin.setAvatar.selector ||
                selector == IDelayAdmin.setTarget.selector
            ) {
                revert DelayAvatarLocked();
            }
        }
    }

    function checkAfterExecution(bytes32, bool) external view override {}
}
