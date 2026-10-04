// SPDX-License-Identifier: LGPL-3.0-only
pragma solidity >=0.8.5 <0.9.0;

import "@gnosis.pm/safe-contracts/contracts/common/Enum.sol";

/// @dev Stand-in for the DelayOwnerSafe at the Roles Modifier's `target`, for
/// passedVetoReachesTheDelayOwnerSafe (GV-2). It records the module call it
/// receives and returns true. delayOwnerSafeLandsTheVeto (GV-3) shows the
/// real Safe v1.4.1 returns true for that call and sets the Delay's txNonce.
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
