// SPDX-License-Identifier: LGPL-3.0-only
pragma solidity ^0.8.20;

import {AccessControlUpgradeable} from "../vendor/TermToken/lib/openzeppelin-contracts-upgradeable/contracts/access/AccessControlUpgradeable.sol";

/// @dev A Term protocol contract's DEVOPS_ROLE method, for
/// specs/Delay/devopsEndToEnd.spec (P1.13 in PROOFS.md).
///
/// The protocol contracts gate their DEVOPS_ROLE methods with OpenZeppelin's
/// `onlyRole(DEVOPS_ROLE)` (for example TermController.updateTreasuryAddress,
/// term-finance-contracts 2.1.3) and do not override `_checkRole` or
/// `hasRole`. This contract does the same, on the vendored OpenZeppelin
/// AccessControlUpgradeable, whose code is the protocol's v5.3.0 copy apart
/// from two comments. DEVOPS_ROLE is keccak256("DEVOPS_ROLE"), as in the
/// protocol. The method records its argument and its caller so a rule can
/// read that it ran and who called it.
contract DevopsRoleTarget is AccessControlUpgradeable {
    bytes32 public constant DEVOPS_ROLE = keccak256("DEVOPS_ROLE");

    uint256 public lastValue;
    address public lastCaller;

    function devopsMethod(uint256 value) external onlyRole(DEVOPS_ROLE) {
        lastValue = value;
        lastCaller = msg.sender;
    }
}
