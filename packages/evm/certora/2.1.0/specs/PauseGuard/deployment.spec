/*
 * PauseGuard deployment: what PauseGuard's constructor sets up holds for the
 * life of the contract. Each invariant's base case runs the real constructor,
 * with any arguments it accepts.
 *
 * PauseGuard is the only contract in the scene.
 */

methods {
    function pauser() external returns (address) envfree;
}

/*
 * From the constructor on, pauser() is never the zero address.
 */
invariant pauserNeverZero()
    pauser() != 0;

/*
 * setPauser(address(0)) reverts for every caller, the admin included.
 */
rule setPauserRevertsOnZeroAddress() {
    env e;

    setPauser@withrevert(e, 0);

    assert lastReverted,
        "setPauser accepted the zero address";
}
