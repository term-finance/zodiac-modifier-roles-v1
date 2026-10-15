// SPDX-License-Identifier: LGPL-3.0-only
pragma solidity ^0.8.6;
import "../harness/PermissionsKeyHarness.sol";

contract PackedKeyEquivalenceLemma is PermissionsKeyHarness {
    function check_functionKey(address target, uint32 selector) public view {
        (bool actualSuccess, bytes memory actualOutput) = address(this).staticcall(
            abi.encodeWithSelector(this.actualFunctionKey.selector, target, selector)
        );
        (bool modelSuccess, bytes memory modelOutput) = address(this).staticcall(
            abi.encodeWithSelector(this.modelFunctionKey.selector, target, selector)
        );
        assert(actualSuccess && modelSuccess);
        assert(actualOutput.length == 32 && modelOutput.length == 32);
        uint256 actual = abi.decode(actualOutput, (uint256));
        uint256 modeled = abi.decode(modelOutput, (uint256));
        assert(actual == modeled);
        assert(uint160(actual >> 96) == uint160(target));
        assert(uint32(actual >> 64) == selector);
        assert(uint64(actual) == 0);
    }

    function check_compValueKey(address target, uint32 selector, uint256 index) public view {
        (bool actualSuccess, bytes memory actualOutput) = address(this).staticcall(
            abi.encodeWithSelector(this.actualCompValueKey.selector, target, selector, index)
        );
        (bool modelSuccess, bytes memory modelOutput) = address(this).staticcall(
            abi.encodeWithSelector(this.modelCompValueKey.selector, target, selector, index)
        );
        assert(actualSuccess && modelSuccess);
        assert(actualOutput.length == 32 && modelOutput.length == 32);
        uint256 actual = abi.decode(actualOutput, (uint256));
        uint256 modeled = abi.decode(modelOutput, (uint256));
        assert(actual == modeled);
        assert(uint160(actual >> 96) == uint160(target));
        assert(uint32(actual >> 64) == selector);
        assert(uint8(actual >> 56) == uint8(index));
        assert(uint56(actual) == 0);
    }
}
