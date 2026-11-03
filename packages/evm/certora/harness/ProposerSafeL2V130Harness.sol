// SPDX-License-Identifier: LGPL-3.0-only
pragma solidity 0.7.6;

import "./GnosisSafeL2V130Harness.sol";

/// @dev The ProposerSafe, as its own contract in a scene that also holds the
/// OwnerlessSafe. Both run GnosisSafeL2 v1.3.0, so both are
/// GnosisSafeL2V130Harness under a different name. It adds nothing to
/// GnosisSafeL2V130Harness.
contract ProposerSafeL2V130Harness is GnosisSafeL2V130Harness {

}
