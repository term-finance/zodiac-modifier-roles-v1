/*
 * The multisend branch of Permissions.check (to == multisend()). Role
 * membership is always enforced first (Permissions.sol:185-187, before the
 * branch) — see access.spec's nonMemberAlwaysReverts, which already covers
 * this branch too. What is specific to this branch is characterized below.
 */

methods {
    function moduleEntry(address) external returns (address) envfree;
    function memberOf(uint16, address) external returns (bool) envfree;
    function clearanceOf(uint16, address) external returns (RolesHarness.Clearance) envfree;
    function pluckStaticValueAt(bytes, uint256) external returns (bytes32) envfree;
    function functionScopeConfigForData(uint16, address, bytes) external returns (uint256) envfree;
    function multisendEntryAt(bytes, uint256) external returns (Enum.Operation, address, uint256, uint256, bytes) envfree;
    function multisend() external returns (address) envfree;
}

// checkMultisendTransaction's loop (Permissions.sol:220-237) starts at
// i = 100 and only runs while i < data.length, so a blob of at most 100
// bytes never enters the loop body at all: check() returns having verified
// role membership only, no target/function/parameter scoping. The raw CALL
// still fires. This is a genuine characterization, not a bug: reusing
// pluckStaticValueAt(data, 0) here is exact, not approximate — it computes
// `mload(add(32, add(data, 4)))` = `mload(add(data, 36))`, the identical
// expression checkMultisendTransaction uses to read its offset word
// (Permissions.sol:209-211).
//
// This rule leaves `clearanceOf(role, multisend())` completely
// unconstrained and still proves success — by the same argument used in
// permissions.spec for ExecutionOptions, that is the proof that ordinary
// target clearance on the multisend address plays no role in this branch.
// It also does not fix `multisend()` to any particular address, so it
// covers both a configured multisend and the address(0) default before
// setMultisend is ever called.
rule multisendShortBlobPerformsNoScoping(bytes data, uint16 role) {
    env e;
    address to = multisend();

    require moduleEntry(e.msg.sender) != 0;
    require memberOf(role, e.msg.sender);
    require e.msg.value == 0;
    require data.length >= 36 && data.length <= 100;
    require pluckStaticValueAt(data, 0) == to_bytes32(32);

    callTargetFunctionWithRole@withrevert(e, to, data, role);

    assert !lastReverted,
        "an authorized member could not reach the outbound call on a short multisend blob";
}

// The property everySubTxIsChecked does NOT establish: that a scanned
// entry's own target/function scoping was actually enforced. checkTransaction
// (Permissions.sol:236) is called with each parsed sub-tx's own (to, value,
// data, operation) — success of the overall multisend call therefore
// requires each visited entry to independently satisfy the same clearance
// and function-allowlist rules as successImpliesTargetCleared /
// successImpliesFunctionAllowed prove for the top-level (to != multisend())
// case in permissions.spec. Those rules explicitly exclude the multisend
// branch, so they say nothing about entries inside a batch on their own —
// these two rules close that gap for the first and second entries,
// matching this conf's loop_iter of 2. checkTransaction has no try/catch
// anywhere in its call chain, so a revert on any visited entry aborts the
// whole call; proving the first two entries here is not a completeness
// argument by itself, but every entry the prover explores within loop_iter
// is governed by the identical checkTransaction call, so a violation at
// any explored depth would be caught the same way. Beyond loop_iter, this
// is bounded model checking, not an unbounded proof — the same limitation
// noted for everySubTxIsChecked below.
rule multisendFirstSubTxIsScoped(bytes data, uint16 role) {
    env e;
    address to = multisend();

    require moduleEntry(e.msg.sender) != 0;
    require memberOf(role, e.msg.sender);
    require e.msg.value == 0;
    require data.length > 100;

    Enum.Operation subOp;
    address subTo;
    uint256 subValue;
    uint256 subDataLength;
    bytes subData;
    subOp, subTo, subValue, subDataLength, subData = multisendEntryAt(data, 100);
    require subData.length >= 4;

    callTargetFunctionWithRole(e, to, data, role);

    assert clearanceOf(role, subTo) != RolesHarness.Clearance.None,
        "a multisend call succeeded despite its first sub-transaction targeting a non-cleared address";
    assert clearanceOf(role, subTo) == RolesHarness.Clearance.Function
        => functionScopeConfigForData(role, subTo, subData) != 0,
        "a multisend call succeeded despite its first sub-transaction's function not being allowlisted";
}

// Same property for the second entry, whose position is chained off the
// first entry's own parsed dataLength (Permissions.sol:220's loop
// increment: i += 85 + dataLength) — i.e. this is exactly where the real
// loop's second iteration would read from.
rule multisendSecondSubTxIsScoped(bytes data, uint16 role) {
    env e;
    address to = multisend();

    require moduleEntry(e.msg.sender) != 0;
    require memberOf(role, e.msg.sender);
    require e.msg.value == 0;

    Enum.Operation op1;
    address to1;
    uint256 value1;
    uint256 dataLength1;
    bytes data1;
    op1, to1, value1, dataLength1, data1 = multisendEntryAt(data, 100);

    mathint secondEntryOffset = 100 + 85 + dataLength1;
    require data.length > secondEntryOffset;

    Enum.Operation subOp;
    address subTo;
    uint256 subValue;
    uint256 subDataLength;
    bytes subData;
    subOp, subTo, subValue, subDataLength, subData = multisendEntryAt(data, assert_uint256(secondEntryOffset));
    require subData.length >= 4;

    callTargetFunctionWithRole(e, to, data, role);

    assert clearanceOf(role, subTo) != RolesHarness.Clearance.None,
        "a multisend call succeeded despite its second sub-transaction targeting a non-cleared address";
    assert clearanceOf(role, subTo) == RolesHarness.Clearance.Function
        => functionScopeConfigForData(role, subTo, subData) != 0,
        "a multisend call succeeded despite its second sub-transaction's function not being allowlisted";
}

// Pure arithmetic lemma, independent of any contract call: the scan's
// starting offset (100) and the fixed minimum sub-transaction footprint
// (85 bytes: 1 operation + 20 to + 32 value + 32 dataLength) together
// guarantee the loop can never skip a byte range that still contains a
// complete entry.
//
// s is a candidate entry's payload-relative start (i.e. i - 32, since the
// raw loop variable i is offset by the 32-byte memory length-prefix baked
// into `bytes memory` — see the header comment in checkMultisendTransaction,
// Permissions.sol:216-219). "Skipped by the scan" means the loop guard
// i < data.length is false at s, i.e. s + 32 >= L. "A complete entry
// exists at s" means the fixed 85-byte header fits before the end of the
// blob, i.e. s + 85 <= L. The lemma: these cannot both hold, because
// L - 32 <= s would require L - 85 >= s only if 85 <= 32, which is false.
// The ~32-byte margin the scan can miss is strictly smaller than the
// ~85-byte minimum entry size, so anything in the missed margin was never
// a complete entry to begin with, and could not have been executed by a
// real MultiSend contract either.
rule everySubTxIsChecked(mathint L, mathint s) {
    require s + 32 >= L;

    assert s + 85 > L,
        "the multisend scan can skip a byte range that still contains a complete sub-transaction entry";
}
