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

    function selectorForData(bytes memory data) external pure returns (bytes4) {
        return bytes4(data);
    }

    function delayVetoSelector() external pure returns (bytes4) {
        return bytes4(keccak256("setTxNonce(uint256)"));
    }

    /// @dev The raw module linked-list entry. This, not isModuleEnabled, is
    /// what the moduleOnly modifier actually gates on (Modifier.sol:59-62).
    /// The two diverge at SENTINEL_MODULES, which is self-linked by
    /// setupModules (Roles.sol:56-59): moduleOnly accepts it, while
    /// isModuleEnabled reports it as not enabled.
    function moduleEntry(address module) external view returns (address) {
        return modules[module];
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

    /// @dev Mirrors checkTransaction's own `bytes4(data)` truncation
    /// (Permissions.sol:270) so specs never need to slice `data` themselves.
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

    /// @dev Mirrors checkParameters' own Static-value extraction
    /// (Permissions.sol:346-349) so params.spec never reimplements the
    /// calldata layout math. Reverts (CalldataOutOfBounds) exactly when the
    /// real function would; a plain CVL call to this getter (without a
    /// revert-tolerant modifier) therefore restricts a rule to the
    /// in-bounds case for free.
    function pluckStaticValueAt(
        bytes memory data,
        uint256 index
    ) external pure returns (bytes32) {
        return Permissions.pluckStaticValue(data, index);
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

    /// @dev Mirrors checkMultisendTransaction's own per-entry parsing
    /// (Permissions.sol:220-235) exactly, including its zero-copy `out`
    /// slice (a `bytes memory` pointer that reuses the just-read
    /// `dataLength` word, sitting immediately before it in `data`, as its
    /// own length prefix). Given `i`, the byte offset of one entry, returns
    /// what checkTransaction would be called with for that entry.
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
