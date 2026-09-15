// SPDX-License-Identifier: LGPL-3.0-only
pragma solidity >=0.7.0 <0.9.0;

import "@gnosis.pm/safe-contracts/contracts/common/Enum.sol";

/// @dev Stand-in for the avatar/Delay module that Module.exec routes through.
/// Exists so `target` resolves to an address that actually has code: exec
/// makes a high-level `IAvatar(target).execTransactionFromModule(...)` call
/// returning bool, so solc emits an `extcodesize(target) > 0` guard ahead of
/// the dispatch. Left unlinked, `target` is an arbitrary codeless address and
/// that guard reverts — a revert with nothing to do with permissions, which
/// would otherwise show up as a fake divergence in
/// permissionCheckMatchesExecTransactionWithRole.
///
/// Always succeeds and never reverts, so the exec-side of that comparison
/// contributes no revert behavior of its own and `Permissions.check` is left
/// as the only possible source of a difference.
contract DummyAvatar {
    function execTransactionFromModule(
        address to,
        uint256 value,
        bytes memory data,
        Enum.Operation operation
    ) external returns (bool success) {
        return true;
    }

    function execTransactionFromModuleReturnData(
        address to,
        uint256 value,
        bytes memory data,
        Enum.Operation operation
    ) external returns (bool success, bytes memory returnData) {
        return (true, "");
    }
}
