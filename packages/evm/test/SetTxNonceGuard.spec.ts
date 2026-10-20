import { expect } from "chai";
import { BigNumber, BigNumberish, Contract, Wallet } from "ethers";
import hre, { deployments, waffle, ethers } from "hardhat";

import "@nomiclabs/hardhat-ethers";

import { SetTxNonceGuard } from "../typechain-types";

/*
 * SetTxNonceGuard as deployed: installed with setGuard on the Roles Modifier
 * whose module is the Governor, with delay = the Delay Modifier, so that the
 * Governor can do nothing through the Roles Modifier but call setTxNonce on
 * the Delay (the veto).
 *
 * The Certora specs (specs/Roles/setTxNonce*.spec) check the guard through the
 * Roles Modifier against stand-ins: DelayTarget for the Delay, and DummyAvatar
 * or ForwardingAvatar for the DelayOwnerSafe. Their rules assert which calls
 * complete, not which error the guard raises or in what order it checks.
 * These tests run the guard on its own, then through the real Roles Modifier
 * into a real Safe v1.4.1 (the DelayOwnerSafe's version) that owns a real
 * Delay v1.0.1 (contracts/test/*Imports.sol). Every call is encoded from those
 * contracts' own ABIs.
 */

const { AddressZero, HashZero, MaxUint256 } = ethers.constants;

const SENTINEL = "0x0000000000000000000000000000000000000001";

const CALL = 0;
const DELEGATE_CALL = 1;

// ExecutionOptions in Permissions.sol
const OPTIONS_NONE = 0;
const OPTIONS_BOTH = 3;

const ROLE = 1;

// Stand-in for an address inside calldata the guard only inspects.
const SOMEONE = "0x00000000000000000000000000000000000000aa";

const abiOf = (name: string) =>
  new ethers.utils.Interface(hre.artifacts.readArtifactSync(name).abi);

const delayAbi = abiOf("Delay");
const safeAbi = abiOf("Safe");
const testContractAbi = abiOf("TestContract");
const multiSendAbi = abiOf("MultiSend");

const DO_NOTHING = testContractAbi.encodeFunctionData("doNothing");
const SET_TX_NONCE = delayAbi.getSighash("setTxNonce");

const setTxNonce = (nonce: BigNumberish) =>
  delayAbi.encodeFunctionData("setTxNonce", [nonce]);

const selectorOf = (data: string) => ethers.utils.hexDataSlice(data, 0, 4);

/* hardhat names the guard's custom error, with its arguments, in the revert
 * message. */
const customError = (name: string, ...args: string[]) =>
  `custom error '${name}(${args.map((a) => `"${a}"`).join(", ")})'`;

const unexpectedTarget = (to: string) =>
  customError("UnexpectedTarget", ethers.utils.getAddress(to));

// The Delay's owner functions other than setTxNonce.
const DELAY_OWNER_CALLS = [
  delayAbi.encodeFunctionData("setTxCooldown", [0]),
  delayAbi.encodeFunctionData("setTxExpiration", [0]),
  delayAbi.encodeFunctionData("transferOwnership", [SOMEONE]),
  delayAbi.encodeFunctionData("renounceOwnership"),
  delayAbi.encodeFunctionData("enableModule", [SOMEONE]),
  delayAbi.encodeFunctionData("disableModule", [SENTINEL, SOMEONE]),
  delayAbi.encodeFunctionData("setGuard", [SOMEONE]),
  delayAbi.encodeFunctionData("setAvatar", [SOMEONE]),
  delayAbi.encodeFunctionData("setTarget", [SOMEONE]),
];

const checkTransaction = (
  guard: SetTxNonceGuard,
  to: string,
  value: BigNumberish,
  data: string,
  operation = CALL
) =>
  guard.checkTransaction(
    to,
    value,
    data,
    operation,
    0,
    0,
    0,
    AddressZero,
    AddressZero,
    "0x",
    AddressZero
  );

describe("SetTxNonceGuard", async () => {
  const setup = deployments.createFixture(async () => {
    const [deployer, delay, stranger] = waffle.provider.getWallets();

    // Called directly, `delay` only needs to be an address: the guard never
    // calls it.
    const Guard = await hre.ethers.getContractFactory("SetTxNonceGuard");
    const guard = (await Guard.deploy(delay.address)) as SetTxNonceGuard;

    return { guard, deployer, delay, stranger };
  });

  describe("called directly", async () => {
    it("accepts setTxNonce(n) on the Delay, with no value, as a plain call", async () => {
      const { guard, delay } = await setup();

      for (const nonce of [0, 1, MaxUint256]) {
        await expect(
          checkTransaction(guard, delay.address, 0, setTxNonce(nonce))
        ).to.not.be.reverted;
      }
    });

    it("rejects any other destination with UnexpectedTarget(to)", async () => {
      const { guard, stranger } = await setup();

      for (const to of [
        stranger.address,
        AddressZero,
        guard.address,
        SOMEONE,
      ]) {
        await expect(
          checkTransaction(guard, to, 0, setTxNonce(1))
        ).to.be.revertedWith(unexpectedTarget(to));
      }
    });

    it("rejects a delegate call with UnexpectedOperation", async () => {
      const { guard, delay } = await setup();

      await expect(
        checkTransaction(guard, delay.address, 0, setTxNonce(1), DELEGATE_CALL)
      ).to.be.revertedWith(customError("UnexpectedOperation"));
    });

    it("rejects an operation outside the enum", async () => {
      const { guard, deployer, delay } = await setup();

      const data = guard.interface.encodeFunctionData("checkTransaction", [
        delay.address,
        0,
        setTxNonce(1),
        2,
        0,
        0,
        0,
        AddressZero,
        AddressZero,
        "0x",
        AddressZero,
      ]);

      await expect(deployer.call({ to: guard.address, data })).to.be.reverted;
    });

    it("rejects any value with UnexpectedValue", async () => {
      const { guard, delay } = await setup();

      for (const value of [1, MaxUint256]) {
        await expect(
          checkTransaction(guard, delay.address, value, setTxNonce(1))
        ).to.be.revertedWith(customError("UnexpectedValue"));
      }
    });

    it("requires exactly 36 bytes of calldata", async () => {
      const { guard, delay } = await setup();
      const valid = setTxNonce(1);

      for (const data of [
        "0x",
        ethers.utils.hexDataSlice(valid, 0, 3),
        SET_TX_NONCE,
        ethers.utils.hexDataSlice(valid, 0, 35),
        ethers.utils.hexConcat([valid, "0x00"]),
        ethers.utils.hexConcat([valid, HashZero]),
      ]) {
        await expect(
          checkTransaction(guard, delay.address, 0, data)
        ).to.be.revertedWith(customError("UnexpectedCalldata"));
      }
      await expect(checkTransaction(guard, delay.address, 0, valid)).to.not.be
        .reverted;
    });

    it("rejects the Delay's other owner functions, including the seven that are 36 bytes", async () => {
      const { guard, delay } = await setup();

      // Only the selector check stops these.
      expect(
        DELAY_OWNER_CALLS.filter((d) => ethers.utils.hexDataLength(d) === 36)
      ).to.have.length(7);

      for (const data of DELAY_OWNER_CALLS) {
        await expect(
          checkTransaction(guard, delay.address, 0, data)
        ).to.be.revertedWith(customError("UnexpectedCalldata"));
      }
    });

    it("rejects 36 bytes behind any other selector", async () => {
      const { guard, delay } = await setup();

      const flipped = ethers.utils.hexlify(BigNumber.from(SET_TX_NONCE).xor(1));
      for (const selector of ["0x00000000", "0xffffffff", flipped]) {
        await expect(
          checkTransaction(
            guard,
            delay.address,
            0,
            ethers.utils.hexConcat([
              selector,
              ethers.utils.hexDataSlice(setTxNonce(1), 4),
            ])
          )
        ).to.be.revertedWith(customError("UnexpectedCalldata"));
      }
    });

    it("checks the destination, then the operation, then the value, then the calldata", async () => {
      const { guard, delay, stranger } = await setup();
      const bad = DELAY_OWNER_CALLS[0];

      await expect(
        checkTransaction(guard, stranger.address, 1, bad, DELEGATE_CALL)
      ).to.be.revertedWith(unexpectedTarget(stranger.address));
      await expect(
        checkTransaction(guard, delay.address, 1, bad, DELEGATE_CALL)
      ).to.be.revertedWith(customError("UnexpectedOperation"));
      await expect(
        checkTransaction(guard, delay.address, 1, bad, CALL)
      ).to.be.revertedWith(customError("UnexpectedValue"));
      await expect(
        checkTransaction(guard, delay.address, 0, bad, CALL)
      ).to.be.revertedWith(customError("UnexpectedCalldata"));
    });

    it("ignores the Safe-only parameters and the caller", async () => {
      const { guard, delay, stranger } = await setup();

      const withParams = (to: string) =>
        guard
          .connect(stranger)
          .checkTransaction(
            to,
            0,
            setTxNonce(1),
            CALL,
            1,
            2,
            3,
            stranger.address,
            stranger.address,
            "0x1234",
            stranger.address
          );

      await expect(withParams(delay.address)).to.not.be.reverted;
      await expect(withParams(stranger.address)).to.be.revertedWith(
        unexpectedTarget(stranger.address)
      );
    });

    it("checkAfterExecution never reverts", async () => {
      const { guard, stranger } = await setup();

      for (const success of [true, false]) {
        await expect(
          guard
            .connect(stranger)
            .checkAfterExecution(ethers.utils.id("tx"), success)
        ).to.not.be.reverted;
      }
    });

    it("supportsInterface answers for IGuard and IERC165 only", async () => {
      const { guard } = await setup();

      expect(await guard.supportsInterface("0xe6d7a83a")).to.equal(true);
      expect(await guard.supportsInterface("0x01ffc9a7")).to.equal(true);
      expect(await guard.supportsInterface("0xffffffff")).to.equal(false);
      expect(await guard.supportsInterface("0x00000000")).to.equal(false);
    });

    it("delay is the constructor argument", async () => {
      const { guard, delay } = await setup();

      expect(await guard.delay()).to.equal(delay.address);
    });
  });

  /*
   * Random calls checked against a model of checkTransaction: the first of
   * destination, operation, value and calldata that is wrong names the error.
   * The PRNG is seeded, so a failure reproduces.
   */
  describe("against a model of checkTransaction", async () => {
    const expected = (
      delay: string,
      to: string,
      value: BigNumber,
      data: string,
      operation: number
    ) => {
      if (to !== delay) return "UnexpectedTarget";
      if (operation !== CALL) return "UnexpectedOperation";
      if (!value.isZero()) return "UnexpectedValue";
      if (
        ethers.utils.hexDataLength(data) !== 36 ||
        selectorOf(data) !== SET_TX_NONCE
      ) {
        return "UnexpectedCalldata";
      }
      return "ok";
    };

    // mulberry32
    const prng = (seed: number) => () => {
      seed = (seed + 0x6d2b79f5) | 0;
      let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };

    it("agrees on 500 random calls", async function () {
      this.timeout(120000);
      const { guard, delay, stranger } = await setup();

      const random = prng(0x5e7a0ce);
      const pick = <T>(xs: T[]) => xs[Math.floor(random() * xs.length)];
      const randomHex = (bytes: number) =>
        ethers.utils.hexlify(
          Array.from({ length: bytes }, () => Math.floor(random() * 256))
        );

      for (let i = 0; i < 500; i++) {
        const to = pick([
          delay.address,
          delay.address,
          stranger.address,
          AddressZero,
          ethers.utils.getAddress(randomHex(20)),
        ]);
        const value = pick([
          BigNumber.from(0),
          BigNumber.from(0),
          BigNumber.from(1),
          BigNumber.from(randomHex(32)),
        ]);
        const selector = pick([
          SET_TX_NONCE,
          SET_TX_NONCE,
          ...DELAY_OWNER_CALLS.map(selectorOf),
          randomHex(4),
        ]);
        const length = pick([
          0,
          1,
          3,
          4,
          5,
          35,
          36,
          36,
          36,
          37,
          68,
          Math.floor(random() * 100),
        ]);
        const data = ethers.utils.hexDataSlice(
          ethers.utils.hexConcat([selector, randomHex(100)]),
          0,
          length
        );
        const operation = random() < 0.2 ? DELEGATE_CALL : CALL;

        const actual = await checkTransaction(
          guard,
          to,
          value,
          data,
          operation
        ).then(
          () => "ok",
          (e: Error) =>
            /custom error '(\w+)\(/.exec(e.message)?.[1] ?? e.message
        );

        expect(
          actual,
          `case ${i}: to ${to} value ${value} op ${operation} data ${data}`
        ).to.equal(expected(delay.address, to, value, data, operation));
      }
    });
  });

  /*
   * Through the Roles Modifier, as deployed: the Governor (a wallet here) is
   * the Roles Modifier's module and a member of role 1. The Roles Modifier's
   * target is the DelayOwnerSafe (Safe v1.4.1), which has it as a module and
   * owns the Delay; the Delay has four entries queued. Role 1 starts as on
   * chain: setTxNonce on the Delay only, no send, no delegate call. Each
   * rejection is paired with the same call going through without the guard,
   * so the revert is the guard's and not the Roles Modifier's, the Safe's or
   * the Delay's.
   */
  describe("through the Roles Modifier, into the DelayOwnerSafe and the Delay", async () => {
    // v = 1: the owner approves by sending execTransaction itself.
    const preValidatedSignature = (owner: string) =>
      ethers.utils.hexConcat([
        ethers.utils.hexZeroPad(owner, 32),
        HashZero,
        "0x01",
      ]);

    const exec = (safe: Contract, owner: Wallet, to: string, data: string) =>
      safe
        .connect(owner)
        .execTransaction(
          to,
          0,
          data,
          CALL,
          0,
          0,
          0,
          AddressZero,
          AddressZero,
          preValidatedSignature(owner.address)
        );

    const multiSend = (txs: { to: string; data: string }[]) =>
      multiSendAbi.encodeFunctionData("multiSend", [
        ethers.utils.hexConcat(
          txs.map((tx) =>
            ethers.utils.solidityPack(
              ["uint8", "address", "uint256", "uint256", "bytes"],
              [CALL, tx.to, 0, ethers.utils.hexDataLength(tx.data), tx.data]
            )
          )
        ),
      ]);

    const setupUnguarded = deployments.createFixture(async () => {
      const [owner, governor, delayModule, newOwner, stranger] =
        waffle.provider.getWallets();

      const Singleton = await hre.ethers.getContractFactory("Safe");
      const singleton = await Singleton.deploy();
      const proxy = await (
        await hre.ethers.getContractFactory("SafeProxy")
      ).deploy(singleton.address);
      const safe = Singleton.attach(proxy.address);
      await safe.setup(
        [owner.address],
        1,
        AddressZero,
        "0x",
        AddressZero,
        AddressZero,
        0,
        AddressZero
      );

      const testContract = await (
        await hre.ethers.getContractFactory("TestContract")
      ).deploy();
      const multiSendContract = await (
        await hre.ethers.getContractFactory("MultiSend")
      ).deploy();

      const Delay = await hre.ethers.getContractFactory("Delay");
      const delay = await Delay.deploy(
        owner.address,
        stranger.address,
        stranger.address,
        3600,
        0
      );
      await delay.enableModule(delayModule.address);
      for (let i = 0; i < 4; i++) {
        await delay
          .connect(delayModule)
          .execTransactionFromModule(testContract.address, 0, DO_NOTHING, CALL);
      }
      await delay.transferOwnership(safe.address);

      const permissions = await (
        await hre.ethers.getContractFactory("Permissions")
      ).deploy();
      const roles = await (
        await hre.ethers.getContractFactory("Roles", {
          libraries: { Permissions: permissions.address },
        })
      ).deploy(owner.address, safe.address, safe.address);
      await roles.enableModule(governor.address);
      await roles.assignRoles(governor.address, [ROLE], [true]);
      await roles.setDefaultRole(governor.address, ROLE);
      await roles.scopeTarget(ROLE, delay.address);
      await roles.scopeAllowFunction(
        ROLE,
        delay.address,
        SET_TX_NONCE,
        OPTIONS_NONE
      );

      await exec(
        safe,
        owner,
        safe.address,
        safeAbi.encodeFunctionData("enableModule", [roles.address])
      );

      const guard = (await (
        await hre.ethers.getContractFactory("SetTxNonceGuard")
      ).deploy(delay.address)) as SetTxNonceGuard;

      return {
        owner,
        governor,
        delayModule,
        newOwner,
        stranger,
        safe,
        testContract,
        multiSendContract,
        delay,
        roles,
        guard,
      };
    });

    const setupGuarded = deployments.createFixture(async () => {
      const s = await setupUnguarded();
      await s.roles.setGuard(s.guard.address);
      return s;
    });

    type Scene = Awaited<ReturnType<typeof setupUnguarded>>;

    // Role 1 opened up as far as the Roles Modifier allows: every call, with
    // send and delegate call, to the Delay, the Safe and a TestContract.
    const openRole = async (s: Scene) => {
      for (const target of [
        s.delay.address,
        s.safe.address,
        s.testContract.address,
      ]) {
        await s.roles.allowTarget(ROLE, target, OPTIONS_BOTH);
      }
    };

    // The Governor's four ways in. The two WithRole ones revert when the
    // Safe's call fails; the other two return false.
    const ENTRY_POINTS: {
      name: string;
      call: (
        s: Scene,
        to: string,
        data: string,
        value?: BigNumberish,
        operation?: number
      ) => Promise<unknown>;
    }[] = [
      {
        name: "execTransactionFromModule",
        call: (s, to, data, value = 0, operation = CALL) =>
          s.roles
            .connect(s.governor)
            .execTransactionFromModule(to, value, data, operation),
      },
      {
        name: "execTransactionFromModuleReturnData",
        call: (s, to, data, value = 0, operation = CALL) =>
          s.roles
            .connect(s.governor)
            .execTransactionFromModuleReturnData(to, value, data, operation),
      },
      {
        name: "execTransactionWithRole",
        call: (s, to, data, value = 0, operation = CALL) =>
          s.roles
            .connect(s.governor)
            .execTransactionWithRole(to, value, data, operation, ROLE, true),
      },
      {
        name: "execTransactionWithRoleReturnData",
        call: (s, to, data, value = 0, operation = CALL) =>
          s.roles
            .connect(s.governor)
            .execTransactionWithRoleReturnData(
              to,
              value,
              data,
              operation,
              ROLE,
              true
            ),
      },
    ];
    const withRole = ENTRY_POINTS[2];

    const delayState = async (delay: Contract) => ({
      owner: await delay.owner(),
      guard: await delay.guard(),
      avatar: await delay.avatar(),
      target: await delay.target(),
      txCooldown: (await delay.txCooldown()).toString(),
      txExpiration: (await delay.txExpiration()).toString(),
      modules: [...(await delay.getModulesPaginated(SENTINEL, 10))[0]],
    });

    it("the Roles Modifier takes it as its guard", async () => {
      const { roles, guard } = await setupGuarded();

      expect(await roles.getGuard()).to.equal(guard.address);
    });

    for (const entry of ENTRY_POINTS) {
      it(`${entry.name}: the Governor's setTxNonce lands on the Delay`, async () => {
        const s = await setupGuarded();

        await entry.call(s, s.delay.address, setTxNonce(2));

        expect(await s.delay.txNonce()).to.equal(2);
      });
    }

    it("a setTxNonce the Delay refuses passes the guard and changes nothing", async () => {
      const s = await setupGuarded();

      // Not above txNonce (0), and above queueNonce (4).
      for (const nonce of [0, 5]) {
        await expect(
          withRole.call(s, s.delay.address, setTxNonce(nonce))
        ).to.be.revertedWith(customError("ModuleTransactionFailed"));
        expect(
          await s.roles
            .connect(s.governor)
            .callStatic.execTransactionWithRole(
              s.delay.address,
              0,
              setTxNonce(nonce),
              CALL,
              ROLE,
              false
            )
        ).to.equal(false);
      }
      expect(await s.delay.txNonce()).to.equal(0);
    });

    describe("with role 1 as on chain", async () => {
      it("rejects extra calldata behind the nonce, which the role and the Delay accept", async () => {
        const data = ethers.utils.hexConcat([setTxNonce(1), HashZero]);

        const unguarded = await setupUnguarded();
        await withRole.call(unguarded, unguarded.delay.address, data);
        expect(await unguarded.delay.txNonce()).to.equal(1);

        const s = await setupGuarded();
        await expect(
          withRole.call(s, s.delay.address, data)
        ).to.be.revertedWith(customError("UnexpectedCalldata"));
        expect(await s.delay.txNonce()).to.equal(0);
      });

      it("rejects a MultiSend batch holding only a setTxNonce, which the role lets through", async () => {
        const batch = (s: Scene) =>
          multiSend([{ to: s.delay.address, data: setTxNonce(1) }]);

        // The role checks each entry of the batch, not the outer delegate
        // call to MultiSend.
        const unguarded = await setupUnguarded();
        await unguarded.roles.setMultisend(unguarded.multiSendContract.address);
        await withRole.call(
          unguarded,
          unguarded.multiSendContract.address,
          batch(unguarded),
          0,
          DELEGATE_CALL
        );
        expect(await unguarded.delay.txNonce()).to.equal(1);

        const s = await setupGuarded();
        await s.roles.setMultisend(s.multiSendContract.address);
        await expect(
          withRole.call(
            s,
            s.multiSendContract.address,
            batch(s),
            0,
            DELEGATE_CALL
          )
        ).to.be.revertedWith(unexpectedTarget(s.multiSendContract.address));
        expect(await s.delay.txNonce()).to.equal(0);
      });
    });

    describe("with role 1 opened up, the guard alone holds the Governor to setTxNonce", async () => {
      for (const entry of ENTRY_POINTS) {
        it(`${entry.name}: rejects a call to anything but the Delay`, async () => {
          const unguarded = await setupUnguarded();
          await openRole(unguarded);
          await expect(
            entry.call(unguarded, unguarded.testContract.address, DO_NOTHING)
          ).to.emit(unguarded.testContract, "DoNothing");

          const s = await setupGuarded();
          await openRole(s);
          await expect(
            entry.call(s, s.testContract.address, DO_NOTHING)
          ).to.be.revertedWith(unexpectedTarget(s.testContract.address));
        });
      }

      const ownerCalls: { name: string; data: (s: Scene) => string }[] = [
        {
          name: "setTxCooldown(0)",
          data: () => delayAbi.encodeFunctionData("setTxCooldown", [0]),
        },
        {
          name: "setTxExpiration(60)",
          data: () => delayAbi.encodeFunctionData("setTxExpiration", [60]),
        },
        {
          name: "transferOwnership",
          data: (s) =>
            delayAbi.encodeFunctionData("transferOwnership", [
              s.governor.address,
            ]),
        },
        {
          name: "renounceOwnership",
          data: () => delayAbi.encodeFunctionData("renounceOwnership"),
        },
        {
          name: "enableModule",
          data: (s) =>
            delayAbi.encodeFunctionData("enableModule", [s.governor.address]),
        },
        {
          name: "disableModule",
          data: (s) =>
            delayAbi.encodeFunctionData("disableModule", [
              SENTINEL,
              s.delayModule.address,
            ]),
        },
        {
          name: "setGuard",
          data: (s) =>
            delayAbi.encodeFunctionData("setGuard", [s.guard.address]),
        },
        {
          name: "setAvatar",
          data: (s) =>
            delayAbi.encodeFunctionData("setAvatar", [s.governor.address]),
        },
        {
          name: "setTarget",
          data: (s) =>
            delayAbi.encodeFunctionData("setTarget", [s.governor.address]),
        },
      ];

      for (const c of ownerCalls) {
        it(`rejects the Delay's ${c.name}, which changes the Delay without the guard`, async () => {
          const unguarded = await setupUnguarded();
          await openRole(unguarded);
          const unguardedBefore = await delayState(unguarded.delay);
          await withRole.call(
            unguarded,
            unguarded.delay.address,
            c.data(unguarded)
          );
          expect(await delayState(unguarded.delay)).to.not.deep.equal(
            unguardedBefore
          );

          const s = await setupGuarded();
          await openRole(s);
          const before = await delayState(s.delay);
          await expect(
            withRole.call(s, s.delay.address, c.data(s))
          ).to.be.revertedWith(customError("UnexpectedCalldata"));
          expect(await delayState(s.delay)).to.deep.equal(before);
        });
      }

      it("rejects the Safe's own settings, which change without the guard", async () => {
        const data = (s: Scene) =>
          safeAbi.encodeFunctionData("addOwnerWithThreshold", [
            s.newOwner.address,
            1,
          ]);

        // ConfigLockGuard, on the DelayOwnerSafe on chain, never sees the
        // module path, so this guard is what keeps the Governor out.
        const unguarded = await setupUnguarded();
        await openRole(unguarded);
        await withRole.call(unguarded, unguarded.safe.address, data(unguarded));
        expect(await unguarded.safe.getOwners()).to.include(
          unguarded.newOwner.address
        );

        const s = await setupGuarded();
        await openRole(s);
        await expect(
          withRole.call(s, s.safe.address, data(s))
        ).to.be.revertedWith(unexpectedTarget(s.safe.address));
        expect(await s.safe.getOwners()).to.deep.equal([s.owner.address]);
      });

      it("rejects a value with UnexpectedValue, though the role may send", async () => {
        const call = (s: Scene) =>
          s.roles
            .connect(s.governor)
            .execTransactionWithRole(
              s.delay.address,
              1,
              setTxNonce(1),
              CALL,
              ROLE,
              false
            );

        const unguarded = await setupUnguarded();
        await openRole(unguarded);
        await expect(call(unguarded)).to.not.be.reverted;

        const s = await setupGuarded();
        await openRole(s);
        await expect(call(s)).to.be.revertedWith(
          customError("UnexpectedValue")
        );
      });

      it("rejects a delegate call with UnexpectedOperation, though the role may delegate call", async () => {
        const call = (s: Scene) =>
          s.roles
            .connect(s.governor)
            .execTransactionWithRole(
              s.delay.address,
              0,
              setTxNonce(1),
              DELEGATE_CALL,
              ROLE,
              false
            );

        const unguarded = await setupUnguarded();
        await openRole(unguarded);
        await expect(call(unguarded)).to.not.be.reverted;

        const s = await setupGuarded();
        await openRole(s);
        await expect(call(s)).to.be.revertedWith(
          customError("UnexpectedOperation")
        );
      });
    });
  });
});
