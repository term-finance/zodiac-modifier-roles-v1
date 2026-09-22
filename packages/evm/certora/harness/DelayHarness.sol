// SPDX-License-Identifier: LGPL-3.0-only
pragma solidity >=0.8.0;

import "../helpers/Delay.sol";

/// @dev Exposes the Zodiac Modifier's internal module linked list as an
/// external view getter for Certora specs, and nothing else. The vendored
/// certora/helpers/Delay.sol is left untouched: this contract only inherits
/// it, so every rule verified here runs against the real mastercopy code.
///
/// `modules` is `mapping(address => address) internal` (Modifier.sol:16) with
/// no public getter. The raw entry, not isModuleEnabled, is what the
/// moduleOnly gate actually reads (Modifier.sol:58-61), and the two diverge at
/// SENTINEL_MODULES, which setupModules self-links (Delay.sol:106-112):
/// moduleOnly accepts it, while isModuleEnabled reports it as not enabled.
contract DelayHarness is Delay {
    constructor(
        address _owner,
        address _avatar,
        address _target,
        uint256 _cooldown,
        uint256 _expiration
    ) Delay(_owner, _avatar, _target, _cooldown, _expiration) {}

    function moduleEntry(address module) external view returns (address) {
        return modules[module];
    }
}
