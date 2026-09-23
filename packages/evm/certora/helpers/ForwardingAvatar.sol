// SPDX-License-Identifier: LGPL-3.0-only
pragma solidity >=0.7.0 <0.9.0;

import "@gnosis.pm/safe-contracts/contracts/common/Enum.sol";

/// @dev Stand-in for the DelayOwnerSafe on the module path, for the one scene
/// that follows a Governor call all the way into the Delay
/// (specs/Roles/setTxNonceLands.spec). Every other Roles scene links `target`
/// to DummyAvatar, which returns true and forwards nothing.
///
/// The two module entry points are the Safe's own, reduced to what the module
/// path actually does:
///   - the module check is ModuleManager.sol:68, over a flat mapping rather
///     than the Safe's linked list (same predicate for any non-sentinel
///     caller);
///   - the forward is Executor.execute (Executor.sol:8-25) verbatim: a
///     low-level `call` carrying `value` for Operation.Call, a `delegatecall`
///     otherwise, and the inner call's success returned rather than
///     propagated as a revert.
/// Events are dropped. `gasleft()` is passed as the Safe passes it.
///
/// One deliberate deviation. A plain `Call` of `setTxNonce(uint256)` to the
/// linked Delay is made as a typed call rather than through Executor's
/// low-level `call`. Semantically the same — same callee, same selector, same
/// argument, zero value, and the callee's revert returned as `false` rather
/// than propagated — but it lets the Prover resolve the callee through the
/// `ForwardingAvatar:delay` link. Through the low-level path it resolved the
/// function by `unresolved external ... => DISPATCH` but handed it a
/// calldatasize of 0, so the Delay's dispatcher reverted before reaching
/// setTxNonce (first run of governorSetTxNonceLandsWhenDelayAccepts). Every
/// other call still goes through `execute` unchanged.
interface IDelaySetTxNonce {
    function setTxNonce(uint256 _txNonce) external;
}

contract ForwardingAvatar {
    address internal constant SENTINEL_MODULES = address(0x1);

    mapping(address => address) public modules;

    // Linked to DelayTarget in confs/Roles-setTxNonceLands.conf.
    IDelaySetTxNonce public delay;

    function execTransactionFromModule(
        address to,
        uint256 value,
        bytes memory data,
        Enum.Operation operation
    ) public returns (bool success) {
        require(
            msg.sender != SENTINEL_MODULES && modules[msg.sender] != address(0),
            "GS104"
        );
        success = execute(to, value, data, operation, gasleft());
    }

    function execTransactionFromModuleReturnData(
        address to,
        uint256 value,
        bytes memory data,
        Enum.Operation operation
    ) public returns (bool success, bytes memory returnData) {
        success = execTransactionFromModule(to, value, data, operation);
        returnData = "";
    }

    function execute(
        address to,
        uint256 value,
        bytes memory data,
        Enum.Operation operation,
        uint256 txGas
    ) internal returns (bool success) {
        if (
            operation == Enum.Operation.Call &&
            to == address(delay) &&
            value == 0 &&
            data.length >= 36 &&
            bytes4(data) == IDelaySetTxNonce.setTxNonce.selector
        ) {
            uint256 nonce;
            // solhint-disable-next-line no-inline-assembly
            assembly {
                nonce := mload(add(data, 0x24))
            }
            try delay.setTxNonce{gas: txGas}(nonce) {
                success = true;
            } catch {
                success = false;
            }
            return success;
        }
        if (operation == Enum.Operation.DelegateCall) {
            // solhint-disable-next-line no-inline-assembly
            assembly {
                success := delegatecall(txGas, to, add(data, 0x20), mload(data), 0, 0)
            }
        } else {
            // solhint-disable-next-line no-inline-assembly
            assembly {
                success := call(txGas, to, value, add(data, 0x20), mload(data), 0, 0)
            }
        }
    }
}
