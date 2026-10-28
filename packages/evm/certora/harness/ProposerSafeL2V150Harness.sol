// SPDX-License-Identifier: LGPL-3.0-only
pragma solidity 0.7.6;

import "./SafeL2V150Harness.sol";

/// @dev The ProposerSafe, as its own contract in a scene that also holds the
/// OwnerlessSafe. Both run SafeL2 v1.5.0, so both are SafeL2V150Harness
/// under a different name. It adds nothing to SafeL2V150Harness.
contract ProposerSafeL2V150Harness is SafeL2V150Harness {

}
