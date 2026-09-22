// SPDX-License-Identifier: LGPL-3.0-only
pragma solidity >=0.7.0 <0.9.0;

import "@gnosis.pm/safe-contracts/contracts/common/Enum.sol";

interface IDelayOwnerFunctions {
    function enableModule(address module) external;
}

/// @dev Hostile stand-in for the avatar that Module.exec forwards to, used in
/// place of DummyAvatar in the module-integrity scene.
///
/// DummyAvatar returns true and calls nothing, which is deliberate for the
/// specs it serves but makes any claim about what the avatar's call can do
/// back to the Delay pass vacuously. This avatar does the one thing the
/// threat model cares about: every time the Delay hands it a queue entry, it
/// turns around and tries to enable a module on the Delay that fronted it.
/// That is the shape of the attack this integration exists to rule out — a
/// module reaching the Delay's owner-only surface through an execution rather
/// than through the owner.
///
/// The attempt is swallowed with try/catch and the avatar reports success
/// regardless, so executeNextTx still has a non-reverting path. Without that,
/// the enableModule revert would roll the whole transaction back and there
/// would be no post-state in which to observe that the attempt was made and
/// refused — the same vacuity, one layer down. `attempts` records that the
/// avatar was reached at all; `succeeded` records whether enableModule
/// returned.
contract ReenteringAvatar {
    /// @dev The Delay this avatar fronts. Linked to the harness by the conf.
    address public delay;
    /// @dev The address this avatar tries to smuggle into the module ring.
    address public attacker;

    /// @dev Bumped on every forward, so a witness rule can show the avatar
    /// really was reached and really did try.
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
