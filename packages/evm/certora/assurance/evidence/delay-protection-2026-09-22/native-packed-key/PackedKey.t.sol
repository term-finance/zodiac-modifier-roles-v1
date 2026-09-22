// SPDX-License-Identifier: MIT
pragma solidity >=0.7.0 <0.9.0;
import "../certora/harness/RolesHarness.sol";
contract PackedKeyTest {
    function testDifferentShortSelectorsRemainRevoked() public {
        RolesHarness r = new RolesHarness(address(this), address(0xdead), address(0xdead));
        r.scopeTarget(10001, address(10001));
        r.scopeRevokeFunction(10001, address(10001), bytes4(0x46ba0000));
        r.scopeRevokeFunction(10001, address(10001), bytes4(0));
        r.scopeAllowFunction(10001, address(10001), bytes4(0x46ba2307), ExecutionOptions.None);
        assert(r.functionScopeConfigForData(10001, address(10001), hex"46ba") == 0);
        assert(r.functionScopeConfigForData(10001, address(10001), hex"") == 0);
        assert(r.functionScopeConfigForData(10001, address(10001), hex"46ba2307") != 0);
    }
}
