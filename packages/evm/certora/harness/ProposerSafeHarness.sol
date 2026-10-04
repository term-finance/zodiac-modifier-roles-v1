// SPDX-License-Identifier: LGPL-3.0-only
pragma solidity 0.7.6;

import "./GnosisSafeHarness.sol";

/// @dev The ProposerSafe, as its own contract in a scene that also holds the
/// OwnerlessSafe. Both run GnosisSafe v1.3.0, so both are GnosisSafeHarness
/// under a different name. It adds nothing to GnosisSafeHarness.
contract ProposerSafeHarness is GnosisSafeHarness {

}
