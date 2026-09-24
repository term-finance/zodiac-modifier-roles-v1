// SPDX-License-Identifier: LGPL-3.0-only
pragma solidity >=0.7.0 <0.9.0;

import {RolesHarness} from "../harness/RolesHarness.sol";
import {Clearance, ExecutionOptions} from "../../contracts/Permissions.sol";
import {Enum} from "@gnosis.pm/safe-contracts/contracts/common/Enum.sol";

interface BoundaryVm {
    function expectCall(address callee, bytes calldata data) external;
    function record() external;
    function accesses(address account) external returns (bytes32[] memory reads, bytes32[] memory writes);
}

contract BoundaryReceiver {
    fallback() external {}
}

contract BoundaryMutationReplay {
    BoundaryVm private constant vm = BoundaryVm(address(uint160(uint256(keccak256("hevm cheat code")))));

    function prepared() private returns (RolesHarness roles, address receiver, bytes memory data) {
        receiver = address(new BoundaryReceiver());
        roles = new RolesHarness(address(this), address(this), address(this));
        roles.enableModule(address(this));
        uint16[] memory ids = new uint16[](1);
        bool[] memory membership = new bool[](1);
        ids[0] = 7;
        membership[0] = true;
        roles.assignRoles(address(this), ids, membership);
        data = hex"123456780000000000000000";
        roles.scopeTarget(7, receiver);
        roles.scopeRevokeFunction(7, receiver, bytes4(data));
        roles.scopeAllowFunction(7, receiver, bytes4(keccak256("setTxNonce(uint256)")), ExecutionOptions.None);
        assert(receiver != roles.multisend());
        assert(roles.clearanceOf(7, receiver) == Clearance.Function);
        assert(roles.functionScopeConfigForData(7, receiver, data) == 0);
    }

    function rejected(RolesHarness roles, address receiver, bytes memory data) private {
        bool reverted;
        try roles.callTargetFunctionWithRole(receiver, data, 7) returns (bool) {} catch {
            reverted = true;
        }
        assert(reverted);
    }

    function test_observeCallBeforeRollback() public {
        (RolesHarness roles, address receiver, bytes memory data) = prepared();
        vm.expectCall(receiver, data);
        rejected(roles, receiver, data);
    }

    function test_observeWriteBeforeRollback() public {
        (RolesHarness roles, address receiver, bytes memory data) = prepared();
        vm.record();
        rejected(roles, receiver, data);
        (, bytes32[] memory writes) = vm.accesses(address(roles));
        bool found;
        for (uint256 i; i < writes.length; ++i) {
            found = found || writes[i] == bytes32(0);
        }
        assert(found);
    }
}

contract BoundaryWitnessReceiver {
    uint256 public calls;
    fallback() external {
        ++calls;
    }
}

contract BoundaryWitnessAvatar {
    function execTransactionFromModule(address to, uint256 value, bytes calldata data, Enum.Operation operation)
        external returns (bool success)
    {
        assert(operation == Enum.Operation.Call);
        (success,) = to.call{value: value}(data);
    }

    function execTransactionFromModuleReturnData(address to, uint256 value, bytes calldata data, Enum.Operation operation)
        external returns (bool success, bytes memory result)
    {
        assert(operation == Enum.Operation.Call);
        (success, result) = to.call{value: value}(data);
    }
}

contract BoundaryFeasibilityWitnesses {
    function prepared(uint8 dropped) private returns (RolesHarness roles, BoundaryWitnessReceiver receiver, bytes memory data) {
        receiver = new BoundaryWitnessReceiver();
        address avatar = address(new BoundaryWitnessAvatar());
        roles = new RolesHarness(address(this), avatar, avatar);
        roles.enableModule(address(this));
        uint16[] memory ids = new uint16[](1);
        bool[] memory membership = new bool[](1);
        ids[0] = 7;
        membership[0] = true;
        roles.assignRoles(address(this), ids, membership);
        data = hex"123456780000000000000000";
        if (dropped == 1) {
            data = abi.encodeWithSelector(bytes4(keccak256("multiSend(bytes)")), bytes(""));
        }
        roles.scopeTarget(7, address(receiver));
        roles.scopeRevokeFunction(7, address(receiver), bytes4(data));
        if (dropped == 1) {
            roles.setMultisend(address(receiver));
        } else if (dropped == 2) {
            roles.allowTarget(7, address(receiver), ExecutionOptions.None);
        } else if (dropped == 3) {
            roles.scopeAllowFunction(7, address(receiver), bytes4(data), ExecutionOptions.None);
        }
        assert((address(receiver) != roles.multisend()) == (dropped != 1));
        assert((roles.clearanceOf(7, address(receiver)) == Clearance.Function) == (dropped != 2));
        assert((roles.functionScopeConfigForData(7, address(receiver), data) == 0) == (dropped != 3));
    }

    function invoke(uint8 variant, RolesHarness roles, address receiver, bytes memory data) private returns (bool success) {
        bytes memory encoded;
        if (variant == 0) {
            encoded = abi.encodeCall(roles.callTargetFunctionWithRole, (receiver, data, 7));
        } else if (variant == 1) {
            encoded = abi.encodeCall(roles.execTransactionWithRole, (receiver, 0, data, Enum.Operation.Call, 7, true));
        } else {
            encoded = abi.encodeCall(roles.execTransactionWithRoleReturnData, (receiver, 0, data, Enum.Operation.Call, 7, true));
        }
        (success,) = address(roles).call(encoded);
    }

    function test_allPremisesHaveFeasibleRejection() public {
        (RolesHarness roles, BoundaryWitnessReceiver receiver, bytes memory data) = prepared(0);
        for (uint8 variant; variant < 3; ++variant) {
            assert(!invoke(variant, roles, address(receiver), data));
            assert(receiver.calls() == 0);
        }
    }

    function demonstrateNecessity(uint8 dropped) private {
        (RolesHarness roles, BoundaryWitnessReceiver receiver, bytes memory data) = prepared(dropped);
        for (uint8 variant; variant < 3; ++variant) {
            assert(invoke(variant, roles, address(receiver), data));
            assert(receiver.calls() == variant + 1);
        }
    }

    function test_multisendPremiseIsNecessary() public { demonstrateNecessity(1); }
    function test_clearancePremiseIsNecessary() public { demonstrateNecessity(2); }
    function test_deniedGrantPremiseIsNecessary() public { demonstrateNecessity(3); }
}
