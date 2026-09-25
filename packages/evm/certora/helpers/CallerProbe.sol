// SPDX-License-Identifier: LGPL-3.0-only
pragma solidity >=0.7.0 <0.9.0;

/// @dev Records who called it, for fallbackHandlerCallsComeFromTheHandler.
contract CallerProbe {
    address public lastCaller;
    uint256 public hits;

    function record() external {
        lastCaller = msg.sender;
        hits += 1;
    }
}
