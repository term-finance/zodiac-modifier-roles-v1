// SPDX-License-Identifier: LGPL-3.0-only
pragma solidity >=0.7.0 <0.9.0;

interface ISafeAdmin {
    function setGuard(address guard) external;

    function enableModule(address module) external;

    function disableModule(address prevModule, address module) external;

    function setFallbackHandler(address handler) external;

    function setModuleGuard(address moduleGuard) external;
}
