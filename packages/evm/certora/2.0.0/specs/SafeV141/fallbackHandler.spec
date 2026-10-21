/*
 * Safe v1.4.1: once fallback calls its handler, every call the handler makes
 * comes from the handler, never from the Safe.
 *
 * The handler slot points at ForwardingFallbackHandler, which makes one call
 * onward to CallerProbe, and the probe records its msg.sender. fallback's
 * call to the handler is routed to ForwardingFallbackHandler, as on chain
 * when the slot holds its address.
 */

using ForwardingFallbackHandler as handler;
using CallerProbe as probe;

methods {
    function fallbackHandlerIs(address) external returns (bool) envfree;
    function probe.lastCaller() external returns (address) envfree;
    function probe.hits() external returns (uint256) envfree;

    // Every selector reaches the handler: its functions by name, anything
    // else its fallback(). A call that somehow is not dispatched fails the
    // rule instead of being havoced.
    unresolved external in SafeV141Harness._ => DISPATCH(use_fallback=true) [
        ForwardingFallbackHandler._
    ] default ASSERT_FALSE;
}

rule fallbackHandlerCallsComeFromTheHandler(method f, calldataarg args)
    filtered { f -> f.isFallback }
{
    env e;
    // The handler is not the Safe itself.
    require handler != currentContract;
    require fallbackHandlerIs(handler);
    require probe.hits() == 0;

    f@withrevert(e, args);
    // A revert rolls the probe back, so hits > 0 means the handler's onward
    // call happened and stood.
    bool handlerCalledOnward = probe.hits() > 0;

    assert handlerCalledOnward => probe.lastCaller() == handler,
        "a call made by the fallback handler did not come from the handler";
    assert handlerCalledOnward => probe.lastCaller() != currentContract,
        "a call made by the fallback handler came from the Safe";
}

/*
 * The rule above is not vacuous: a call to fallback() can succeed with the
 * handler making its onward call.
 */
rule fallbackReachesTheHandler(method f, calldataarg args)
    filtered { f -> f.isFallback }
{
    env e;
    require handler != currentContract;
    require fallbackHandlerIs(handler);
    require probe.hits() == 0;

    f@withrevert(e, args);
    bool succeeded = !lastReverted;

    satisfy succeeded && probe.hits() == 1,
        "no call to fallback reached the handler";
}
