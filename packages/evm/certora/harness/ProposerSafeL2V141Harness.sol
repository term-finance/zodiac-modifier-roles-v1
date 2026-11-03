// SPDX-License-Identifier: LGPL-3.0-only
pragma solidity 0.7.6;

import "./SafeL2V141Harness.sol";

/// @dev The ProposerSafe, as its own contract in a scene that also holds the
/// OwnerlessSafe. Both run SafeL2 v1.4.1, so both are SafeL2V141Harness
/// under a different name. It adds nothing to SafeL2V141Harness.
contract ProposerSafeL2V141Harness is SafeL2V141Harness {

}
