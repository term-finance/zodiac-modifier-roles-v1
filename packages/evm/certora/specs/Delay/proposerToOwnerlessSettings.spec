/*
 * Property: the Term multisig holders on the ProposerSafe can change the
 * OwnerlessSafe's owners, threshold, modules, guard and fallback handler,
 * end to end, through the Delay Modifier.
 *
 * It covers the ProposerSafe's half of P4.OwnerlessSafe.12 in PROOFS.md. The
 * OwnerlessSafe's own owners reach the same settings directly, which is
 * specs/Safe/signedSettings.spec. Here the ProposerSafe's owners reach them
 * the only way they can: the ProposerSafe is the Delay Modifier's one module
 * (P1.8) and the Delay Modifier is the OwnerlessSafe's one module (P1.5), so
 * the flow, in two transactions, is:
 *
 *   1. an owner of the ProposerSafe calls approveHash on the hash of a
 *      ProposerSafe transaction that calls the Delay's
 *      execTransactionFromModule(OwnerlessSafe, 0, <settings call>, Call), and
 *      anyone submits it with that approval as the signature. The
 *      ProposerSafe's signature check runs for real, the ProposerSafe calls
 *      the Delay, and the Delay queues the proposal;
 *   2. once the cooldown has passed and before the proposal expires, anyone
 *      calls the Delay's executeNextTx with the proposal. The Delay hands it
 *      to its target, the OwnerlessSafe, whose execTransactionFromModule makes
 *      the OwnerlessSafe call its own settings function, and the setting
 *      changes.
 *
 * The earlier rules each cover a piece of this: DM-5 the queueing, DP-29 the
 * execution (with a stand-in for the OwnerlessSafe), LG-2 and SC-1 the
 * module's settings call. The last rule here, proposerApprovalChangesOwnerless-
 * Settings, runs the real code of both Safes and the Delay in one execution.
 * It only passes if the owner's approval is what gets the proposal queued, the
 * queued entry is exactly the proposal that executes, and the Delay's
 * execution is what changes the setting.
 *
 * Rules:
 *   queueCallLayoutIsSatisfiable
 *     the calldata the rules below pin can exist (a check on the rules, not
 *     on the contracts; one settings function per call length)
 *   proposerApprovalQueuesAnEntry
 *     the first transaction can succeed and queue something (one settings
 *     function per call length)
 *   proposerApprovalQueuesTheProposal
 *     the first transaction alone: the owner's approval gets the Delay to
 *     store the hash of (OwnerlessSafe, 0, <settings call>, Call)
 *   queuedProposalChangesOwnerlessSettings
 *     the second transaction alone: an entry with that hash, past its
 *     cooldown, makes the OwnerlessSafe change the setting
 *   proposerApprovalChangesOwnerlessSettings
 *     both, in one execution
 * The first two are the flow cut at the Delay's queue, and the hash the Delay
 * stores is what joins them. They are also what shows which half the Prover
 * cannot check if the whole does not run.
 *
 * The scene is the real GnosisSafe v1.3.0 code twice, as ProposerSafeHarness
 * and OwnerlessSafeHarness (solc 0.7.6), and the real Delay mastercopy source,
 * certora/helpers/Delay.sol (solc 0.8.6), whose target is linked to the
 * OwnerlessSafe. No guard is installed on either Safe or on the Delay.
 *
 * Why a witness (satisfy) and not an assert. execTransaction reads gasleft()
 * (GS010), which the Prover treats as an unconstrained value, so "does not
 * revert" cannot be asserted for every execution. The rule shows an execution
 * exists in which the owner's approval alone makes the OwnerlessSafe change
 * each setting. That is what "can be changed by the Term multisig holders"
 * needs.
 *
 * Modelling notes.
 *   - The ProposerSafe's threshold is 1 and the owner's approval is the one
 *     signature. The Prover unrolls the signature loop once (loop_iter 1);
 *     the deployed threshold is 5. The loop is covered one pass at a time by
 *     eachSignatureAcceptsANewApprovingOwner (SE-12), and a threshold-t check
 *     only repeats that pass t times.
 *   - The wiring is the deployed one: the ProposerSafe is an enabled module
 *     of the Delay, the Delay is an enabled module of the OwnerlessSafe, and
 *     the Delay's target is the OwnerlessSafe. The Delay's queue starts empty.
 *   - Each Safe's call is a low-level `call` with a symbolic target, which the
 *     Prover cannot resolve. The ProposerSafe's is routed to
 *     Delay.execTransactionFromModule, which is what it calls on chain. The
 *     OwnerlessSafe's is routed to its own settings functions, which is what
 *     happens when `to` is the OwnerlessSafe itself. DISPATCH ignores `to`,
 *     so the rule pins `to`. Any other call either Safe makes is havoced.
 *   - The ProposerSafe's call to the Delay carries a `bytes` argument inside
 *     `bytes`. The rule builds that calldata by pinning every word of it, and
 *     pins its inner call byte for byte to the call the Delay later executes,
 *     so the entry the Delay queues is the entry executeNextTx runs. The
 *     calldata lengths are fixed for the Prover, as in delayOwnerGuard.spec.
 *   - The proposal's expiry and cooldown are the Delay's own: the second
 *     transaction runs after the cooldown and before expiry, as in DP-29.
 */

using ProposerSafeHarness as proposerSafe;
using Delay as delayContract;
using CalldataReader as reader;

methods {
    // The OwnerlessSafe, the scene's main contract.
    function moduleEntry(address) external returns (address) envfree;
    function ownerEntry(address) external returns (address) envfree;
    function thresholdValue() external returns (uint256) envfree;
    function guardAddress() external returns (address) envfree;
    function fallbackHandlerSlotWord() external returns (uint256) envfree;
    function selectorOf(bytes) external returns (uint32) envfree;

    function proposerSafe.ownerEntry(address) external returns (address) envfree;
    function proposerSafe.thresholdValue() external returns (uint256) envfree;
    function proposerSafe.guardAddress() external returns (address) envfree;
    function proposerSafe.nonce() external returns (uint256) envfree;

    function delayContract.guard() external returns (address) envfree;
    function delayContract.target() external returns (address) envfree;
    function delayContract.isModuleEnabled(address) external returns (bool) envfree;
    function delayContract.txNonce() external returns (uint256) envfree;
    function delayContract.queueNonce() external returns (uint256) envfree;
    function delayContract.txCooldown() external returns (uint256) envfree;
    function delayContract.txExpiration() external returns (uint256) envfree;
    function delayContract.txCreatedAt(uint256) external returns (uint256) envfree;
    function delayContract.txHash(uint256) external returns (bytes32) envfree;
    function delayContract.getTransactionHash(address, uint256, bytes, Enum.Operation) external returns (bytes32) envfree;

    function reader.wordAtByte(bytes, uint256) external returns (uint256) envfree;
    function reader.addressAtByte(bytes, uint256) external returns (address) envfree;
    function reader.isApprovedHashSig(bytes, address) external returns (bool) envfree;

    // The ProposerSafe's call to `to`, run as the call to the Delay it makes
    // on chain.
    unresolved external in ProposerSafeHarness._ => DISPATCH [
        Delay.execTransactionFromModule(address, uint256, bytes, Enum.Operation)
    ] default NONDET;

    // The OwnerlessSafe's call to `to`, run as a call to its own settings
    // functions.
    unresolved external in OwnerlessSafeHarness._ => DISPATCH [
        OwnerlessSafeHarness.enableModule(address),
        OwnerlessSafeHarness.disableModule(address, address),
        OwnerlessSafeHarness.addOwnerWithThreshold(address, uint256),
        OwnerlessSafeHarness.removeOwner(address, address, uint256),
        OwnerlessSafeHarness.swapOwner(address, address, address),
        OwnerlessSafeHarness.changeThreshold(uint256),
        OwnerlessSafeHarness.setGuard(address),
        OwnerlessSafeHarness.setFallbackHandler(address)
    ] default HAVOC_ECF;
}

/// Head of the Safes' owner and module lists.
definition SENTINEL() returns address = 0x1;

definition isSelfOnlySetting(method f) returns bool =
    f.selector == sig:enableModule(address).selector ||
    f.selector == sig:disableModule(address, address).selector ||
    f.selector == sig:addOwnerWithThreshold(address, uint256).selector ||
    f.selector == sig:removeOwner(address, address, uint256).selector ||
    f.selector == sig:swapOwner(address, address, address).selector ||
    f.selector == sig:changeThreshold(uint256).selector ||
    f.selector == sig:setGuard(address).selector ||
    f.selector == sig:setFallbackHandler(address).selector;

/// One settings function for each call length (36, 68 and 100 bytes), for the
/// checks on the rules themselves.
definition isOnePerLength(method f) returns bool =
    f.selector == sig:enableModule(address).selector ||
    f.selector == sig:addOwnerWithThreshold(address, uint256).selector ||
    f.selector == sig:removeOwner(address, address, uint256).selector;

/// The length of the OwnerlessSafe's call to each settings function: the
/// selector, then one 32-byte word per argument.
definition settingCallLength(method f) returns uint256 =
    (f.selector == sig:disableModule(address, address).selector ||
     f.selector == sig:addOwnerWithThreshold(address, uint256).selector) ? 68 :
    (f.selector == sig:removeOwner(address, address, uint256).selector ||
     f.selector == sig:swapOwner(address, address, address).selector) ? 100 :
    36;

/// The length of the ProposerSafe's call to the Delay that carries that
/// settings call: the selector (4 bytes), four head words (to, value, the
/// offset of `data`, operation) and the length of `data` (32 bytes each),
/// which is 164 bytes, then `data` padded to a whole number of words.
definition queueCallLength(method f) returns uint256 =
    settingCallLength(f) == 36 ? 228 :
    settingCallLength(f) == 68 ? 260 :
    292;

/*
 * `q` is the ABI encoding of the Delay's
 * execTransactionFromModule(to, 0, inner, Call), and `inner` is its `data`
 * argument, L bytes long (36, 68 or 100):
 *   bytes 0-3          the selector
 *   bytes 4-35         to
 *   bytes 36-67        value, 0
 *   bytes 68-99        the offset of `data`, 128
 *   bytes 100-131      operation, 0 (Call)
 *   bytes 132-163      the length of `data`, L
 *   bytes 164-         `data`, padded with zeros to a whole word
 * The bytes of `data` are compared by overlapping 32-byte windows at the
 * start, at every whole word that fits, and at the end, which together cover
 * all L bytes.
 *
 * A window read past the end of an array reverts, and a revert inside a
 * `require` leaves no execution at all. So the windows that only fit a longer
 * `inner` (the whole words at 32 and 64) are read inside `if` statements,
 * which only make the read when it is in range, and not behind an implication
 * in one expression. The reads in the first expression are in range for every
 * L this rule uses.
 */
function isQueueCall(bytes q, address to, bytes inner, uint256 L) returns bool {
    bool head =
        selectorOf(q) == sig:Delay.execTransactionFromModule(address, uint256, bytes, Enum.Operation).selector &&
        reader.addressAtByte(q, 4) == to &&
        reader.wordAtByte(q, 36) == 0 &&
        reader.wordAtByte(q, 68) == 128 &&
        reader.wordAtByte(q, 100) == 0 &&
        reader.wordAtByte(q, 132) == L &&
        reader.wordAtByte(q, 164) == reader.wordAtByte(inner, 0) &&
        reader.wordAtByte(q, assert_uint256(164 + L - 32)) == reader.wordAtByte(inner, assert_uint256(L - 32));
    bool word32 = true;
    bool word64 = true;
    if (L >= 64) {
        word32 = reader.wordAtByte(q, 196) == reader.wordAtByte(inner, 32);
    }
    if (L >= 96) {
        word64 = reader.wordAtByte(q, 228) == reader.wordAtByte(inner, 64);
    }
    return head && word32 && word64;
}

/// The deployed wiring: the ProposerSafe is a module of the Delay, the Delay
/// is a module of the OwnerlessSafe and its target, with no guard, and
/// neither Safe has a guard.
function wiredScene() {
    require delayContract.isModuleEnabled(proposerSafe);
    require moduleEntry(delayContract) != 0;
    require delayContract != SENTINEL();
    require delayContract.target() == currentContract;
    require delayContract.guard() == 0;
    require guardAddress() == 0;
    require proposerSafe.guardAddress() == 0;
}

/// The ProposerSafe's threshold is one and its owner is the signer, whose
/// approval is the one signature.
function ownerSigns(address owner, bytes signatures) {
    require proposerSafe.thresholdValue() == 1;
    require owner != SENTINEL();
    require proposerSafe.ownerEntry(owner) != 0;
    require reader.isApprovedHashSig(signatures, owner);
}

/// The OwnerlessSafe's call to one of its own settings functions, `inner`.
function settingsCall(method f, bytes inner) {
    require inner.length == settingCallLength(f);
    require selectorOf(inner) == f.selector;
}

/*
 * 1. The ProposerSafe's owner approves the transaction that queues the
 * proposal, and anyone submits it. The transaction is the ProposerSafe's call
 * to the Delay's execTransactionFromModule(OwnerlessSafe, 0, inner, Call),
 * carried in `queueData`.
 */
function ownerQueuesTheProposal(address owner, bytes queueData, bytes signatures) {
    env eApprove;
    env eQueue;
    require eApprove.msg.sender == owner;

    bytes32 txHash = proposerSafe.getTransactionHash(eQueue,
        delayContract, 0, queueData, Enum.Operation.Call, 0, 0, 0, 0, 0, proposerSafe.nonce());
    proposerSafe.approveHash(eApprove, txHash);
    proposerSafe.execTransaction(eQueue,
        delayContract, 0, queueData, Enum.Operation.Call, 0, 0, 0, 0, 0, signatures);
}

/*
 * 2. After the cooldown, and before the proposal expires, anyone executes it:
 * the Delay's executeNextTx with the proposal's own arguments. The timing is
 * the Delay's own, as in DP-29. True if it did not revert.
 */
function anyoneExecutes(bytes inner, uint256 createdAt) returns bool {
    env eExec;
    require eExec.msg.value == 0;
    require eExec.block.timestamp >= createdAt;
    require eExec.block.timestamp - createdAt >= delayContract.txCooldown();
    require createdAt + delayContract.txCooldown() + delayContract.txExpiration() <= max_uint256;
    require delayContract.txExpiration() == 0 ||
        createdAt + delayContract.txCooldown() + delayContract.txExpiration() >= to_mathint(eExec.block.timestamp);

    delayContract.executeNextTx@withrevert(eExec, currentContract, 0, inner, Enum.Operation.Call);
    return !lastReverted;
}

/*
 * The pinned calldata can exist. Nothing but the layout is required: some
 * ProposerSafe call to the Delay has the encoding isQueueCall describes, for
 * each settings function's length. If this fails, the layout contradicts
 * itself and every rule below that pins it holds for no execution.
 */
rule queueCallLayoutIsSatisfiable(method f, bytes inner, bytes queueData)
    filtered { f -> isOnePerLength(f) }
{
    settingsCall(f, inner);
    require queueData.length == queueCallLength(f);
    require isQueueCall(queueData, currentContract, inner, settingCallLength(f));

    satisfy true, "the queue call's layout cannot exist";
}

/* ------------------------------------------------------------------------
 * The two halves, and the whole.
 *
 * The first two rules are the flow cut at the Delay's queue: the entry the
 * ProposerSafe's owner gets queued is the hash of the OwnerlessSafe's
 * settings call, and an entry with that hash, once past its cooldown, makes
 * the OwnerlessSafe change the setting. The third rule runs both in one
 * execution. If the third cannot be checked, the first two still show each
 * half, and the Delay's stored hash is what joins them.
 * --------------------------------------------------------------------- */

/*
 * The first transaction can succeed at all. The ProposerSafe's owner approves
 * the transaction that calls the Delay with the pinned calldata, anyone
 * submits it, and the Delay's queue grows by one entry. Nothing is said about
 * what the entry is; the next rule says that. If this one passes and the next
 * does not, the pinned calldata does not decode to the proposal it is meant
 * to.
 */
rule proposerApprovalQueuesAnEntry(
    method f, address owner, bytes inner, bytes queueData, bytes signatures
)
    filtered { f -> isOnePerLength(f) }
{
    wiredScene();
    require delayContract.txNonce() == delayContract.queueNonce();
    require delayContract.queueNonce() < max_uint256;
    ownerSigns(owner, signatures);
    settingsCall(f, inner);
    require queueData.length == queueCallLength(f);
    require isQueueCall(queueData, currentContract, inner, settingCallLength(f));

    uint256 slot = delayContract.queueNonce();

    ownerQueuesTheProposal(owner, queueData, signatures);

    satisfy to_mathint(delayContract.queueNonce()) == slot + 1,
        "the ProposerSafe's owner could not get the Delay to queue anything";
}

/*
 * First half. The ProposerSafe's owner approves the proposal, anyone submits
 * it, and the Delay queues it: its queue grows by one entry, and that entry
 * is the hash of exactly the transaction the OwnerlessSafe will be asked to
 * make, (OwnerlessSafe, 0, inner, Call). For each of the OwnerlessSafe's eight
 * settings functions; `f` only picks which function's selector `inner`
 * carries.
 */
rule proposerApprovalQueuesTheProposal(
    method f, address owner, bytes inner, bytes queueData, bytes signatures
)
    filtered { f -> isSelfOnlySetting(f) }
{
    wiredScene();
    require delayContract.txNonce() == delayContract.queueNonce();
    require delayContract.queueNonce() < max_uint256;
    ownerSigns(owner, signatures);
    settingsCall(f, inner);
    require queueData.length == queueCallLength(f);
    require isQueueCall(queueData, currentContract, inner, settingCallLength(f));

    uint256 slot = delayContract.queueNonce();

    ownerQueuesTheProposal(owner, queueData, signatures);

    satisfy to_mathint(delayContract.queueNonce()) == slot + 1 &&
        delayContract.txHash(slot) == delayContract.getTransactionHash(currentContract, 0, inner, Enum.Operation.Call),
        "the ProposerSafe's owner could not get the Delay to queue the OwnerlessSafe's settings call";
}

/*
 * Second half. The Delay's next entry is the hash of the OwnerlessSafe's
 * settings call, and its cooldown has passed: anyone's executeNextTx runs it,
 * the Delay hands it to the OwnerlessSafe, and the OwnerlessSafe changes a
 * setting. For each of the eight settings functions.
 */
rule queuedProposalChangesOwnerlessSettings(method f, address a, bytes inner)
    filtered { f -> isSelfOnlySetting(f) }
{
    wiredScene();
    settingsCall(f, inner);

    uint256 n = delayContract.txNonce();
    require n < delayContract.queueNonce();
    require delayContract.txHash(n) == delayContract.getTransactionHash(currentContract, 0, inner, Enum.Operation.Call);

    uint256 thresholdBefore = thresholdValue();
    address ownerBefore = ownerEntry(a);
    address moduleBefore = moduleEntry(a);
    uint256 handlerBefore = fallbackHandlerSlotWord();

    bool executed = anyoneExecutes(inner, delayContract.txCreatedAt(n));

    satisfy executed && (
        thresholdValue() != thresholdBefore ||
        ownerEntry(a) != ownerBefore ||
        moduleEntry(a) != moduleBefore ||
        guardAddress() != 0 ||
        fallbackHandlerSlotWord() != handlerBefore),
        "an entry past its cooldown could not make the OwnerlessSafe change a setting through this settings function";
}

/*
 * The whole flow in one execution. The ProposerSafe's owner approves a
 * proposal to the Delay, the Delay queues it, the cooldown passes, and
 * executing it makes the OwnerlessSafe change a setting: for each of the
 * OwnerlessSafe's eight settings functions. `f` only picks which function's
 * selector the proposal's call carries.
 */
rule proposerApprovalChangesOwnerlessSettings(
    method f, address owner, address a, bytes inner, bytes queueData, bytes signatures
)
    filtered { f -> isSelfOnlySetting(f) }
{
    wiredScene();
    require delayContract.txNonce() == delayContract.queueNonce();
    require delayContract.queueNonce() < max_uint256;
    ownerSigns(owner, signatures);
    settingsCall(f, inner);
    require queueData.length == queueCallLength(f);
    require isQueueCall(queueData, currentContract, inner, settingCallLength(f));

    uint256 thresholdBefore = thresholdValue();
    address ownerBefore = ownerEntry(a);
    address moduleBefore = moduleEntry(a);
    uint256 handlerBefore = fallbackHandlerSlotWord();

    ownerQueuesTheProposal(owner, queueData, signatures);

    bool executed = anyoneExecutes(inner, delayContract.txCreatedAt(delayContract.txNonce()));

    satisfy executed && (
        thresholdValue() != thresholdBefore ||
        ownerEntry(a) != ownerBefore ||
        moduleEntry(a) != moduleBefore ||
        guardAddress() != 0 ||
        fallbackHandlerSlotWord() != handlerBefore),
        "the ProposerSafe's owner could not get a proposal through the Delay that makes the OwnerlessSafe change a setting through this settings function";
}
