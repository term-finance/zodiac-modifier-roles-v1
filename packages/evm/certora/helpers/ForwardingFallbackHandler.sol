// SPDX-License-Identifier: LGPL-3.0-only
pragma solidity >=0.7.0 <0.9.0;

import "./CallerProbe.sol";

/// @dev Stand-in fallback handler for fallbackHandlerCallsComeFromTheHandler.
/// Whatever the Safe's fallback() sends it, it makes one call onward, to
/// `target` (linked to CallerProbe), so the rule can check who that call
/// comes from. Every entry point forwards the same way: `handle` for its own
/// selector, fallback() for any other.
contract ForwardingFallbackHandler {
    address internal target;

    function handle() external {
        CallerProbe(target).record();
    }

    fallback() external {
        CallerProbe(target).record();
    }
}
