// SPDX-License-Identifier: LGPL-3.0-only
pragma solidity >=0.7.0 <0.9.0;

import "@gnosis.pm/zodiac/contracts/guard/BaseGuard.sol";

/// @title PauseGuard - Blocks Delay executions while paused.
/// @dev Attach with `setGuard` on a Zodiac Delay modifier. executeNextTx is the
/// only Delay entry point that reaches Module.exec, so this guard sees
/// executions and never queueing: execTransactionFromModule and
/// execTransactionFromModuleReturnData write the queue and return without
/// calling exec. Queueing therefore stays open while paused, as do the Delay's
/// owner functions (setTxNonce, setGuard, setTxCooldown, ...), which do not go
/// through exec either.
contract PauseGuard is BaseGuard {
    /// @dev The one account allowed to unpause and to set the pauser. Fixed at
    /// deployment.
    address public immutable admin;

    /// @dev The one account allowed to pause.
    address public pauser;

    /// @dev While true, every execution through a Delay this guard is
    /// installed on reverts.
    bool public paused;

    event Paused(address indexed account);
    event Unpaused(address indexed account);
    event PauserSet(address indexed previousPauser, address indexed newPauser);

    /// Admin or pauser is the zero address
    error ZeroAddress();

    /// Already paused
    error AlreadyPaused();

    /// Not currently paused
    error NotPaused();

    /// Caller is not the pauser
    error NotPauser(address caller);

    /// Caller is not the admin
    error NotAdmin(address caller);

    /// Executions are paused
    error ExecutionPaused();

    constructor(address _admin, address _pauser) {
        if (_admin == address(0) || _pauser == address(0)) {
            revert ZeroAddress();
        }

        admin = _admin;
        pauser = _pauser;
        emit PauserSet(address(0), _pauser);
    }

    /// @dev Blocks every execution through the Delay until the admin
    /// unpauses. Entries keep ageing while paused, but the Delay checks expiry
    /// against its current txCooldown and txExpiration, so its owner can revive
    /// an entry that expired during the pause, for example by raising
    /// txCooldown or setting txExpiration to 0. Calling Delay.skipExpired first
    /// (anyone, even while paused) drops it for good, unless txExpiration is 0.
    function pause() external {
        if (msg.sender != pauser) {
            revert NotPauser(msg.sender);
        }
        if (paused) {
            revert AlreadyPaused();
        }
        paused = true;
        emit Paused(msg.sender);
    }

    /// @dev Lifts the pause. Every queue entry that is past its cooldown and
    /// has not expired becomes executable by anyone again immediately.
    function unpause() external {
        if (msg.sender != admin) {
            revert NotAdmin(msg.sender);
        }
        if (!paused) {
            revert NotPaused();
        }
        paused = false;
        emit Unpaused(msg.sender);
    }

    /// @dev Replaces the account allowed to pause. There is no way to leave it
    /// unset: to stand the pauser down, point it at an account that cannot act.
    /// @param account New pauser
    function setPauser(address account) external {
        if (msg.sender != admin) {
            revert NotAdmin(msg.sender);
        }
        if (account == address(0)) {
            revert ZeroAddress();
        }
        emit PauserSet(pauser, account);
        pauser = account;
    }

    /// @dev Reverts while paused, which makes Delay.executeNextTx revert. The
    /// revert rolls back that call's txNonce increment, so the head entry stays
    /// at the head of the queue and blocks every entry behind it.
    function checkTransaction(
        address,
        uint256,
        bytes memory,
        Enum.Operation,
        uint256,
        uint256,
        uint256,
        address,
        address payable,
        bytes memory,
        address
    ) external view override {
        if (paused) {
            revert ExecutionPaused();
        }
    }

    function checkAfterExecution(bytes32, bool) external view override {}
}
