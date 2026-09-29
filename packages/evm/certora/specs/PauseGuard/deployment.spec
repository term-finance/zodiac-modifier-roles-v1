/*
 * Property: what PauseGuard's constructor sets up holds for the life of the
 * contract. Each invariant's base case runs the real constructor, with any
 * arguments it accepts, so these are checked against it rather than read off
 * source:
 *
 *     defaultAdminRoleNeverHeld   nobody ever holds DEFAULT_ADMIN_ROLE
 *     roleAdminWiringIsFixed      ADMIN_ROLE and DEFAULT_ADMIN_ROLE are both
 *                                 administered by DEFAULT_ADMIN_ROLE, always
 *     exactlyOneAdminRoleHolder   ADMIN_ROLE has exactly one holder, always
 *     pauserNeverZero             the pauser is never the zero address
 *     setPauserRevertsOnZeroAddress
 *                                 setPauser(address(0)) always reverts
 *
 * Together with the deployed state (hasRole(ADMIN_ROLE, <Admin Safe>) and
 * pauser() read on chain), exactlyOneAdminRoleHolder makes the Admin Safe the
 * only ADMIN_ROLE holder there can ever be.
 *
 * PauseGuard is the only contract in the scene. Its behaviour with the Delay
 * is Delay-pauseGuardSufficient.conf.
 */

methods {
    function pauser() external returns (address) envfree;
    function hasRole(bytes32, address) external returns (bool) envfree;
    function getRoleAdmin(bytes32) external returns (bytes32) envfree;
    function ADMIN_ROLE() external returns (bytes32) envfree;
    function DEFAULT_ADMIN_ROLE() external returns (bytes32) envfree;
}

/// keccak256("ADMIN_ROLE"), for the hook, which cannot call ADMIN_ROLE().
definition ADMIN_ROLE_ID() returns bytes32 =
    to_bytes32(0xa49807205ce4d355092ef5a8a18f56e8913cf4a201fbe287825b095693c21775);

/*
 * Number of ADMIN_ROLE holders, kept in step with AccessControl's membership
 * map. Storage starts zeroed before the constructor, so the count starts at 0.
 */
ghost mathint adminRoleHolders {
    init_state axiom adminRoleHolders == 0;
}

hook Sstore _roles[KEY bytes32 role].members[KEY address account] bool newValue (bool oldValue) {
    if (role == ADMIN_ROLE_ID()) {
        adminRoleHolders = adminRoleHolders + (newValue ? 1 : 0) - (oldValue ? 1 : 0);
    }
}

/*
 * The constructor grants DEFAULT_ADMIN_ROLE to nobody, and nothing grants it
 * later: its admin is itself, so grantRole needs a holder to begin with.
 */
invariant defaultAdminRoleNeverHeld(address account)
    !hasRole(DEFAULT_ADMIN_ROLE(), account)
    {
        preserved with (env e) {
            requireInvariant defaultAdminRoleNeverHeld(e.msg.sender);
            requireInvariant roleAdminWiringIsFixed();
        }
    }

/*
 * Both roles are administered by DEFAULT_ADMIN_ROLE from the constructor on.
 * Nothing calls _setRoleAdmin.
 */
invariant roleAdminWiringIsFixed()
    getRoleAdmin(ADMIN_ROLE()) == DEFAULT_ADMIN_ROLE() &&
    getRoleAdmin(DEFAULT_ADMIN_ROLE()) == DEFAULT_ADMIN_ROLE();

/*
 * The constructor grants ADMIN_ROLE to exactly one address, its nonzero
 * `_admin`, and membership never changes after that: grantRole and revokeRole
 * need DEFAULT_ADMIN_ROLE, which nobody holds, and renounceRole always
 * reverts.
 */
invariant exactlyOneAdminRoleHolder()
    adminRoleHolders == 1
    {
        preserved with (env e) {
            requireInvariant defaultAdminRoleNeverHeld(e.msg.sender);
            requireInvariant roleAdminWiringIsFixed();
        }
    }

/*
 * The constructor rejects a zero `_pauser`, and setPauser rejects a zero
 * account, so there is always an account that can pause.
 */
invariant pauserNeverZero()
    pauser() != 0;

/*
 * setPauser(address(0)) reverts for every caller, admins included.
 */
rule setPauserRevertsOnZeroAddress() {
    env e;

    setPauser@withrevert(e, 0);

    assert lastReverted,
        "setPauser accepted the zero address";
}
