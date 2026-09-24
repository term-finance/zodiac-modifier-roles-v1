// SPDX-License-Identifier: MIT
pragma solidity >=0.7.0 <0.9.0;
import {Permissions} from "../contracts/Permissions.sol";
contract PackedKeyLemma {
    function check_packedKeyInjective(address a, address b, bytes4 x, bytes4 y) public pure {
        bytes32 first = Permissions.keyForFunctions(a, x);
        bytes32 second = Permissions.keyForFunctions(b, y);
        assert((first == second) == (a == b && x == y));
    }
}
