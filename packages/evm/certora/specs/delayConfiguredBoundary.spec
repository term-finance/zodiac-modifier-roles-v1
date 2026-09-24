// The required configuration is a separate transition obligation. Persistent
// observations retain attempted effects even when the forwarding call reverts.
using Permissions as permissionsLibrary;
persistent ghost bool attemptedEffect;
methods {
    unresolved external in _._ => DISPATCH [] default HAVOC_ALL;
    function _.checkTransaction(address,uint256,bytes,Enum.Operation,uint256,uint256,uint256,address,address,bytes,address) external => HAVOC_ALL UNRESOLVED;
    function _.checkAfterExecution(bytes32,bool) external => HAVOC_ALL UNRESOLVED;
    function _.execTransactionFromModule(address,uint256,bytes,Enum.Operation) external => HAVOC_ALL UNRESOLVED;
    function _.execTransactionFromModuleReturnData(address,uint256,bytes,Enum.Operation) external => HAVOC_ALL UNRESOLVED;
    function multisend() external returns (address) envfree;
    function clearanceOf(uint16,address) external returns (RolesHarness.Clearance) envfree;
    function functionScopeConfigForData(uint16,address,bytes) external returns (uint256) envfree;
}
hook CALL(uint g, address a, uint v, uint ao, uint al, uint ro, uint rl) uint rc { attemptedEffect = true; }
hook STATICCALL(uint g, address a, uint ao, uint al, uint ro, uint rl) uint rc { attemptedEffect = true; }
hook DELEGATECALL(uint g, address a, uint ao, uint al, uint ro, uint rl) uint rc {
    attemptedEffect = attemptedEffect || a != permissionsLibrary;
}
hook CALLCODE(uint g, address a, uint v, uint ao, uint al, uint ro, uint rl) uint rc { attemptedEffect = true; }
hook CREATE1(uint v, uint o, uint l) address a { attemptedEffect = true; }
hook CREATE2(uint v, uint o, uint l, bytes32 s) address a { attemptedEffect = true; }
hook SELFDESTRUCT(address a) { attemptedEffect = true; }
hook ALL_SSTORE(uint slot, uint value) { attemptedEffect = true; }
hook ALL_TSTORE(uint slot, uint value) { attemptedEffect = true; }

rule directConfiguredRejection(address to, bytes data, uint16 role, uint256 value, Enum.Operation operation, bool shouldRevert) {
    require to != multisend(), "The approved policy excludes the multisend parser target";
    require clearanceOf(role, to) == RolesHarness.Clearance.Function, "Separate configuration transition obligation";
    require functionScopeConfigForData(role, to, data) == 0, "Separate configuration transition obligation for the denied selector";
    attemptedEffect = false;
    env caller;
    callTargetFunctionWithRole@withrevert(caller, to, data, role);
    assert lastReverted, "denied selector must revert";
    assert !attemptedEffect, "rejection must precede boundary calls, creation, destruction and storage writes";
}

rule safeConfiguredRejection(address to, bytes data, uint16 role, uint256 value, Enum.Operation operation, bool shouldRevert) {
    require to != multisend(), "The approved policy excludes the multisend parser target";
    require clearanceOf(role, to) == RolesHarness.Clearance.Function, "Separate configuration transition obligation";
    require functionScopeConfigForData(role, to, data) == 0, "Separate configuration transition obligation for the denied selector";
    attemptedEffect = false;
    env caller;
    execTransactionWithRole@withrevert(caller, to, value, data, operation, role, shouldRevert);
    assert lastReverted, "denied selector must revert";
    assert !attemptedEffect, "rejection must precede boundary calls, creation, destruction and storage writes";
}

rule returnDataConfiguredRejection(address to, bytes data, uint16 role, uint256 value, Enum.Operation operation, bool shouldRevert) {
    require to != multisend(), "The approved policy excludes the multisend parser target";
    require clearanceOf(role, to) == RolesHarness.Clearance.Function, "Separate configuration transition obligation";
    require functionScopeConfigForData(role, to, data) == 0, "Separate configuration transition obligation for the denied selector";
    attemptedEffect = false;
    env caller;
    execTransactionWithRoleReturnData@withrevert(caller, to, value, data, operation, role, shouldRevert);
    assert lastReverted, "denied selector must revert";
    assert !attemptedEffect, "rejection must precede boundary calls, creation, destruction and storage writes";
}
