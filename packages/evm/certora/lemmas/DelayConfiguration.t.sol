// SPDX-License-Identifier: LGPL-3.0-only
pragma solidity >=0.7.0 <0.9.0;

import {Permissions, Role, Clearance, ExecutionOptions} from "../../contracts/Permissions.sol";

interface SymbolicStorage {
    function enableSymbolicStorage(address account) external;
}

/// @dev Unwritten storage and the Role's base slot are arbitrary, including
///      dormant grants. The library receives the same storage reference shape
///      as a Role selected from the production mapping.
contract DelayConfigurationLemma {
    SymbolicStorage private constant svm = SymbolicStorage(
        address(uint160(uint256(keccak256("svm cheat code"))))
    );

    function check_packedKeyHasExactRepresentation(address target, bytes4 selector) public pure {
        bytes32 actual = Permissions.keyForFunctions(target, selector);
        bytes32 expected = bytes32(
            (uint256(uint160(target)) << 96) | (uint256(uint32(selector)) << 64)
        );
        assert(actual == expected);
    }

    function check_configurationClearsDeniedSelector(
        uint256 roleSlot,
        uint16 roleId,
        address target,
        bytes4 denied,
        bytes4 permitted,
        address observedTarget,
        bytes4 observedSelector
    ) public {
        svm.enableSymbolicStorage(address(this));
        Role storage role;
        assembly {
            role.slot := roleSlot
        }
        bytes32 observedKey = Permissions.keyForFunctions(observedTarget, observedSelector);
        uint256 beforeValue = role.functions[observedKey];

        Permissions.scopeTarget(role, roleId, target);
        Permissions.scopeRevokeFunction(role, roleId, target, denied);
        Permissions.scopeAllowFunction(role, roleId, target, permitted, ExecutionOptions.None);

        assert(role.targets[target].clearance == Clearance.Function);
        assert(role.targets[target].options == ExecutionOptions.None);
        assert(role.functions[Permissions.keyForFunctions(target, permitted)] != 0);
        if (denied != permitted) {
            assert(role.functions[Permissions.keyForFunctions(target, denied)] == 0);
        }
        if (observedTarget != target || (observedSelector != denied && observedSelector != permitted)) {
            assert(role.functions[observedKey] == beforeValue);
        }
    }
}
