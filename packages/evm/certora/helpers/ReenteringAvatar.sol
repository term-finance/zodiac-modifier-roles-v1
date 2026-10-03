// SPDX-License-Identifier: LGPL-3.0-only
pragma solidity >=0.7.0 <0.9.0;

import "@gnosis.pm/safe-contracts/contracts/common/Enum.sol";

interface IDelayOwnerFunctions {
    function enableModule(address module) external;
}

/// @dev Hostile stand-in for the avatar that Module.exec forwards to, used in
/// the module-integrity scene. Every time the Delay forwards to it, it tries
/// to enable a module on the Delay. The attempt is swallowed with try/catch
/// and the avatar reports success, so executeNextTx can still complete.
/// `attempts` records that the avatar was reached, and `succeeded` whether
/// enableModule returned.
contract ReenteringAvatar {
    /// @dev The Delay this avatar fronts. Linked to the harness by the conf.
    address public delay;
    /// @dev The address this avatar tries to add to the Delay's module list.
    address public attacker;

    /// @dev Bumped on every forward.
    uint256 public attempts;
    /// @dev Set only if enableModule returned without reverting.
    bool public succeeded;

    function execTransactionFromModule(
        address,
        uint256,
        bytes memory,
        Enum.Operation
    ) external returns (bool) {
        attempts++;
        try IDelayOwnerFunctions(delay).enableModule(attacker) {
            succeeded = true;
        } catch {}
        return true;
    }

    function execTransactionFromModuleReturnData(
        address,
        uint256,
        bytes memory,
        Enum.Operation
    ) external returns (bool, bytes memory) {
        attempts++;
        try IDelayOwnerFunctions(delay).enableModule(attacker) {
            succeeded = true;
        } catch {}
        return (true, "");
    }
}
