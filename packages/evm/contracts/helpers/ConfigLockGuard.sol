// SPDX-License-Identifier: LGPL-3.0-only
pragma solidity >=0.7.0 <0.9.0;

import "@gnosis.pm/zodiac/contracts/guard/BaseGuard.sol";
import "../interfaces/ISafeAdmin.sol";
import "../interfaces/IDelay.sol";

/// @title ConfigLockGuard - Locks a Safe's configuration, and that of the Zodiac Delay modifier it owns.
/// @dev Attach with `setGuard` on the Safe. Safe v1.3.0, v1.4.1 and v1.5.0
/// call checkTransaction from execTransaction only, never from
/// execTransactionFromModule, so this guard sees what the owners sign and
/// nothing a module sends. On the Safe itself it blocks setGuard, enableModule,
/// disableModule, setFallbackHandler and v1.5.0's setModuleGuard, and it
/// blocks delegate calls, which could otherwise write the guard, module guard,
/// module or handler storage directly. Once
/// set, only an enabled module can remove or replace the guard, and the owners
/// can no longer enable one, so on a Safe with no module when the guard is set
/// it is permanent. The Safe is taken from msg.sender rather than pinned, so
/// any Safe that installs it keeps its plain calls and owner management
/// instead of having every transaction rejected.
///
/// `lockedDelay` -- the Safe also cannot change that Delay modifier's
/// owner, modules, guard, avatar or target, and cannot call setTxCooldown or
/// setTxExpiration, so the Delay's timing is fixed and the cooldown cannot be
/// lowered to skip the window for vetoes. Its other owner function
/// (setTxNonce, which is the veto) stays open. This guard is built
/// for the Zodiac Delay modifier only; it does not lock other modifiers, such
/// as Roles, whose admin functions differ.
contract ConfigLockGuard is BaseGuard {
    /// @dev Zodiac Delay modifier whose ownership, modules, guard, avatar,
    /// target, cooldown and expiration are locked.
    address public immutable lockedDelay;

    /// Only plain calls are allowed, not delegate calls
    error UnexpectedOperation();

    /// The locked Delay modifier address cannot be zero
    error InvalidLockedDelay();

    /// The Safe's guard cannot be removed or replaced
    error GuardLocked();

    /// The Safe cannot enable or disable modules
    error ModulesLocked();

    /// The Safe's fallback handler cannot be changed
    error FallbackHandlerLocked();

    /// The Safe's module guard (Safe v1.5.0) cannot be set or changed
    error ModuleGuardLocked();

    /// The Delay's ownership cannot be transferred or renounced
    error DelayOwnershipLocked();

    /// The Delay cannot enable or disable modules
    error DelayModulesLocked();

    /// The Delay's guard cannot be removed or replaced
    error DelayGuardLocked();

    /// The Delay's avatar and target cannot be changed
    error DelayAvatarLocked();

    /// The Delay's cooldown and expiration cannot be changed
    error DelayTimingLocked();

    constructor(address _lockedDelay) {
        if (_lockedDelay == address(0)) {
            revert InvalidLockedDelay();
        }
        lockedDelay = _lockedDelay;
    }

    /// @dev Reverts on delegate calls and on the Safe and Delay admin calls
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
        if (to == msg.sender) {
            bytes4 selector = bytes4(data);
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
            if (selector == ISafeAdmin.setModuleGuard.selector) {
                revert ModuleGuardLocked();
            }
        } else if (to == lockedDelay) {
            bytes4 selector = bytes4(data);
            if (
                selector == IDelay.transferOwnership.selector ||
                selector == IDelay.renounceOwnership.selector
            ) {
                revert DelayOwnershipLocked();
            }
            if (
                selector == IDelay.enableModule.selector ||
                selector == IDelay.disableModule.selector
            ) {
                revert DelayModulesLocked();
            }
            if (selector == IDelay.setGuard.selector) {
                revert DelayGuardLocked();
            }
            if (
                selector == IDelay.setAvatar.selector ||
                selector == IDelay.setTarget.selector
            ) {
                revert DelayAvatarLocked();
            }
            if (
                selector == IDelay.setTxCooldown.selector ||
                selector == IDelay.setTxExpiration.selector
            ) {
                revert DelayTimingLocked();
            }
        }
    }

    function checkAfterExecution(bytes32, bool) external view override {}
}
