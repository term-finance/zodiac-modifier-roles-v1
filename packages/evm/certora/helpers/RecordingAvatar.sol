// SPDX-License-Identifier: LGPL-3.0-only
pragma solidity >=0.8.5 <0.9.0;

import "@gnosis.pm/safe-contracts/contracts/common/Enum.sol";

/// @dev Stand-in for the DelayOwnerSafe at the Roles Modifier's `target`, for
/// GV-2 in specs/Governor/veto.spec. It records the module call it receives
/// and returns true.
///
/// GV-2 follows a passed veto from the Governor through the Roles Modifier to
/// this call, and asserts on what was recorded. The call's other side, that
/// the DelayOwnerSafe's `execTransactionFromModule` with those arguments
/// returns true and sets the Delay's txNonce, is GV-3
/// (specs/SafeV141/vetoLandsOnDelay.spec), on the real Safe v1.4.1.
///
/// The two cannot run as one rule. With the Safe inlined behind the
/// Governor's dispatched call to Roles, the Prover (certora-cli 7.31.0) stops
/// with an internal error at the Safe's call to the Delay: every other cut
/// of the path runs, and this one dispatch entry is the difference. Called
/// directly, as in GV-3, the Safe's dispatch works.
///
/// Only `execTransactionFromModule` is here: `execTransactionWithRole`
/// reaches the avatar through Module.exec, which calls nothing else on it.
contract RecordingAvatar {
    uint256 public callCount;
    address public lastCaller;
    address public lastTo;
    uint256 public lastValue;
    uint256 public lastDataLength;
    uint32 public lastDataSelector;
    uint256 public lastDataWord;
    uint8 public lastOperation;

    function execTransactionFromModule(
        address to,
        uint256 value,
        bytes calldata data,
        Enum.Operation operation
    ) external returns (bool success) {
        callCount += 1;
        lastCaller = msg.sender;
        lastTo = to;
        lastValue = value;
        lastDataLength = data.length;
        // The selector, and the word after it: setTxNonce's one argument.
        lastDataSelector = data.length >= 4 ? uint32(bytes4(data[:4])) : 0;
        lastDataWord = data.length >= 36 ? abi.decode(data[4:36], (uint256)) : 0;
        lastOperation = uint8(operation);
        return true;
    }
}
