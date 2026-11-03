// SPDX-License-Identifier: LGPL-3.0-only
pragma solidity >=0.7.0 <0.9.0;

// Test only. Compiles GnosisSafe v1.3.0 so the ConfigLockGuard tests can deploy
// it. Kept apart from SafeV141Imports.sol because both versions declare Enum,
// OwnerManager and the other base contracts under the same names.
import "@gnosis.pm/safe-contracts/contracts/GnosisSafe.sol";
import "@gnosis.pm/safe-contracts/contracts/proxies/GnosisSafeProxy.sol";
