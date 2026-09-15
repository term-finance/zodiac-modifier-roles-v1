/*
 * Parameter-scoping enforcement for callTargetFunctionWithRole, restricted
 * to non-multisend targets (see multisend.spec for that branch). This is
 * the most prover-hostile layer in Permissions.check: pluckDynamicValue
 * does a byte-copy loop plus a keccak256 over a symbolic-length buffer. We
 * only verify the Static/OneOf comparisons here, at a fixed, single
 * parameter index, for tractability. That is a real restriction: it does
 * not exercise pluckDynamicValue, and does not exercise a role with more
 * than one scoped parameter. It is still a meaningful check because
 * compare()/compareOneOf() (Permissions.sol:365-390) do not special-case
 * the parameter index — the index only selects which storage slot and
 * which calldata word are read, so a mismatch at index 0 exercises the
 * same comparison logic a mismatch at any other index would.
 */

methods {
    function clearanceOf(uint16, address) external returns (RolesHarness.Clearance) envfree;
    function functionScopeConfigForData(uint16, address, bytes) external returns (uint256) envfree;
    function unpackFunctionOptions(uint256) external returns (RolesHarness.ExecutionOptions, bool, uint256) envfree;
    function unpackParam(uint256, uint256) external returns (bool, RolesHarness.ParameterType, RolesHarness.Comparison) envfree;
    function pluckStaticValueAt(bytes, uint256) external returns (bytes32) envfree;
    function compValueOfForData(uint16, address, bytes, uint8) external returns (bytes32) envfree;
    function compValuesOneOfLengthForData(uint16, address, bytes, uint8) external returns (uint256) envfree;
    function compValuesOneOfAtForData(uint16, address, bytes, uint8, uint256) external returns (bytes32) envfree;
    function multisend() external returns (address) envfree;
}

// A single scoped Static/EqualTo parameter whose calldata value does not
// match the configured compValue must revert. Fixing paramIndex to 0 keeps
// this tractable (see file header for why that does not weaken the claim).
// The non-@withrevert calls to pluckStaticValueAt implicitly restrict this
// rule to calldata long enough that the pluck itself does not revert with
// CalldataOutOfBounds — we are isolating the compare() mismatch revert,
// which shortCalldataReverts and CalldataOutOfBounds paths are not part of.
rule staticParamMismatchReverts(address to, bytes data, uint16 role) {
    env e;
    uint8 paramIndex = 0;

    require to != multisend();
    require clearanceOf(role, to) == RolesHarness.Clearance.Function;

    uint256 scopeConfig = functionScopeConfigForData(role, to, data);
    require scopeConfig != 0;

    // checkTransaction only calls checkParameters when the function is not
    // wildcarded (Permissions.sol:282-285), and checkParameters only visits
    // index i while i < length (Permissions.sol:330). Storage is havoced, so
    // without these the prover picks a scopeConfig that is wildcarded (or has
    // length 0) yet still carries per-parameter bits at index 0 — a config the
    // setters never produce, in which the parameter is legitimately never
    // compared.
    RolesHarness.ExecutionOptions options;
    bool isWildcarded;
    uint256 length;
    options, isWildcarded, length = unpackFunctionOptions(scopeConfig);
    require !isWildcarded;
    require to_mathint(length) > to_mathint(paramIndex);

    bool isScoped;
    RolesHarness.ParameterType paramType;
    RolesHarness.Comparison paramComp;
    isScoped, paramType, paramComp = unpackParam(scopeConfig, paramIndex);
    require isScoped;
    require paramType == RolesHarness.ParameterType.Static;
    require paramComp == RolesHarness.Comparison.EqualTo;

    bytes32 actual = pluckStaticValueAt(data, paramIndex);
    bytes32 expected = compValueOfForData(role, to, data, paramIndex);
    require actual != expected;

    callTargetFunctionWithRole@withrevert(e, to, data, role);

    assert lastReverted,
        "callTargetFunctionWithRole succeeded despite a Static/EqualTo parameter mismatch";
}

// A single scoped OneOf parameter whose calldata value is absent from the
// (length-1) allowlist must revert. Restricted to a length-1 allowlist for
// tractability; compareOneOf's loop (Permissions.sol:386-389) is a plain
// linear scan with no per-index special-casing, so a length-1 miss
// exercises the same revert path a longer miss would.
rule oneOfParamMismatchReverts(address to, bytes data, uint16 role) {
    env e;
    uint8 paramIndex = 0;

    require to != multisend();
    require clearanceOf(role, to) == RolesHarness.Clearance.Function;

    uint256 scopeConfig = functionScopeConfigForData(role, to, data);
    require scopeConfig != 0;

    // checkTransaction only calls checkParameters when the function is not
    // wildcarded (Permissions.sol:282-285), and checkParameters only visits
    // index i while i < length (Permissions.sol:330). Storage is havoced, so
    // without these the prover picks a scopeConfig that is wildcarded (or has
    // length 0) yet still carries per-parameter bits at index 0 — a config the
    // setters never produce, in which the parameter is legitimately never
    // compared.
    RolesHarness.ExecutionOptions options;
    bool isWildcarded;
    uint256 length;
    options, isWildcarded, length = unpackFunctionOptions(scopeConfig);
    require !isWildcarded;
    require to_mathint(length) > to_mathint(paramIndex);

    bool isScoped;
    RolesHarness.ParameterType paramType;
    RolesHarness.Comparison paramComp;
    isScoped, paramType, paramComp = unpackParam(scopeConfig, paramIndex);
    require isScoped;
    require paramType == RolesHarness.ParameterType.Static;
    require paramComp == RolesHarness.Comparison.OneOf;

    require compValuesOneOfLengthForData(role, to, data, paramIndex) == 1;
    bytes32 actual = pluckStaticValueAt(data, paramIndex);
    bytes32 allowed = compValuesOneOfAtForData(role, to, data, paramIndex, 0);
    require actual != allowed;

    callTargetFunctionWithRole@withrevert(e, to, data, role);

    assert lastReverted,
        "callTargetFunctionWithRole succeeded despite a OneOf parameter value absent from its allowlist";
}
