// SPDX-License-Identifier: LGPL-3.0-only
pragma solidity >=0.7.0 <0.9.0;

interface IModifierAdmin {
    function transferOwnership(address newOwner) external;

    function renounceOwnership() external;

    function enableModule(address module) external;

    function disableModule(address prevModule, address module) external;

    function setGuard(address guard) external;

    function setAvatar(address avatar) external;

    function setTarget(address target) external;
}
