// SPDX-License-Identifier: LGPL-3.0-only
pragma solidity 0.7.6;

import "./GnosisSafeHarness.sol";

/// @dev The Ownerless Safe, as its own contract in a scene that also holds the
/// Proposer Safe. See ProposerSafeHarness. It adds nothing to
/// GnosisSafeHarness.
contract OwnerlessSafeHarness is GnosisSafeHarness {

}
