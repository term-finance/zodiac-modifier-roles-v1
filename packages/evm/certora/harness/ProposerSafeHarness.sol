// SPDX-License-Identifier: LGPL-3.0-only
pragma solidity 0.7.6;

import "./GnosisSafeHarness.sol";

/// @dev The Proposer Safe, as its own contract in a scene that also holds the
/// Ownerless Safe. Both run the same GnosisSafe v1.3.0 code on chain (P1.9 in
/// PROOFS.md), so both are GnosisSafeHarness under a different name; the
/// Prover tells contracts in a scene apart by name, and the scene needs two.
/// It adds nothing to GnosisSafeHarness.
contract ProposerSafeHarness is GnosisSafeHarness {

}
