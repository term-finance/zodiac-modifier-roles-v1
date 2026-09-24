using DummyAvatar as closureScene0;
using Permissions as closureScene1;
using RolesHarness as closureScene2;

persistent ghost bool dependencyEscaped;

// Dynamic selectors need a separate trap; typed unknown receivers are
// also observed by the opcode hooks. Call-resolution reports remain required.
methods {
    unresolved external in _._ => DISPATCH [] default ASSERT_FALSE;
}

hook CALL(uint g, address addr, uint value, uint argsOffset, uint argsLength, uint retOffset, uint retLength) uint rc {
    dependencyEscaped = dependencyEscaped || !(addr == closureScene0 || addr == closureScene1 || addr == closureScene2);
}

hook STATICCALL(uint g, address addr, uint argsOffset, uint argsLength, uint retOffset, uint retLength) uint rc {
    dependencyEscaped = dependencyEscaped || !(addr == closureScene0 || addr == closureScene1 || addr == closureScene2);
}

hook DELEGATECALL(uint g, address addr, uint argsOffset, uint argsLength, uint retOffset, uint retLength) uint rc {
    dependencyEscaped = dependencyEscaped || !(addr == closureScene0 || addr == closureScene1 || addr == closureScene2);
}

hook CALLCODE(uint g, address addr, uint value, uint argsOffset, uint argsLength, uint retOffset, uint retLength) uint rc {
    dependencyEscaped = dependencyEscaped || true;
}

hook CREATE1(uint value, uint offset, uint length) address result {
    dependencyEscaped = true;
}

hook CREATE2(uint value, uint offset, uint length, bytes32 salt) address result {
    dependencyEscaped = true;
}

hook SELFDESTRUCT(address addr) {
    dependencyEscaped = true;
}

// Persistent state retains observations on paths that subsequently revert.
// No functional-spec imports, preconditions, or method filters apply here.
rule dependencyClosureBoundary(method f) {
    env e;
    calldataarg args;
    dependencyEscaped = false;
    f@withrevert(e, args);
    assert !dependencyEscaped, "Call, creation or destruction escaped the declared scene";
}

rule dependencyClosureReachable(method f) {
    env e;
    calldataarg args;
    f@withrevert(e, args);
    satisfy !lastReverted;
}
