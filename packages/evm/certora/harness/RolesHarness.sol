// SPDX-License-Identifier: LGPL-3.0-only
pragma solidity >=0.7.0 <0.9.0;

import "../../contracts/Roles.sol";
import "../../contracts/Permissions.sol";

/// @dev Exposes internal Roles/Permissions state as external view getters for
/// Certora specs. `roles` is `mapping(uint16 => Role) internal` and `Role`
/// contains nested mappings, so each leaf needs its own flat getter.
contract RolesHarness is Roles {
    constructor(
        address _owner,
        address _avatar,
        address _target
    ) Roles(_owner, _avatar, _target) {}

    function memberOf(
        uint16 roleId,
        address member
    ) external view returns (bool) {
        return roles[roleId].members[member];
    }

    /// @dev The raw module linked-list entry, which is what moduleOnly gates
    /// on.
    function moduleEntry(address module) external view returns (address) {
        return modules[module];
    }

    /// @dev Permissions.checkTransaction, the per-entry check that both the
    /// direct path and checkMultisendTransaction's loop call. Declared
    /// `view`, so the parametric rules over write functions skip it.
    function checkEntry(
        uint16 roleId,
        address to,
        uint256 value,
        bytes memory data,
        Enum.Operation operation
    ) external view {
        Permissions.checkTransaction(roles[roleId], to, value, data, operation);
    }

    function clearanceOf(
        uint16 roleId,
        address targetAddress
    ) external view returns (Clearance) {
        return roles[roleId].targets[targetAddress].clearance;
    }

    function optionsOf(
        uint16 roleId,
        address targetAddress
    ) external view returns (ExecutionOptions) {
        return roles[roleId].targets[targetAddress].options;
    }

    /// @dev The function scope config for `data`'s selector, as
    /// checkTransaction keys it.
    function functionScopeConfigForData(
        uint16 roleId,
        address targetAddress,
        bytes memory data
    ) external view returns (uint256) {
        return
            roles[roleId].functions[
                Permissions.keyForFunctions(targetAddress, bytes4(data))
            ];
    }

    /// @dev functionScopeConfigForData, keyed on the selector directly.
    /// uint32 so it takes selectorOf's return type and CVL's
    /// `sig:C.f(...).selector` without a cast.
    function functionScopeConfigForSelector(
        uint16 roleId,
        address targetAddress,
        uint32 functionSig
    ) external view returns (uint256) {
        return
            roles[roleId].functions[
                Permissions.keyForFunctions(targetAddress, bytes4(functionSig))
            ];
    }

    /// @dev Decodes the packed per-function scope config using the real
    /// unpacking logic, rather than reimplementing the bit math in CVL.
    function unpackFunctionOptions(
        uint256 scopeConfig
    )
        external
        pure
        returns (ExecutionOptions options, bool isWildcarded, uint256 length)
    {
        return Permissions.unpackFunction(scopeConfig);
    }

    function unpackParam(
        uint256 scopeConfig,
        uint256 index
    )
        external
        pure
        returns (bool isScoped, ParameterType paramType, Comparison paramComp)
    {
        return Permissions.unpackParameter(scopeConfig, index);
    }

    /// @dev Permissions.pluckStaticValue: the static value of argument
    /// `index`. Reverts exactly when the real function would.
    function pluckStaticValueAt(
        bytes memory data,
        uint256 index
    ) external pure returns (bytes32) {
        return Permissions.pluckStaticValue(data, index);
    }

    /// @dev The selector of `data`, as checkTransaction reads it, as a uint32
    /// to compare against CVL's `sig:C.f(...).selector`.
    function selectorOf(bytes memory data) external pure returns (uint32) {
        return uint32(bytes4(data));
    }

    /// @dev pluckStaticValueAt, widened to uint256.
    function pluckStaticUintAt(
        bytes memory data,
        uint256 index
    ) external pure returns (uint256) {
        return uint256(Permissions.pluckStaticValue(data, index));
    }

    function compValueOfForData(
        uint16 roleId,
        address targetAddress,
        bytes memory data,
        uint8 paramIndex
    ) external view returns (bytes32) {
        return
            roles[roleId].compValues[
                Permissions.keyForCompValues(
                    targetAddress,
                    bytes4(data),
                    paramIndex
                )
            ];
    }

    function compValuesOneOfLengthForData(
        uint16 roleId,
        address targetAddress,
        bytes memory data,
        uint8 paramIndex
    ) external view returns (uint256) {
        return
            roles[roleId]
                .compValuesOneOf[
                    Permissions.keyForCompValues(
                        targetAddress,
                        bytes4(data),
                        paramIndex
                    )
                ]
                .length;
    }

    /// @dev Parses the multisend entry at byte offset `i` exactly as
    /// checkMultisendTransaction does, and returns what checkTransaction
    /// would be called with for that entry. `out` reuses the entry's
    /// dataLength word as its length prefix, as the original does.
    function multisendEntryAt(
        bytes memory data,
        uint256 i
    )
        external
        pure
        returns (
            Enum.Operation operation,
            address to,
            uint256 value,
            uint256 dataLength,
            bytes memory out
        )
    {
        assembly {
            operation := shr(0xf8, mload(add(data, i)))
            to := shr(0x60, mload(add(data, add(i, 0x01))))
            value := mload(add(data, add(i, 0x15)))
            dataLength := mload(add(data, add(i, 0x35)))
            out := add(data, add(i, 0x35))
        }
    }

    function compValuesOneOfAtForData(
        uint16 roleId,
        address targetAddress,
        bytes memory data,
        uint8 paramIndex,
        uint256 i
    ) external view returns (bytes32) {
        return
            roles[roleId].compValuesOneOf[
                Permissions.keyForCompValues(
                    targetAddress,
                    bytes4(data),
                    paramIndex
                )
            ][i];
    }
}
