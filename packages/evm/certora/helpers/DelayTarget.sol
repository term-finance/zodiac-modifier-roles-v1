// SPDX-License-Identifier: LGPL-3.0-only
pragma solidity >=0.7.0 <0.9.0;

/*
 * @title In-scene model of the Zodiac Delay modifier.
 *
 * @dev VENDORED, NOT IMPORTED. Source of truth is
 * zodiac-modifier-delay/contracts/Delay.sol at tag v1.0.1 — the version
 * behind mastercopy 0xd54895B1121A2eE3f37b502F507631FA1331BED6, which is
 * what both live mainnet Delay proxies (0x0C19d8A4... protocol,
 * 0x80Ce5a0d... DAO) delegate to. v1.0.1 sits on @gnosis.pm/zodiac +
 * OZ-upgradeable 4.x, so its storage is the sequential layout that matches
 * Roles (slot 51 _owner, 101 guard, 102 avatar, 103 target, 104 modules,
 * 105.. txCooldown/txExpiration/txNonce/queueNonce), NOT the ERC-7201
 * namespaced layout of v1.1.0. setTxNonce and executeNextTx are logically
 * identical across the two versions — v1.1.0 only renames the setTxNonce
 * parameter, adds a TxNonceSet event, and renames Enum.Operation to
 * Operation — so the bodies below hold for either, but the pin is v1.0.1
 * because that is what is deployed.
 *
 * Neither version can be pulled into this scene directly:
 *   - v1.0.1 inherits @gnosis.pm/zodiac's Modifier, the same base Roles
 *     inherits — so pulling in the upstream file would put two copies of
 *     `Modifier`, `Module` and `Guardable` in one scene under the same
 *     names, which Certora resolves ambiguously.
 *   - v1.1.0 is worse: it inherits @gnosis-guild/zodiac-core's Modifier on
 *     OZ-upgradeable 5.0.2 (solc ^0.8.20) while this repo is on 4.3.1 and
 *     CI pins a single solc 0.8.6. Certora's `packages` remapping is
 *     scene-global, so only one `@openzeppelin` resolves at a time.
 * So the parts of Delay that this integration actually touches are copied
 * here verbatim and compiled under the Roles toolchain. Every function
 * below is byte-identical to upstream apart from the three deliberate
 * deviations listed under "Model deviations". Keep in sync: if Delay.sol
 * changes, this file and delaySetTxNonce.spec have to be revisited.
 *
 * Model deviations, and why each is sound for the rules in
 * certora/specs/Roles/delaySetTxNonce.spec:
 *
 *  1. Events are dropped. No rule observes logs.
 *
 *  2. `Operation` is spelled `uint8` rather than the upstream enum. The
 *     enum is {Call, DelegateCall} in both dependency trees and
 *     `abi.encodePacked` of an enum emits one byte, so getTransactionHash
 *     is unchanged for operation < 2. Using a raw uint8 additionally lets
 *     the prover consider operation >= 2, which only widens the input
 *     space.
 *
 *  3. `executeNextTx`'s final `require(exec(...))` (Delay.sol:203) is
 *     modelled as an unconditional success. exec() forwards to the avatar
 *     and can only ADD a revert; dropping it makes the executor strictly
 *     more permissive. Every claim about executeNextTx here is a negative
 *     one ("this queue entry can never execute"), so proving it against a
 *     never-failing executor is the conservative direction.
 *
 *  4. The upstream `moduleOnly` gate on the two queueing entry points is
 *     modelled as a plain `modules` mapping check rather than Zodiac's
 *     linked list. Same predicate (`modules[msg.sender] != address(0)`,
 *     Modifier.sol:59-62), without dragging a second Modifier base into
 *     the scene.
 *
 * `owner`/`onlyOwner` stand in for OwnableUpgradeable, which is where
 * upstream's `onlyOwner` comes from via FactoryFriendly. Upstream OZ 5
 * reverts with the custom error OwnableUnauthorizedAccount where this
 * reverts with a string; no rule distinguishes revert reasons.
 */
contract DelayTarget {
    address public owner;
    address public avatar;
    mapping(address => address) public modules;

    uint256 public txCooldown;
    uint256 public txExpiration;
    uint256 public txNonce;
    uint256 public queueNonce;
    // Mapping of queue nonce to transaction hash.
    mapping(uint256 => bytes32) public txHash;
    // Mapping of queue nonce to creation timestamp.
    mapping(uint256 => uint256) public txCreatedAt;

    modifier onlyOwner() {
        require(owner == msg.sender, "Ownable: caller is not the owner");
        _;
    }

    modifier moduleOnly() {
        require(modules[msg.sender] != address(0), "Module not authorized");
        _;
    }

    /// @dev Delay.sol:91-94
    function setTxCooldown(uint256 _txCooldown) public onlyOwner {
        txCooldown = _txCooldown;
    }

    /// @dev Delay.sol:100-109
    function setTxExpiration(uint256 _txExpiration) public onlyOwner {
        require(
            _txExpiration == 0 || _txExpiration >= 60,
            "Expiration must be 0 or at least 60 seconds"
        );
        txExpiration = _txExpiration;
    }

    /// @dev Delay.sol:114-122. The subject of this integration: the only
    /// way to invalidate already-queued transactions, gated on ownership
    /// of the Delay rather than on any Roles-side permission.
    function setTxNonce(uint256 _txNonce) public onlyOwner {
        require(
            _txNonce > txNonce,
            "New nonce must be higher than current txNonce"
        );
        require(_txNonce <= queueNonce, "Cannot be higher than queueNonce");
        txNonce = _txNonce;
    }

    /// @dev Delay.sol:131-143
    function execTransactionFromModule(
        address to,
        uint256 value,
        bytes calldata data,
        uint8 operation
    ) public moduleOnly returns (bool success) {
        bytes32 hash = getTransactionHash(to, value, data, operation);
        txHash[queueNonce] = hash;
        txCreatedAt[queueNonce] = block.timestamp;
        queueNonce++;
        success = true;
    }

    /// @dev Delay.sol:153-171
    function execTransactionFromModuleReturnData(
        address to,
        uint256 value,
        bytes calldata data,
        uint8 operation
    ) public moduleOnly returns (bool success, bytes memory returnData) {
        bytes32 hash = getTransactionHash(to, value, data, operation);
        txHash[queueNonce] = hash;
        txCreatedAt[queueNonce] = block.timestamp;
        success = true;
        returnData = abi.encode(queueNonce, hash, block.timestamp);
        queueNonce++;
    }

    /// @dev Delay.sol:179-204, with deviation 3 above.
    function executeNextTx(
        address to,
        uint256 value,
        bytes calldata data,
        uint8 operation
    ) public {
        require(txNonce < queueNonce, "Transaction queue is empty");
        uint256 txCreationTimestamp = txCreatedAt[txNonce];
        require(
            block.timestamp - txCreationTimestamp >= txCooldown,
            "Transaction is still in cooldown"
        );
        if (txExpiration != 0) {
            require(
                txCreationTimestamp + txCooldown + txExpiration >=
                    block.timestamp,
                "Transaction expired"
            );
        }
        require(
            txHash[txNonce] == getTransactionHash(to, value, data, operation),
            "Transaction hashes do not match"
        );
        txNonce++;
    }

    /// @dev Delay.sol:206-215
    function skipExpired() public {
        while (
            txExpiration != 0 &&
            txCreatedAt[txNonce] + txCooldown + txExpiration <
                block.timestamp &&
            txNonce < queueNonce
        ) {
            txNonce++;
        }
    }

    /// @dev Delay.sol:217-224
    function getTransactionHash(
        address to,
        uint256 value,
        bytes memory data,
        uint8 operation
    ) public pure returns (bytes32) {
        return keccak256(abi.encodePacked(to, value, data, operation));
    }
}
