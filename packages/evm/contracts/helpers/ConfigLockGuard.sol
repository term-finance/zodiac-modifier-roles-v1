// SPDX-License-Identifier: LGPL-3.0-only
pragma solidity >=0.7.0 <0.9.0;

import "@gnosis.pm/zodiac/contracts/guard/BaseGuard.sol";

interface ISafeAdmin {
    function setGuard(address guard) external;

    function enableModule(address module) external;

    function disableModule(address prevModule, address module) external;

    function setFallbackHandler(address handler) external;
}

interface IModifierAdmin {
    function transferOwnership(address newOwner) external;

    function renounceOwnership() external;

    function enableModule(address module) external;

    function disableModule(address prevModule, address module) external;

    function setGuard(address guard) external;

    function setAvatar(address avatar) external;

    function setTarget(address target) external;
}

/// @title ConfigLockGuard - Locks a Safe's configuration, and that of a Zodiac modifier it owns.
/// @dev Attach with `setGuard` on the Safe. Safe v1.3.0 and v1.4.1 call
/// checkTransaction from execTransaction only, never from
/// execTransactionFromModule, so this guard sees what the owners sign and
/// nothing a module sends. On the Safe itself it blocks setGuard, enableModule,
/// disableModule and setFallbackHandler, and it blocks delegate calls, which
/// could otherwise write the guard, module or handler storage directly. Once
/// set, the guard cannot be removed or replaced. The Safe is taken from
/// msg.sender rather than pinned, so the guard never rejects a Safe it was
/// installed on by mistake with no way to take it off again.
///
/// `lockedModifier` -- the Safe also cannot change that modifier's
/// owner, modules, guard, avatar or target. Its other owner functions (for the
/// Delay: setTxNonce, setTxCooldown, setTxExpiration) stay open. Pass
contract ConfigLockGuard is BaseGuard {
    /// @dev Zodiac modifier whose ownership, modules, guard, avatar and target
    /// are locked.
    address public immutable lockedModifier;

    /// Only plain calls are allowed, not delegate calls
    error UnexpectedOperation();

    /// The Safe's guard cannot be removed or replaced
    error GuardLocked();

    /// The Safe cannot enable or disable modules
    error ModulesLocked();

    /// The Safe's fallback handler cannot be changed
    error FallbackHandlerLocked();

    /// The modifier's ownership cannot be transferred or renounced
    error ModifierOwnershipLocked();

    /// The modifier cannot enable or disable modules
    error ModifierModulesLocked();

    /// The modifier's guard cannot be removed or replaced
    error ModifierGuardLocked();

    /// The modifier's avatar and target cannot be changed
    error ModifierAvatarLocked();

    constructor(address _lockedModifier) {
        lockedModifier = _lockedModifier;
    }

    /// @dev Reverts on delegate calls and on the Safe and modifier admin calls
    /// that would unlock either one. Everything else, including the Safe's
    /// owner and threshold management, passes.
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
            if (
                selector == ISafeAdmin.enableModule.selector ||
                selector == ISafeAdmin.disableModule.selector
            ) {
                revert ModulesLocked();
            }
            if (selector == ISafeAdmin.setFallbackHandler.selector) {
                revert FallbackHandlerLocked();
            }
        } else if (to == lockedModifier) {
            if (
                selector == IModifierAdmin.transferOwnership.selector ||
                selector == IModifierAdmin.renounceOwnership.selector
            ) {
                revert ModifierOwnershipLocked();
            }
            if (
                selector == IModifierAdmin.enableModule.selector ||
                selector == IModifierAdmin.disableModule.selector
            ) {
                revert ModifierModulesLocked();
            }
            if (selector == IModifierAdmin.setGuard.selector) {
                revert ModifierGuardLocked();
            }
            if (
                selector == IModifierAdmin.setAvatar.selector ||
                selector == IModifierAdmin.setTarget.selector
            ) {
                revert ModifierAvatarLocked();
            }
        }
    }

    function checkAfterExecution(bytes32, bool) external view override {}
}
