// SPDX-License-Identifier: LGPL-3.0-only
pragma solidity >=0.7.0 <0.9.0;

import "@gnosis.pm/zodiac/contracts/guard/BaseGuard.sol";

interface IDelay {
    function setTxNonce(uint256 _nonce) external;
}

/// @title SetTxNonceGuard - Restricts a module to calling setTxNonce on one Delay modifier.
/// @dev Attach with `setGuard` on a Zodiac module. Module.exec and
/// Module.execAndReturnData route every transaction through checkTransaction,
/// so while this guard is set the module can do nothing other than invalidate
/// the queue of the Delay it was deployed against.
contract SetTxNonceGuard is BaseGuard {
    /// @dev Delay modifier whose transaction queue may be invalidated.
    address public immutable delay;

    /// Destination is not the Delay modifier
    error UnexpectedTarget(address to);

    /// Only plain calls are allowed, not delegate calls
    error UnexpectedOperation();

    /// Only zero value transactions are allowed
    error UnexpectedValue();

    /// Payload is not an abi encoded setTxNonce(uint256)
    error UnexpectedCalldata();

    constructor(address _delay) {
        delay = _delay;
    }

    /// @dev Reverts unless the transaction is delay.setTxNonce(uint256).
    /// @param to Destination address of module transaction
    /// @param value Ether value of module transaction
    /// @param data Data payload of module transaction
    /// @param operation Operation type of module transaction
    function checkTransaction(
        address to,
        uint256 value,
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
        if (to != delay) {
            revert UnexpectedTarget(to);
        }
        if (operation != Enum.Operation.Call) {
            revert UnexpectedOperation();
        }
        if (value != 0) {
            revert UnexpectedValue();
        }
        // Exact length, so that no extra calldata rides along behind the nonce
        if (data.length != 36 || bytes4(data) != IDelay.setTxNonce.selector) {
            revert UnexpectedCalldata();
        }
    }

    function checkAfterExecution(bytes32, bool) external view override {}
}
