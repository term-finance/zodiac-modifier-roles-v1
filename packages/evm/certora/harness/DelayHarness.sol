// SPDX-License-Identifier: LGPL-3.0-only
pragma solidity >=0.8.0;

import "../helpers/Delay.sol";

/// @dev Exposes the Modifier's internal module list entry as a view getter,
/// and nothing else. certora/helpers/Delay.sol is inherited unmodified.
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
