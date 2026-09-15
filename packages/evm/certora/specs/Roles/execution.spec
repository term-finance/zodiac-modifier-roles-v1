/*
 * Execution-mechanics properties of callTargetFunctionWithRole: it makes
 * exactly one outbound call, to `to`, as a plain CALL (value 0, calldata
 * length preserved), never a DELEGATECALL to the caller-supplied `to`, and
 * its own return value faithfully reports the callee's outcome without
 * ever reverting on the callee's behalf.
 *
 * These are all consequences of the single raw-assembly line
 * `call(txGas, to, 0, add(data, 0x20), mload(data), 0, 0)` (Roles.sol:371)
 * — nothing else in the function issues a CALL or DELEGATECALL, so CVL
 * opcode hooks (which fire for every such opcode in the whole trace) see
 * exactly this one event and nothing else. That single fact is also what
 * formalizes two properties that would otherwise need their own rules:
 *   - the transaction guard is never invoked (IGuard.checkTransaction /
 *     checkAfterExecution would each need their own CALL opcode; the
 *     function's source never references the `guard` state variable at
 *     all, and exactlyOneOutboundCall independently confirms there is no
 *     room for one), and
 *   - execution is immediate rather than routed through `target` or
 *     `avatar` (exactlyOneOutboundCall already shows the one call that
 *     happens goes to `to` — whatever address the role was actually
 *     scoped to — with no separate call to either).
 * That is the direct-call semantics this function was added to provide,
 * not a defect: see permissions.spec for the authorization strength on
 * that shortened path.
 *
 * Not proved here: byte-for-byte fidelity of the forwarded calldata.
 * Opcode hooks expose only the memory offset and length of the CALL's
 * args, not their content — CVL cannot read EVM memory. argsLengthMatchesData
 * proves the length is preserved; the assembly line forwarding the bytes
 * (`add(data, 0x20)`, i.e. exactly past data's length word, for exactly
 * `mload(data)`, i.e. data.length, bytes) is a single unconditional
 * expression with no branching, so content fidelity is not the kind of
 * property this codebase tends to get subtly wrong the way the permission
 * layer's bit-packing and offset arithmetic are.
 */

using Permissions as permissionsLib;

// These MUST be `persistent`. The raw assembly call at Roles.sol:371 goes
// to an arbitrary, unresolved `to`, which the Prover handles with a
// havocing AUTO summary — and a havoc wipes non-persistent ghosts along
// with storage ("if an unresolved call is handled by a havoc, the ghost
// values will havoc as well"). Without `persistent`, the CALL hook fires
// and increments correctly, then the very summary for that same call
// erases the counter, leaving an arbitrary post-value and failing every
// rule below for a reason that has nothing to do with the contract.
// Persistent ghosts are never havoced and never reverted.
persistent ghost mathint totalCallCount;
persistent ghost mapping(address => mathint) callCountTo;
persistent ghost mathint lastCallValue;
persistent ghost mathint lastCallArgsLength;
persistent ghost mathint lastCallRc;
persistent ghost mathint totalDelegatecallCount;
persistent ghost address lastDelegatecallAddr;

hook CALL(uint g, address addr, uint value, uint argsOffset, uint argsLength, uint retOffset, uint retLength) uint rc {
    totalCallCount = totalCallCount + 1;
    callCountTo[addr] = callCountTo[addr] + 1;
    lastCallValue = value;
    lastCallArgsLength = argsLength;
    lastCallRc = rc;
}

hook DELEGATECALL(uint g, address addr, uint argsOffset, uint argsLength, uint retOffset, uint retLength) uint rc {
    totalDelegatecallCount = totalDelegatecallCount + 1;
    lastDelegatecallAddr = addr;
}

// The core mechanical fact everything else in this file rests on: exactly
// one CALL opcode executes, and it targets `to`. Proven jointly by a total
// count and a per-address count both increasing by exactly 1 — since
// per-address counts can only be non-negative and must sum to the total,
// the one call recorded cannot have gone anywhere but `to`.
rule exactlyOneOutboundCall(address to, bytes data, uint16 role) {
    env e;
    mathint totalBefore = totalCallCount;
    mathint toBefore = callCountTo[to];

    callTargetFunctionWithRole(e, to, data, role);

    assert totalCallCount - totalBefore == 1,
        "callTargetFunctionWithRole did not make exactly one outbound CALL";
    assert callCountTo[to] - toBefore == 1,
        "the one outbound CALL did not go to `to`";
}

rule callValueIsZero(address to, bytes data, uint16 role) {
    env e;
    callTargetFunctionWithRole(e, to, data, role);
    assert lastCallValue == 0,
        "the outbound CALL carried nonzero native value";
}

rule argsLengthMatchesData(address to, bytes data, uint16 role) {
    env e;
    callTargetFunctionWithRole(e, to, data, role);
    assert lastCallArgsLength == data.length,
        "the outbound CALL's calldata length did not match `data.length`";
}

rule returnsCalleeSuccessFlag(address to, bytes data, uint16 role) {
    env e;
    bool success = callTargetFunctionWithRole(e, to, data, role);
    assert success == (lastCallRc != 0),
        "the return value did not faithfully report the callee's success/failure";
}

// Even when the callee reverts (rc == 0), callTargetFunctionWithRole must
// still return normally rather than reverting on the callee's behalf —
// unlike execTransactionWithRole's shouldRevert flag, there is no such
// option here, by design (see plan: intended, caller-beware behavior).
//
// The premise needs the `totalCallCount` guard, not just `lastCallRc == 0`.
// Persistent ghosts are never reset, so on any path where the raw call
// never executes, `lastCallRc` still holds its arbitrary initial value —
// which the prover will happily pick as 0, satisfying "the callee failed"
// on a trace where there was no callee at all. The original version was
// broken exactly that way: msg.value was left free, the non-payable
// callvalue check reverted at function entry before Permissions.check was
// even reached, no CALL fired, and a stale `lastCallRc == 0` made the
// premise true against a revert that had nothing to do with the callee.
// Requiring exactly one CALL to have fired pins the premise to a real
// observation. msg.value is fixed at 0 for the same reason it is in the
// liveness rules: the function is non-payable, so nonzero value reverting
// is correct behavior and not what this rule is about.
rule neverRevertsOnCalleeRevert(address to, bytes data, uint16 role) {
    env e;
    require e.msg.value == 0;

    mathint callsBefore = totalCallCount;

    callTargetFunctionWithRole@withrevert(e, to, data, role);
    bool outerReverted = lastReverted;

    assert (totalCallCount - callsBefore == 1 && lastCallRc == 0) => !outerReverted,
        "callTargetFunctionWithRole reverted because the callee's inner call failed";
}

// A DELEGATECALL to the caller-supplied, untrusted callee would let it
// rewrite Roles' own storage under Roles' own identity — the one way this
// function's execution mechanics could be worse than a plain CALL. It
// never does: the single DELEGATECALL in the trace is the linked
// Permissions.check library call, and the callee gets a plain CALL
// (exactlyOneOutboundCall above).
//
// Counted in total rather than per-address on purpose. An earlier version
// asserted `delegatecallCountTo[to]` did not increase, and the prover
// rightly broke it by choosing `to` = the Permissions library's own
// address: the library delegatecall is then, trivially, "a delegatecall to
// `to`", while the callee still only receives a CALL. Address-aliasing
// like that says nothing about the property, so the count is taken
// globally and pinned to exactly the one library call.
rule onlyDelegatecallsPermissionsLibrary(address to, bytes data, uint16 role) {
    env e;
    mathint before = totalDelegatecallCount;

    callTargetFunctionWithRole(e, to, data, role);

    assert totalDelegatecallCount - before == 1,
        "callTargetFunctionWithRole made a DELEGATECALL other than the single linked Permissions.check";
    assert lastDelegatecallAddr == permissionsLib,
        "the DELEGATECALL did not target the linked Permissions library";
}

// Restricted to `to != currentContract`: a callee that is Roles itself is
// a distinct, owner-configuration-gated scenario (the raw CALL would
// re-enter Roles' own functions with msg.sender == Roles) noted separately
// in the write-up, not folded into "benign callee" here.
rule storageUnchangedUnderBenignCallee(address to, bytes data, uint16 role) {
    env e;
    require to != currentContract;

    storage before = lastStorage;
    callTargetFunctionWithRole(e, to, data, role);
    storage afterCall = lastStorage;

    // Scoped to currentContract deliberately. The unresolved callee is
    // handled by a havocing summary, which scrambles the rest of the scene
    // by construction — a whole-scene comparison would fail on that
    // artifact rather than on anything Roles did. The claim here is about
    // Roles' own storage, which a plain CALL cannot touch.
    assert before[currentContract] == afterCall[currentContract],
        "callTargetFunctionWithRole's own storage changed as a result of calling an external, non-reentrant callee";
}
