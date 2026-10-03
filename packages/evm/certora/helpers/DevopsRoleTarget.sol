// SPDX-License-Identifier: LGPL-3.0-only
pragma solidity ^0.8.20;

import {AccessControlUpgradeable} from "../vendor/TermToken/lib/openzeppelin-contracts-upgradeable/contracts/access/AccessControlUpgradeable.sol";

/// @dev A Term protocol contract's DEVOPS_ROLE method, behind OpenZeppelin's
/// `onlyRole(DEVOPS_ROLE)` on the vendored AccessControlUpgradeable.
/// DEVOPS_ROLE is keccak256("DEVOPS_ROLE"), as in the protocol. The method
/// records its argument and its caller.
contract DevopsRoleTarget is AccessControlUpgradeable {
    bytes32 public constant DEVOPS_ROLE = keccak256("DEVOPS_ROLE");

    uint256 public lastValue;
    address public lastCaller;

    function devopsMethod(uint256 value) external onlyRole(DEVOPS_ROLE) {
        lastValue = value;
        lastCaller = msg.sender;
    }
}
