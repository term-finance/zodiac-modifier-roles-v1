// SPDX-License-Identifier: LGPL-3.0-only
pragma solidity 0.7.6;

import "./SafeV150Harness.sol";

/// @dev The ProposerSafe, as its own contract in a scene that also holds the
/// OwnerlessSafe. Both run Safe v1.5.0, so both are SafeV150Harness
/// under a different name. It adds nothing to SafeV150Harness.
contract ProposerSafeV150Harness is SafeV150Harness {

}
