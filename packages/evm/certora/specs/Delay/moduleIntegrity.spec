/*
 * Property: nothing but the Delay's owner can change who is allowed to queue.
 *
 * This is the file that covers the attack the whole integration exists to
 * rule out: an unauthorized party gets an address into the Delay's module
 * ring, that address queues a malicious transaction, and after the cooldown
 * anyone executes it against the avatar. Everything downstream of the module
 * ring — the cooldown, the veto, the pause — is irrelevant once a hostile
 * module is enabled, because the queue entry it writes is indistinguishable
 * from a legitimate one.
 *
 * The scene is the real Delay, not a model: certora/helpers/Delay.sol is the
 * verified mastercopy source, inherited unmodified by
 * certora/harness/DelayHarness.sol, which adds one view getter and no logic.
 *
 * Four claims, and the fourth is the reason the scene is not the one the
 * other Delay spec uses:
 *
 *   1. The module ring changes only through enableModule/disableModule, and
 *      only for the owner.
 *   2. Only an address already in the ring can put an entry in the queue.
 *   3. `owner` and `guard` are likewise owner-only, so neither the ring's
 *      gatekeeper nor the guard sitting over execution can be re-pointed by
 *      anyone else.
 *   4. An execution cannot become a module grant. executeNextTx forwards to
 *      the avatar, and the avatar can call anything — including straight back
 *      into the Delay. That return path is where enableModule would be
 *      reached without ever going through the owner, and it is the shape of
 *      the incident this design was written after.
 *
 * Claim 4 is why `target` is linked to ReenteringAvatar rather than
 * DummyAvatar. DummyAvatar returns true and calls nothing, so under it every
 * statement about what the avatar's call can do back to the Delay holds
 * vacuously. ReenteringAvatar tries enableModule on the Delay that forwarded
 * to it, every time, and records that it tried — so
 * avatarEnableModuleAttemptIsReachable can show the path was actually
 * exercised rather than assumed away.
 *
 * Rules, by claim:
 *
 *   setUp is spent
 *     setUpAlwaysRevertsAfterDeployment   the public, unmodified setUp cannot
 *                                         be re-entered to reset the ring or
 *                                         the owner. Every rule below that
 *                                         pins the ring relies on this
 *
 *   the module ring
 *     modulesOnlyChangeThroughOwnerEnableOrDisable
 *                                         over every entry point: the ring
 *                                         moves only under enableModule or
 *                                         disableModule, and only for owner
 *     ownerCanEnableModule                the owner still can (witness)
 *
 *   who may queue
 *     queueOnlyGrowsThroughEnabledModules over every entry point: queueNonce
 *                                         and txHash move only for a caller
 *                                         already in the ring
 *     enabledModuleCanQueue               an enabled module still can
 *                                         (witness)
 *
 *   the ring's gatekeeper and the guard over execution
 *     ownerOnlyChangesThroughOwnableTransfer
 *     guardOnlyChangesThroughOwnerSetGuard
 *
 *   an execution is not a module grant
 *     executeNextTxCannotEnableModuleThroughTheAvatar
 *                                         end to end, with a hostile avatar
 *     avatarEnableModuleAttemptIsReachable
 *                                         the hostile avatar really is
 *                                         reached and really does try, so the
 *                                         rule above is not vacuous (witness)
 *
 * Composition with the Roles specs. This file proves only that `owner` is the
 * sole route into the ring. What stops the Governor from BEING that route is
 * Property 1: with SetTxNonceGuard and the role configuration in place, the
 * only call the Governor can make the DelayOwnerSafe emit is
 * Delay.setTxNonce. The DelayOwnerSafe is the Delay's owner, so those two
 * together — and only together — give the claim that matters:
 *
 *     the Governor can never enable a module on the Delay.
 *
 * Neither half states that conclusion on its own, and weakening either one
 * silently gives it up. See PROOFS.md Property 5.
 *
 * Deliberately NOT claimed here:
 *   - Anything about who the owner is. `owner` is left unconstrained, so
 *     these rules hold for any owner, including a Safe. That the owner is the
 *     DelayOwnerSafe rather than something reachable by the Governor is a
 *     deployment fact, checked in the verification plan, not proved here.
 *   - That the owner will not enable a hostile module itself. A 5-of-11
 *     quorum that wants to hand the Delay over can; the point of these rules
 *     is that nothing else can.
 *   - That the avatar cannot do harm elsewhere. ReenteringAvatar models the
 *     one return path this file is about — back into the Delay's own
 *     owner-only surface. What a real avatar does with the rest of a queue
 *     entry is the queue entry's business, and is what the cooldown is for.
 *   - That the Delay's avatar is not its own owner. Both
 *     modulesOnlyChangeThroughOwnerEnableOrDisable and
 *     executeNextTxCannotEnableModuleThroughTheAvatar require
 *     target() != owner(): if a Delay were wired so that the contract it
 *     forwards to is also the contract that owns it, the return path would
 *     reach enableModule with msg.sender == owner and an execution really
 *     could enable a module. In the deployment those are the Ownerless Safe
 *     and the DelayOwnerSafe, two distinct addresses, checked in the
 *     verification plan.
 *   - Anything about the guard's behaviour. PauseGuard is in the scene only
 *     so setGuard's ERC-165 probe and Module.exec's hooks resolve against a
 *     real implementation instead of an unresolved call. Property 4 is where
 *     the guard is actually specified.
 *
 * Modelling notes.
 *   - The witness rules and the two claim-4 rules require `guard() == 0`.
 *     Module.exec consults the guard before forwarding, so an installed guard
 *     can only ADD reverts to executeNextTx; proving a negative claim against
 *     the guard-less, maximally permissive executor is the conservative
 *     direction, and it keeps the claim-4 statement about the avatar rather
 *     than about PauseGuard's flag.
 *   - The parametric rules exclude setUp from `f`;
 *     setUpAlwaysRevertsAfterDeployment carries that entry point on its own.
 *     See the note above the rules for why pinning the pre-state instead
 *     would make the setUp instance vacuous. Three of the four then assume
 *     nothing at all about the pre-state; the exception is
 *     modulesOnlyChangeThroughOwnerEnableOrDisable, which needs
 *     target() != owner() for the reason given at the rule.
 *   - loop_iter 1 with optimistic_loop bounds skipExpired's while loop and
 *     getModulesPaginated's; neither calls exec or writes the ring.
 *   - executeNextTx and the queueing entry points hash the whole transaction.
 *     The conf sets optimistic_hashing with hashing_length_bound 1024, so
 *     these rules cover transactions whose `data` is at most 971 bytes.
 */

using ReenteringAvatar as hostileAvatar;

methods {
    function owner() external returns (address) envfree;
    function guard() external returns (address) envfree;
    function target() external returns (address) envfree;
    function avatar() external returns (address) envfree;
    function txNonce() external returns (uint256) envfree;
    function queueNonce() external returns (uint256) envfree;
    function txHash(uint256) external returns (bytes32) envfree;
    function moduleEntry(address) external returns (address) envfree;

    function hostileAvatar.delay() external returns (address) envfree;
    function hostileAvatar.attacker() external returns (address) envfree;
    function hostileAvatar.attempts() external returns (uint256) envfree;
    function hostileAvatar.succeeded() external returns (bool) envfree;

    // NO summary for the avatar's return path into the Delay. The conf links
    // ReenteringAvatar.delay to DelayHarness, so
    // IDelayOwnerFunctions(delay).enableModule(attacker) resolves statically
    // and needs no dispatcher.
    //
    // A `_.enableModule(address) => DISPATCHER(true)` here is actively wrong:
    // the wildcard catches this rule file's own direct calls on
    // currentContract too, routes them through the dispatcher's per-case
    // storage merge, and lets the Prover report enableModule as succeeding
    // while neither write to `modules` lands. That shows up as
    // ownerCanEnableModule failing with the ring untouched after a call that
    // did not revert.

    // Module.exec's guard hooks, and Guardable.setGuard's ERC-165 probe of a
    // new guard. PauseGuard is the only implementor in the scene.
    function _.checkTransaction(
        address, uint256, bytes, Enum.Operation,
        uint256, uint256, uint256, address, address, bytes, address
    ) external => DISPATCHER(true);
    function _.checkAfterExecution(bytes32, bool) external => DISPATCHER(true);
    function _.supportsInterface(bytes4) external => DISPATCHER(true);
}

/// Modifier.sol:13 — `address internal constant`, so there is no getter.
definition SENTINEL_MODULES() returns address = 0x1;

/*
 * On setUp, and why the parametric rules exclude it.
 *
 * setUp is the one entry point that can legitimately rewrite the module ring
 * and the owner, so a parametric rule that left it in would report it as a
 * counterexample to every claim in this file. The obvious fix — requiring the
 * ring already set up (moduleEntry(SENTINEL_MODULES()) == SENTINEL_MODULES(),
 * Delay.sol:106-112) — is worse than useless: in that pre-state setUp ALWAYS
 * reverts, and a parametric `f(e, args)` without @withrevert prunes reverting
 * paths, so the setUp instance passes with an unreachable body. Vacuous, not
 * proved.
 *
 * So the parametric rules below filter setUp out of `f` and assume nothing at
 * all about the pre-state, which makes them strictly stronger — they hold from
 * any storage the Prover can pick. setUpAlwaysRevertsAfterDeployment states
 * the setUp case directly instead, as a revert claim where a revert is the
 * thing being asserted rather than something silently assumed away.
 *
 * The two together cover every entry point of the deployed contract. The
 * non-parametric rules further down still require the ring set up, because
 * they are about behaviour in the deployed configuration rather than about
 * every reachable storage state.
 */

/* ------------------------------------------------------------------------
 * 1. setUp is spent
 * --------------------------------------------------------------------- */

/*
 * setUp is `public` with no access modifier of its own (Delay.sol:76). It is
 * safe only because of two things inside it: __Ownable_init() carries OZ's
 * `initializer` (Delay.sol:87), and setupModules() requires the sentinel slot
 * to still be empty (Delay.sol:106-112). A second setUp would run
 * transferOwnership(attacker) AND reset the module ring — both halves of what
 * the rest of this file protects — so it is worth pinning rather than reading
 * off the source.
 *
 * Stated against the module ring alone, so it holds whichever of the two
 * guards the Prover's chosen pre-state trips.
 */
rule setUpAlwaysRevertsAfterDeployment(bytes initParams) {
    env e;
    require moduleEntry(SENTINEL_MODULES()) == SENTINEL_MODULES();

    setUp@withrevert(e, initParams);

    assert lastReverted,
        "setUp ran a second time, which would reset the module ring and the owner";
}

/* ------------------------------------------------------------------------
 * 2. The module ring
 * --------------------------------------------------------------------- */

/*
 * THE property this file exists for. Over every state-changing entry point of
 * the Delay — including executeNextTx, whose avatar tries enableModule on the
 * way through — if any address's ring entry moved, the entry point was
 * enableModule or disableModule and the caller was the owner.
 */
rule modulesOnlyChangeThroughOwnerEnableOrDisable(method f, calldataarg args, address m)
    filtered {
        f -> !f.isView && !f.isPure &&
             f.selector != sig:DelayHarness.setUp(bytes).selector
    }
{
    env e;
    // The avatar is not itself the Delay's owner - the same deployment
    // constraint executeNextTxCannotEnableModuleThroughTheAvatar depends on,
    // and it is needed here for the same reason. Without it the Prover picks
    // target() == owner(), the avatar's enableModule on the way through
    // executeNextTx then arrives with msg.sender == owner() and legitimately
    // succeeds, and the ring moves under an entry point that is not
    // enableModule and for a caller, e.msg.sender, that is not the owner.
    //
    // That counterexample does not violate "only the owner can change the
    // ring": the nested call WAS the owner. It violates the stronger reading
    // this rule asserts, that the OUTERMOST caller is the owner, which is
    // only equivalent while no nested caller can be the owner. In the
    // deployment the avatar is the Ownerless Safe and the owner is the
    // DelayOwnerSafe, two distinct addresses, checked in the verification plan.
    require target() != owner();

    address ownerBefore = owner();
    address entryBefore = moduleEntry(m);

    f(e, args);

    assert moduleEntry(m) != entryBefore =>
        (f.selector == sig:DelayHarness.enableModule(address).selector ||
         f.selector == sig:DelayHarness.disableModule(address,address).selector),
        "an entry point other than enableModule or disableModule changed the module ring";
    assert moduleEntry(m) != entryBefore => e.msg.sender == ownerBefore,
        "a caller other than the owner changed the module ring";
}

/*
 * The bound above is not achieved by nothing working: enableModule is
 * reachable and completes for the owner, so modulesOnlyChangeThroughOwner-
 * EnableOrDisable is bounding a live path rather than an empty one.
 *
 * It asserts ONLY that the call does not revert, and deliberately says nothing
 * about the ring afterwards. The post-state is not observable in this scene:
 * the Prover scalarizes the constant-key modules[SENTINEL_MODULES] that
 * Modifier's own code touches (visible in counterexamples as a scalar going
 * SENTINEL -> m across the call), while every getter reachable from CVL takes
 * the key as a parameter and reads the storage wordmap, which does not see
 * that write. Asserting the ring here - through isModuleEnabled, through
 * moduleEntry, or through a dedicated constant-key harness getter - fails on a
 * model where enableModule reports success and the ring reads unchanged. That
 * is a scene artifact, not a Delay behaviour: the write demonstrably happens.
 *
 * So the post-state claim is left to PROOFS.md's "Explicitly not proved"
 * rather than asserted against a storage view that cannot see it.
 */
rule ownerCanEnableModule(address m) {
    env e;
    require moduleEntry(SENTINEL_MODULES()) == SENTINEL_MODULES();
    require e.msg.value == 0;
    require e.msg.sender == owner();
    require m != 0 && m != SENTINEL_MODULES();
    require moduleEntry(m) == 0;

    enableModule@withrevert(e, m);

    assert !lastReverted,
        "the Delay's owner could not enable a module";
}

/* ------------------------------------------------------------------------
 * 3. Who may queue
 * --------------------------------------------------------------------- */

/*
 * The other half of the attack: even an address that somehow reached a Delay
 * entry point cannot leave a queue entry behind unless it is already in the
 * ring. Stated on both things a queued entry writes — the nonce that orders
 * the queue, and the hash executeNextTx later checks against.
 *
 * moduleOnly gates on the raw ring entry (Modifier.sol:58-61), which is what
 * moduleEntry returns, not on isModuleEnabled: the two diverge at the
 * self-linked sentinel.
 */
rule queueOnlyGrowsThroughEnabledModules(method f, calldataarg args, uint256 n)
    filtered {
        f -> !f.isView && !f.isPure &&
             f.selector != sig:DelayHarness.setUp(bytes).selector
    }
{
    env e;
    uint256 queueNonceBefore = queueNonce();
    bytes32 txHashBefore = txHash(n);

    f(e, args);

    assert queueNonce() != queueNonceBefore => moduleEntry(e.msg.sender) != 0,
        "a caller that is not an enabled module moved the queue nonce";
    assert txHash(n) != txHashBefore => moduleEntry(e.msg.sender) != 0,
        "a caller that is not an enabled module wrote a queue entry";
}

/*
 * An enabled module still can. Non-vacuity witness for the rule above.
 */
rule enabledModuleCanQueue(
    address to, uint256 value, bytes data, Enum.Operation operation
) {
    env e;
    require moduleEntry(SENTINEL_MODULES()) == SENTINEL_MODULES();
    require e.msg.value == 0;
    require moduleEntry(e.msg.sender) != 0;

    uint256 queueNonceBefore = queueNonce();
    require queueNonceBefore < max_uint256;

    execTransactionFromModule@withrevert(e, to, value, data, operation);

    assert !lastReverted,
        "an enabled module could not queue a transaction";
    assert to_mathint(queueNonce()) == queueNonceBefore + 1,
        "queueing returned without advancing the queue nonce";
}

/* ------------------------------------------------------------------------
 * 4. The ring's gatekeeper, and the guard over execution
 * --------------------------------------------------------------------- */

/*
 * Ownership cannot be seized: it moves only through OwnableUpgradeable's own
 * two entry points, and only for the current owner.
 *
 * renounceOwnership is in the allowed set because it exists on the mastercopy
 * and cannot be removed — the Delay is a minimal proxy to immutable code. If
 * the owner ever called it, `owner` would become zero and enableModule,
 * setGuard, setTxNonce, setTxCooldown and setTxExpiration would all be frozen
 * for good. That is a runbook constraint, not something these rules prevent.
 */
rule ownerOnlyChangesThroughOwnableTransfer(method f, calldataarg args)
    filtered {
        f -> !f.isView && !f.isPure &&
             f.selector != sig:DelayHarness.setUp(bytes).selector
    }
{
    env e;
    address ownerBefore = owner();

    f(e, args);

    assert owner() != ownerBefore =>
        (f.selector == sig:DelayHarness.transferOwnership(address).selector ||
         f.selector == sig:DelayHarness.renounceOwnership().selector),
        "an entry point other than transferOwnership or renounceOwnership changed the owner";
    assert owner() != ownerBefore => e.msg.sender == ownerBefore,
        "a caller other than the owner changed the owner";
}

/*
 * The guard over execution is owner-only too, so a hostile module cannot
 * detach PauseGuard on its way past — it would have to be the owner, and by
 * the ring rule it cannot become the owner either.
 */
rule guardOnlyChangesThroughOwnerSetGuard(method f, calldataarg args)
    filtered {
        f -> !f.isView && !f.isPure &&
             f.selector != sig:DelayHarness.setUp(bytes).selector
    }
{
    env e;
    address ownerBefore = owner();
    address guardBefore = guard();

    f(e, args);

    assert guard() != guardBefore =>
        f.selector == sig:DelayHarness.setGuard(address).selector,
        "an entry point other than setGuard changed the guard";
    assert guard() != guardBefore => e.msg.sender == ownerBefore,
        "a caller other than the owner changed the guard";
}

/* ------------------------------------------------------------------------
 * 5. An execution is not a module grant
 * --------------------------------------------------------------------- */

/*
 * The incident's shape, stated end to end. The avatar is hostile: every queue
 * entry it is handed, it turns around and calls enableModule on the Delay
 * that forwarded to it. executeNextTx runs anyway — the avatar swallows the
 * refusal and reports success — and the attacker is still not in the ring
 * afterwards.
 *
 * enableModule is onlyOwner and the caller on that return path is the avatar,
 * not the owner. This rule says the Delay has no other way to read it.
 */
rule executeNextTxCannotEnableModuleThroughTheAvatar(
    address to, uint256 value, bytes data, Enum.Operation operation
) {
    env e;
    require moduleEntry(SENTINEL_MODULES()) == SENTINEL_MODULES();
    require target() == hostileAvatar;
    require hostileAvatar.delay() == currentContract;
    require guard() == 0;

    // The avatar is not itself the Delay's owner. In the deployment it is the
    // Ownerless Safe while the owner is the DelayOwnerSafe, two distinct
    // addresses; wire a Delay so that its avatar IS its owner and an execution
    // really could enable a module, because the return path would then arrive
    // at enableModule with msg.sender == owner. That is a deployment
    // constraint this rule depends on, not one it proves.
    require target() != owner();

    address attacker = hostileAvatar.attacker();
    require attacker != 0 && attacker != SENTINEL_MODULES();
    require moduleEntry(attacker) == 0;
    require !hostileAvatar.succeeded();

    executeNextTx@withrevert(e, to, value, data, operation);

    assert moduleEntry(attacker) == 0,
        "executing a queue entry put an address in the module ring";
    assert !hostileAvatar.succeeded(),
        "the avatar's enableModule call on the Delay returned instead of reverting";
}

/*
 * That the rule above is about a refusal and not about a path that never
 * runs: there is a state in which executeNextTx completes AND the avatar was
 * reached and did try. Without this, a DummyAvatar-shaped scene would satisfy
 * the rule above while proving nothing at all.
 */
rule avatarEnableModuleAttemptIsReachable(
    address to, uint256 value, bytes data, Enum.Operation operation
) {
    env e;
    require moduleEntry(SENTINEL_MODULES()) == SENTINEL_MODULES();
    require target() == hostileAvatar;
    require hostileAvatar.delay() == currentContract;
    require guard() == 0;

    uint256 attemptsBefore = hostileAvatar.attempts();
    require attemptsBefore < max_uint256;

    executeNextTx(e, to, value, data, operation);

    satisfy hostileAvatar.attempts() > attemptsBefore,
        "no queue entry reaches the avatar at all, so the claim-4 rule is vacuous";
}
