// SPDX-License-Identifier: LGPL-3.0-only
pragma solidity >=0.7.0 <0.9.0;

/*
 * @title In-scene model of the Zodiac Delay modifier.
 *
 * @dev Vendored from zodiac-modifier-delay contracts/Delay.sol v1.0.1, the
 * version behind mastercopy 0xd54895B1121A2eE3f37b502F507631FA1331BED6 that
 * the live Delay proxies delegate to. Line references below are to that file.
 * Each function is copied verbatim apart from these deviations:
 *   1. Events are dropped.
 *   2. `Operation` is spelled `uint8` rather than the upstream enum.
 *      abi.encodePacked of the enum emits one byte, so getTransactionHash is
 *      unchanged for operation < 2.
 *   3. executeNextTx's final `require(exec(...))` (Delay.sol:203) is modelled
 *      as an unconditional success: exec() forwards to the avatar and can only
 *      add a revert.
 *   4. moduleOnly is a plain `modules` mapping check rather than Zodiac's
 *      linked list, with the same predicate, modules[msg.sender] != address(0).
 *
 * `owner` and `onlyOwner` stand in for OwnableUpgradeable.
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

    /// @dev Delay.sol:114-122.
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
