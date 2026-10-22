import { expect } from "chai";
import { BigNumberish, Contract, Wallet } from "ethers";
import hre, { deployments, waffle, ethers } from "hardhat";

import "@nomiclabs/hardhat-ethers";

import { ConfigLockGuard } from "../typechain-types";

/*
 * ConfigLockGuard as deployed: one instance, lockedDelay = the Delay,
 * installed with setGuard on several Safes.
 *
 * The Certora specs (specs/Safe/configLockGuard.spec,
 * specs/SafeV141/configLockGuard.spec, specs/Delay/delayOwnerGuard.spec) prove
 * these properties symbolically, but their rules assert only that the guard
 * reverts, not with which error, and they stub the Safe's signature check.
 * These tests run the real GnosisSafe v1.3.0, Safe v1.4.1 and Delay v1.0.1
 * (contracts/test/*Imports.sol) with real signatures and check the exact
 * error. Every call is encoded from those contracts' own ABIs, never from the
 * guard's ISafeAdmin / IDelay, so a wrong signature in either
 * interface fails here.
 */

const { AddressZero, HashZero } = ethers.constants;

const SENTINEL = "0x0000000000000000000000000000000000000001";
const GUARD_SLOT = ethers.utils.id("guard_manager.guard.address");
const FALLBACK_HANDLER_SLOT = ethers.utils.id(
  "fallback_manager.handler.address"
);

const CALL = 0;
const DELEGATE_CALL = 1;

// Stand-ins for addresses inside calldata the guard only inspects.
const SOMEONE = "0x00000000000000000000000000000000000000aa";
const SOMEONE_ELSE = "0x00000000000000000000000000000000000000bb";

const abiOf = (name: string) =>
  new ethers.utils.Interface(hre.artifacts.readArtifactSync(name).abi);

const safeV130Abi = abiOf("GnosisSafe");
const delayAbi = abiOf("Delay");
const testContractAbi = abiOf("TestContract");
const multiSendAbi = abiOf("MultiSend");

const DO_NOTHING = testContractAbi.encodeFunctionData("doNothing");

/* hardhat names the guard's custom error in the revert message. The quote in
 * front keeps GuardLocked from matching DelayGuardLocked. */
const customError = (name: string) => `custom error '${name}()'`;

const selectorOf = (data: string) => ethers.utils.hexDataSlice(data, 0, 4);

type LockedCall = { name: string; data: string; error: string };

// What the guard blocks when the Safe calls itself.
const SAFE_LOCKED: LockedCall[] = [
  {
    name: "setGuard(other)",
    data: safeV130Abi.encodeFunctionData("setGuard", [SOMEONE]),
    error: "GuardLocked",
  },
  {
    name: "setGuard(0)",
    data: safeV130Abi.encodeFunctionData("setGuard", [AddressZero]),
    error: "GuardLocked",
  },
  {
    name: "enableModule",
    data: safeV130Abi.encodeFunctionData("enableModule", [SOMEONE]),
    error: "ModulesLocked",
  },
  {
    name: "disableModule",
    data: safeV130Abi.encodeFunctionData("disableModule", [SENTINEL, SOMEONE]),
    error: "ModulesLocked",
  },
  {
    name: "setFallbackHandler",
    data: safeV130Abi.encodeFunctionData("setFallbackHandler", [SOMEONE]),
    error: "FallbackHandlerLocked",
  },
];

// What the guard blocks when the Safe calls lockedDelay.
const DELAY_LOCKED: LockedCall[] = [
  {
    name: "transferOwnership",
    data: delayAbi.encodeFunctionData("transferOwnership", [SOMEONE]),
    error: "DelayOwnershipLocked",
  },
  {
    name: "renounceOwnership",
    data: delayAbi.encodeFunctionData("renounceOwnership"),
    error: "DelayOwnershipLocked",
  },
  {
    name: "enableModule",
    data: delayAbi.encodeFunctionData("enableModule", [SOMEONE]),
    error: "DelayModulesLocked",
  },
  {
    name: "disableModule",
    data: delayAbi.encodeFunctionData("disableModule", [SENTINEL, SOMEONE]),
    error: "DelayModulesLocked",
  },
  {
    name: "setGuard(other)",
    data: delayAbi.encodeFunctionData("setGuard", [SOMEONE]),
    error: "DelayGuardLocked",
  },
  {
    name: "setGuard(0)",
    data: delayAbi.encodeFunctionData("setGuard", [AddressZero]),
    error: "DelayGuardLocked",
  },
  {
    name: "setAvatar",
    data: delayAbi.encodeFunctionData("setAvatar", [SOMEONE]),
    error: "DelayAvatarLocked",
  },
  {
    name: "setTarget",
    data: delayAbi.encodeFunctionData("setTarget", [SOMEONE]),
    error: "DelayAvatarLocked",
  },
  {
    name: "setTxCooldown",
    data: delayAbi.encodeFunctionData("setTxCooldown", [0]),
    error: "DelayTimingLocked",
  },
  {
    name: "setTxExpiration",
    data: delayAbi.encodeFunctionData("setTxExpiration", [0]),
    error: "DelayTimingLocked",
  },
];

// Safe settings the guard leaves open.
const SAFE_OPEN = [
  safeV130Abi.encodeFunctionData("addOwnerWithThreshold", [SOMEONE, 1]),
  safeV130Abi.encodeFunctionData("removeOwner", [SENTINEL, SOMEONE, 1]),
  safeV130Abi.encodeFunctionData("swapOwner", [
    SENTINEL,
    SOMEONE,
    SOMEONE_ELSE,
  ]),
  safeV130Abi.encodeFunctionData("changeThreshold", [2]),
  safeV130Abi.encodeFunctionData("approveHash", [HashZero]),
];

// Delay functions the guard leaves open.
const DELAY_OPEN = [
  delayAbi.encodeFunctionData("setTxNonce", [1]),
  delayAbi.encodeFunctionData("executeNextTx", [SOMEONE, 0, "0x", CALL]),
  delayAbi.encodeFunctionData("skipExpired"),
  delayAbi.encodeFunctionData("execTransactionFromModule", [
    SOMEONE,
    0,
    "0x",
    CALL,
  ]),
];

// Delay selectors with no Safe function of the same selector.
const DELAY_ONLY = DELAY_LOCKED.filter(
  (c) => !SAFE_LOCKED.some((s) => selectorOf(s.data) === selectorOf(c.data))
);

const checkTransaction = (
  guard: ConfigLockGuard,
  safe: Wallet,
  to: string,
  data: string,
  operation = CALL
) =>
  guard
    .connect(safe)
    .checkTransaction(
      to,
      0,
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

describe("ConfigLockGuard", async () => {
  const setup = deployments.createFixture(async () => {
    const [safeA, safeB, safeC, delay, stranger] = waffle.provider.getWallets();

    // Called directly, msg.sender plays the Safe and `delay` only needs to be
    // an address: the guard never calls it.
    const Guard = await hre.ethers.getContractFactory("ConfigLockGuard");
    const guard = (await Guard.deploy(delay.address)) as ConfigLockGuard;

    return { Guard, guard, safeA, safeB, safeC, delay, stranger };
  });

  describe("constructor", async () => {
    it("rejects address(0) as the locked Delay", async () => {
      const { Guard } = await setup();

      await expect(Guard.deploy(AddressZero)).to.be.revertedWith(
        customError("InvalidLockedDelay")
      );
    });

    it("accepts any other address, code or not, as lockedDelay", async () => {
      const { Guard, delay } = await setup();
      const testContract = await (
        await hre.ethers.getContractFactory("TestContract")
      ).deploy();

      for (const lockedDelay of [
        SENTINEL,
        delay.address,
        testContract.address,
      ]) {
        const guard = (await Guard.deploy(lockedDelay)) as ConfigLockGuard;
        expect(await guard.lockedDelay()).to.equal(lockedDelay);
      }
    });
  });

  describe("called directly, as the Safe calls it", async () => {
    describe("delegate calls", async () => {
      it("rejects every delegate call, before it looks at the calldata", async () => {
        const { guard, safeA, delay, stranger } = await setup();

        for (const to of [
          safeA.address,
          delay.address,
          stranger.address,
          AddressZero,
        ]) {
          for (const data of ["0x", "0x12", DO_NOTHING, SAFE_LOCKED[0].data]) {
            await expect(
              checkTransaction(guard, safeA, to, data, DELEGATE_CALL)
            ).to.be.revertedWith(customError("UnexpectedOperation"));
          }
        }
      });

      it("rejects an operation outside the enum", async () => {
        const { guard, safeA, stranger } = await setup();

        const data = guard.interface.encodeFunctionData("checkTransaction", [
          stranger.address,
          0,
          "0x",
          2,
          0,
          0,
          0,
          AddressZero,
          AddressZero,
          "0x",
          AddressZero,
        ]);

        await expect(safeA.call({ to: guard.address, data })).to.be.reverted;
      });
    });

    describe("calldata shorter than a selector", async () => {
      it("passes 0 to 3 bytes, even a prefix of a locked selector", async () => {
        const { guard, safeA, delay } = await setup();

        for (let length = 0; length < 4; length++) {
          await expect(
            checkTransaction(
              guard,
              safeA,
              safeA.address,
              ethers.utils.hexDataSlice(SAFE_LOCKED[0].data, 0, length)
            )
          ).to.not.be.reverted;
          await expect(
            checkTransaction(
              guard,
              safeA,
              delay.address,
              ethers.utils.hexDataSlice(DELAY_LOCKED[0].data, 0, length)
            )
          ).to.not.be.reverted;
        }
      });
    });

    describe("calls to the Safe itself", async () => {
      for (const c of SAFE_LOCKED) {
        it(`rejects ${c.name} with ${c.error}`, async () => {
          const { guard, safeA } = await setup();

          await expect(
            checkTransaction(guard, safeA, safeA.address, c.data)
          ).to.be.revertedWith(customError(c.error));
        });
      }

      it("rejects the bare selector, and extra bytes after the arguments", async () => {
        const { guard, safeA } = await setup();

        for (const c of SAFE_LOCKED) {
          for (const data of [
            selectorOf(c.data),
            ethers.utils.hexConcat([c.data, "0xdeadbeef"]),
          ]) {
            await expect(
              checkTransaction(guard, safeA, safeA.address, data)
            ).to.be.revertedWith(customError(c.error));
          }
        }
      });

      it("ignores value and the gas, refund and signature parameters", async () => {
        const { guard, safeA, stranger } = await setup();

        const withParams = (data: string) =>
          guard
            .connect(safeA)
            .checkTransaction(
              safeA.address,
              ethers.utils.parseEther("1"),
              data,
              CALL,
              1,
              2,
              3,
              stranger.address,
              stranger.address,
              "0x1234",
              stranger.address
            );

        await expect(withParams(SAFE_LOCKED[0].data)).to.be.revertedWith(
          customError("GuardLocked")
        );
        await expect(withParams(SAFE_OPEN[0])).to.not.be.reverted;
      });

      it("lets owner and threshold management through", async () => {
        const { guard, safeA } = await setup();

        for (const data of SAFE_OPEN) {
          await expect(checkTransaction(guard, safeA, safeA.address, data)).to
            .not.be.reverted;
        }
      });
    });

    describe("calls to the locked Delay", async () => {
      for (const c of DELAY_LOCKED) {
        it(`rejects ${c.name} with ${c.error}`, async () => {
          const { guard, safeA, delay } = await setup();

          await expect(
            checkTransaction(guard, safeA, delay.address, c.data)
          ).to.be.revertedWith(customError(c.error));
        });
      }

      it("rejects the bare selector, and extra bytes after the arguments", async () => {
        const { guard, safeA, delay } = await setup();

        for (const c of DELAY_LOCKED) {
          for (const data of [
            selectorOf(c.data),
            ethers.utils.hexConcat([c.data, "0xdeadbeef"]),
          ]) {
            await expect(
              checkTransaction(guard, safeA, delay.address, data)
            ).to.be.revertedWith(customError(c.error));
          }
        }
      });

      it("lets the Delay's other functions through", async () => {
        const { guard, safeA, delay } = await setup();

        for (const data of DELAY_OPEN) {
          await expect(checkTransaction(guard, safeA, delay.address, data)).to
            .not.be.reverted;
        }
      });

      it("names the destination in the error when the Safe and the Delay share a selector", async () => {
        const { guard, safeA, delay } = await setup();

        const shared: [string, string, string][] = [
          ["setGuard", "GuardLocked", "DelayGuardLocked"],
          ["enableModule", "ModulesLocked", "DelayModulesLocked"],
          ["disableModule", "ModulesLocked", "DelayModulesLocked"],
        ];
        for (const [fn, onSafe, onDelay] of shared) {
          const data = delayAbi.encodeFunctionData(
            fn,
            fn === "disableModule" ? [SENTINEL, SOMEONE] : [SOMEONE]
          );
          expect(selectorOf(data)).to.equal(safeV130Abi.getSighash(fn));

          await expect(
            checkTransaction(guard, safeA, safeA.address, data)
          ).to.be.revertedWith(customError(onSafe));
          await expect(
            checkTransaction(guard, safeA, delay.address, data)
          ).to.be.revertedWith(customError(onDelay));
        }
      });

      it("ignores a selector that only the other contract locks", async () => {
        const { guard, safeA, delay } = await setup();

        for (const c of DELAY_ONLY) {
          await expect(checkTransaction(guard, safeA, safeA.address, c.data)).to
            .not.be.reverted;
        }
        await expect(
          checkTransaction(
            guard,
            safeA,
            delay.address,
            safeV130Abi.encodeFunctionData("setFallbackHandler", [SOMEONE])
          )
        ).to.not.be.reverted;
      });
    });

    describe("calls anywhere else", async () => {
      it("lets every locked selector through to any other address", async () => {
        const { guard, safeA, safeB, stranger } = await setup();

        for (const to of [stranger.address, safeB.address, AddressZero]) {
          for (const c of [...SAFE_LOCKED, ...DELAY_LOCKED]) {
            await expect(checkTransaction(guard, safeA, to, c.data)).to.not.be
              .reverted;
          }
        }
      });
    });

    describe("one instance on several Safes, as deployed", async () => {
      it("locks each Safe's own settings, judged by msg.sender", async () => {
        const { guard, safeA, safeB, safeC } = await setup();
        const safes = [safeA, safeB, safeC];

        for (const safe of safes) {
          for (const c of SAFE_LOCKED) {
            await expect(
              checkTransaction(guard, safe, safe.address, c.data)
            ).to.be.revertedWith(customError(c.error));

            for (const otherSafe of safes.filter((s) => s !== safe)) {
              await expect(
                checkTransaction(guard, safe, otherSafe.address, c.data)
              ).to.not.be.reverted;
            }
          }
        }
      });

      it("locks the Delay against every Safe it is installed on", async () => {
        const { guard, safeA, safeB, safeC, delay } = await setup();

        for (const safe of [safeA, safeB, safeC]) {
          for (const c of DELAY_LOCKED) {
            await expect(
              checkTransaction(guard, safe, delay.address, c.data)
            ).to.be.revertedWith(customError(c.error));
          }
        }
      });
    });

    describe("unusual lockedDelay values", async () => {
      it("the Safe itself: the Safe's own branch wins for that Safe", async () => {
        const { Guard, safeA, safeB } = await setup();
        const guard = (await Guard.deploy(safeA.address)) as ConfigLockGuard;

        // safeA calling itself: only the Safe's four are locked.
        for (const c of SAFE_LOCKED) {
          await expect(
            checkTransaction(guard, safeA, safeA.address, c.data)
          ).to.be.revertedWith(customError(c.error));
        }
        for (const c of DELAY_ONLY) {
          await expect(checkTransaction(guard, safeA, safeA.address, c.data)).to
            .not.be.reverted;
        }

        // Any other Safe calling safeA: the Delay list applies.
        for (const c of DELAY_LOCKED) {
          await expect(
            checkTransaction(guard, safeB, safeA.address, c.data)
          ).to.be.revertedWith(customError(c.error));
        }
      });
    });

    describe("the rest of the interface", async () => {
      it("checkAfterExecution never reverts", async () => {
        const { guard, safeA, stranger } = await setup();

        for (const caller of [safeA, stranger]) {
          for (const success of [true, false]) {
            await expect(
              guard
                .connect(caller)
                .checkAfterExecution(ethers.utils.id("tx"), success)
            ).to.not.be.reverted;
          }
        }
      });

      it("supportsInterface answers for IGuard and IERC165 only", async () => {
        const { guard } = await setup();

        expect(await guard.supportsInterface("0xe6d7a83a")).to.equal(true);
        expect(await guard.supportsInterface("0x01ffc9a7")).to.equal(true);
        expect(await guard.supportsInterface("0xffffffff")).to.equal(false);
        expect(await guard.supportsInterface("0x00000000")).to.equal(false);
      });
    });
  });

  /*
   * Random calls checked against a model of the decision table in
   * checkTransaction. The PRNG is seeded, so a failure reproduces.
   */
  describe("against a model of checkTransaction", async () => {
    const SAFE_ERRORS = Object.fromEntries(
      SAFE_LOCKED.map((c) => [selectorOf(c.data), c.error])
    );
    const DELAY_ERRORS = Object.fromEntries(
      DELAY_LOCKED.map((c) => [selectorOf(c.data), c.error])
    );

    const expected = (
      sender: string,
      to: string,
      lockedDelay: string,
      data: string,
      operation: number
    ) => {
      if (operation !== CALL) return "UnexpectedOperation";
      if (ethers.utils.hexDataLength(data) < 4) return "ok";
      const selector = selectorOf(data);
      if (to === sender) return SAFE_ERRORS[selector] ?? "ok";
      if (to === lockedDelay) return DELAY_ERRORS[selector] ?? "ok";
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
      const { Guard, guard, safeA, safeB, delay } = await setup();
      // Locked to safeB: safeB calling itself takes the Safe branch, safeA
      // calling safeB takes the Delay branch.
      const guardOnSafeB = (await Guard.deploy(
        safeB.address
      )) as ConfigLockGuard;

      const random = prng(0xc0ff1e);
      const pick = <T>(xs: T[]) => xs[Math.floor(random() * xs.length)];
      const randomHex = (bytes: number) =>
        ethers.utils.hexlify(
          Array.from({ length: bytes }, () => Math.floor(random() * 256))
        );

      const selectors = [...SAFE_LOCKED, ...DELAY_LOCKED].map((c) =>
        selectorOf(c.data)
      );
      const openSelectors = [...SAFE_OPEN, ...DELAY_OPEN, DO_NOTHING].map(
        selectorOf
      );

      for (let i = 0; i < 500; i++) {
        const g = pick([guard, guardOnSafeB]);
        const lockedDelay = await g.lockedDelay();
        const sender = pick([safeA, safeB]);
        const to = pick([
          sender.address,
          delay.address,
          sender === safeA ? safeB.address : safeA.address,
          AddressZero,
          ethers.utils.getAddress(randomHex(20)),
        ]);
        const selector = pick([...selectors, ...openSelectors, randomHex(4)]);
        const length = pick([
          0,
          1,
          2,
          3,
          4,
          5,
          36,
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
          g,
          sender,
          to,
          data,
          operation
        ).then(
          () => "ok",
          (e: Error) =>
            /custom error '(\w+)\(\)'/.exec(e.message)?.[1] ?? e.message
        );

        expect(
          actual,
          `case ${i}: ${sender.address} -> ${to} (lockedDelay ${lockedDelay}) op ${operation} data ${data}`
        ).to.equal(expected(sender.address, to, lockedDelay, data, operation));
      }
    });
  });

  /*
   * End to end: the owners sign execTransaction on a real Safe, which calls the
   * guard. The Safe owns a real Delay set up as on chain (PauseGuard installed,
   * one module, one queued entry) and has a module enabled before the guard
   * went on. Each rejection is paired with the same call going through on the
   * same Safe without the guard, so the revert is the guard's and not the
   * Safe's or the Delay's.
   */
  const SAFE_VERSIONS = [
    {
      name: "GnosisSafe v1.3.0",
      singleton: "GnosisSafe",
      proxy: "GnosisSafeProxy",
    },
    { name: "Safe v1.4.1", singleton: "Safe", proxy: "SafeProxy" },
  ];

  // v = 1: the owner approves by sending execTransaction itself.
  const preValidatedSignature = (owner: string) =>
    ethers.utils.hexConcat([
      ethers.utils.hexZeroPad(owner, 32),
      HashZero,
      "0x01",
    ]);

  const exec = (
    safe: Contract,
    owner: Wallet,
    to: string,
    data: string,
    operation = CALL,
    value: BigNumberish = 0
  ) =>
    safe
      .connect(owner)
      .execTransaction(
        to,
        value,
        data,
        operation,
        0,
        0,
        0,
        AddressZero,
        AddressZero,
        preValidatedSignature(owner.address)
      );

  const multiSend = (
    txs: {
      operation?: number;
      to: string;
      value?: BigNumberish;
      data: string;
    }[]
  ) =>
    multiSendAbi.encodeFunctionData("multiSend", [
      ethers.utils.hexConcat(
        txs.map((tx) =>
          ethers.utils.solidityPack(
            ["uint8", "address", "uint256", "uint256", "bytes"],
            [
              tx.operation ?? CALL,
              tx.to,
              tx.value ?? 0,
              ethers.utils.hexDataLength(tx.data),
              tx.data,
            ]
          )
        )
      ),
    ]);

  const addressAt = async (account: string, slot: string) =>
    ethers.utils.getAddress(
      ethers.utils.hexDataSlice(
        await ethers.provider.getStorageAt(account, slot),
        12
      )
    );

  const safeState = async (safe: Contract) => ({
    nonce: (await safe.nonce()).toString(),
    guard: await addressAt(safe.address, GUARD_SLOT),
    fallbackHandler: await addressAt(safe.address, FALLBACK_HANDLER_SLOT),
    modules: [...(await safe.getModulesPaginated(SENTINEL, 10))[0]],
    owners: [...(await safe.getOwners())],
    threshold: (await safe.getThreshold()).toString(),
  });

  const delayState = async (delay: Contract) => ({
    owner: await delay.owner(),
    guard: await delay.guard(),
    avatar: await delay.avatar(),
    target: await delay.target(),
    modules: [...(await delay.getModulesPaginated(SENTINEL, 10))[0]],
    txCooldown: (await delay.txCooldown()).toString(),
    txExpiration: (await delay.txExpiration()).toString(),
  });

  for (const version of SAFE_VERSIONS) {
    describe(`end to end on ${version.name}`, async () => {
      const safeAbi = abiOf(version.singleton);

      const setupUnguarded = deployments.createFixture(async () => {
        const [owner, module, handler, newOwner, stranger, delayModule] =
          waffle.provider.getWallets();

        const Singleton = await hre.ethers.getContractFactory(
          version.singleton
        );
        const singleton = await Singleton.deploy();
        const Proxy = await hre.ethers.getContractFactory(version.proxy);
        const proxy = await Proxy.deploy(singleton.address);
        const safe = Singleton.attach(proxy.address);
        await safe.setup(
          [owner.address],
          1,
          AddressZero,
          "0x",
          handler.address,
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
        const multiSendCallOnly = await (
          await hre.ethers.getContractFactory("MultiSendCallOnly")
        ).deploy();

        // The Delay as on chain: PauseGuard installed, one module, one entry
        // queued, owned by the Safe.
        const pauseGuard = await (
          await hre.ethers.getContractFactory("PauseGuard")
        ).deploy(owner.address, owner.address);
        const Delay = await hre.ethers.getContractFactory("Delay");
        const delay = await Delay.deploy(
          owner.address,
          stranger.address,
          stranger.address,
          3600,
          0
        );
        await delay.enableModule(delayModule.address);
        await delay.setGuard(pauseGuard.address);
        await delay
          .connect(delayModule)
          .execTransactionFromModule(testContract.address, 0, DO_NOTHING, CALL);
        await delay.transferOwnership(safe.address);

        const Guard = await hre.ethers.getContractFactory("ConfigLockGuard");
        const guard = (await Guard.deploy(delay.address)) as ConfigLockGuard;
        const otherGuard = (await Guard.deploy(
          stranger.address
        )) as ConfigLockGuard;

        // A module enabled before the guard goes on.
        await exec(
          safe,
          owner,
          safe.address,
          safeAbi.encodeFunctionData("enableModule", [module.address])
        );

        return {
          safe,
          owner,
          module,
          handler,
          newOwner,
          stranger,
          delayModule,
          testContract,
          multiSendContract,
          multiSendCallOnly,
          pauseGuard,
          Delay,
          delay,
          guard,
          otherGuard,
        };
      });

      const setupGuarded = deployments.createFixture(async () => {
        const s = await setupUnguarded();
        await exec(
          s.safe,
          s.owner,
          s.safe.address,
          safeAbi.encodeFunctionData("setGuard", [s.guard.address])
        );
        return s;
      });

      type Scene = Awaited<ReturnType<typeof setupUnguarded>>;

      it("the owners' setGuard installs it", async () => {
        const { safe, owner, guard } = await setupUnguarded();
        expect(await addressAt(safe.address, GUARD_SLOT)).to.equal(AddressZero);

        await exec(
          safe,
          owner,
          safe.address,
          safeAbi.encodeFunctionData("setGuard", [guard.address])
        );

        expect(await addressAt(safe.address, GUARD_SLOT)).to.equal(
          guard.address
        );
      });

      describe("the Safe's own settings", async () => {
        const cases: {
          name: string;
          error: string;
          data: (s: Scene) => string;
        }[] = [
          {
            name: "setGuard(0)",
            error: "GuardLocked",
            data: () => safeAbi.encodeFunctionData("setGuard", [AddressZero]),
          },
          {
            name: "setGuard(another guard)",
            error: "GuardLocked",
            data: (s) =>
              safeAbi.encodeFunctionData("setGuard", [s.otherGuard.address]),
          },
          {
            name: "enableModule",
            error: "ModulesLocked",
            data: (s) =>
              safeAbi.encodeFunctionData("enableModule", [s.stranger.address]),
          },
          {
            name: "disableModule",
            error: "ModulesLocked",
            data: (s) =>
              safeAbi.encodeFunctionData("disableModule", [
                SENTINEL,
                s.module.address,
              ]),
          },
          {
            name: "setFallbackHandler",
            error: "FallbackHandlerLocked",
            data: (s) =>
              safeAbi.encodeFunctionData("setFallbackHandler", [
                s.stranger.address,
              ]),
          },
        ];

        for (const c of cases) {
          it(`rejects ${c.name} with ${c.error} and changes nothing`, async () => {
            const unguarded = await setupUnguarded();
            await expect(
              exec(
                unguarded.safe,
                unguarded.owner,
                unguarded.safe.address,
                c.data(unguarded)
              )
            ).to.not.be.reverted;

            const s = await setupGuarded();
            const before = await safeState(s.safe);
            await expect(
              exec(s.safe, s.owner, s.safe.address, c.data(s))
            ).to.be.revertedWith(customError(c.error));
            expect(await safeState(s.safe)).to.deep.equal(before);
          });
        }
      });

      describe("delegate calls", async () => {
        it("rejects a MultiSend batch that would remove the guard", async () => {
          // Without the guard, a delegate-called batch rewrites the Safe's
          // settings: its calls to the Safe come from the Safe itself.
          const unguarded = await setupUnguarded();
          await exec(
            unguarded.safe,
            unguarded.owner,
            unguarded.multiSendContract.address,
            multiSend([
              {
                to: unguarded.safe.address,
                data: safeAbi.encodeFunctionData("setFallbackHandler", [
                  unguarded.stranger.address,
                ]),
              },
            ]),
            DELEGATE_CALL
          );
          expect(
            await addressAt(unguarded.safe.address, FALLBACK_HANDLER_SLOT)
          ).to.equal(unguarded.stranger.address);

          const s = await setupGuarded();
          const before = await safeState(s.safe);
          await expect(
            exec(
              s.safe,
              s.owner,
              s.multiSendContract.address,
              multiSend([
                {
                  to: s.safe.address,
                  data: safeAbi.encodeFunctionData("setGuard", [AddressZero]),
                },
              ]),
              DELEGATE_CALL
            )
          ).to.be.revertedWith(customError("UnexpectedOperation"));
          expect(await safeState(s.safe)).to.deep.equal(before);
        });

        it("rejects a harmless batch too, so the owners cannot batch through MultiSendCallOnly", async () => {
          const s = await setupGuarded();

          await expect(
            exec(
              s.safe,
              s.owner,
              s.multiSendCallOnly.address,
              multiSend([{ to: s.testContract.address, data: DO_NOTHING }]),
              DELEGATE_CALL
            )
          ).to.be.revertedWith(customError("UnexpectedOperation"));
        });
      });

      it("a plain call to MultiSendCallOnly passes the guard but cannot reach the Safe's settings", async () => {
        const s = await setupGuarded();
        const before = await safeState(s.safe);

        // The guard lets it through (to is MultiSendCallOnly), the Safe's own
        // `authorized` check rejects the inner call (GS031), so execTransaction
        // fails with GS013.
        await expect(
          exec(
            s.safe,
            s.owner,
            s.multiSendCallOnly.address,
            multiSend([
              {
                to: s.safe.address,
                data: safeAbi.encodeFunctionData("setGuard", [AddressZero]),
              },
            ]),
            CALL
          )
        ).to.be.revertedWith("GS013");
        expect(await safeState(s.safe)).to.deep.equal(before);
      });

      describe("what still works", async () => {
        it("plain calls out: ETH and contract calls", async () => {
          const s = await setupGuarded();
          await s.owner.sendTransaction({
            to: s.safe.address,
            value: ethers.utils.parseEther("1"),
          });

          const balance = await ethers.provider.getBalance(s.stranger.address);
          await exec(
            s.safe,
            s.owner,
            s.stranger.address,
            "0x",
            CALL,
            ethers.utils.parseEther("0.25")
          );
          expect(await ethers.provider.getBalance(s.stranger.address)).to.equal(
            balance.add(ethers.utils.parseEther("0.25"))
          );

          await expect(
            exec(s.safe, s.owner, s.testContract.address, DO_NOTHING)
          ).to.emit(s.testContract, "DoNothing");
        });

        it("owner and threshold management", async () => {
          const s = await setupGuarded();
          const self = s.safe.address;
          const call = (fn: string, args: unknown[]) =>
            exec(s.safe, s.owner, self, safeAbi.encodeFunctionData(fn, args));

          await call("addOwnerWithThreshold", [s.newOwner.address, 1]);
          await call("swapOwner", [
            SENTINEL,
            s.newOwner.address,
            s.stranger.address,
          ]);
          await call("removeOwner", [SENTINEL, s.stranger.address, 1]);
          await call("addOwnerWithThreshold", [s.newOwner.address, 1]);
          await call("changeThreshold", [2]);

          expect(await s.safe.getOwners()).to.deep.equal([
            s.newOwner.address,
            s.owner.address,
          ]);
          expect(await s.safe.getThreshold()).to.equal(2);
          expect(await addressAt(self, GUARD_SLOT)).to.equal(s.guard.address);
        });
      });

      describe("the module path, which never reaches the guard", async () => {
        it("a module enabled before the guard can still remove it", async () => {
          const s = await setupGuarded();

          await s.safe
            .connect(s.module)
            .execTransactionFromModule(
              s.safe.address,
              0,
              safeAbi.encodeFunctionData("setGuard", [AddressZero]),
              CALL
            );

          expect(await addressAt(s.safe.address, GUARD_SLOT)).to.equal(
            AddressZero
          );
        });

        it("and can still delegate call", async () => {
          const s = await setupGuarded();

          await expect(
            s.safe
              .connect(s.module)
              .execTransactionFromModule(
                s.multiSendCallOnly.address,
                0,
                multiSend([{ to: s.testContract.address, data: DO_NOTHING }]),
                DELEGATE_CALL
              )
          ).to.emit(s.testContract, "DoNothing");
        });
      });

      describe("the locked Delay", async () => {
        const cases: {
          name: string;
          error: string;
          data: (s: Scene) => string;
        }[] = [
          {
            name: "transferOwnership",
            error: "DelayOwnershipLocked",
            data: (s) =>
              delayAbi.encodeFunctionData("transferOwnership", [
                s.stranger.address,
              ]),
          },
          {
            name: "renounceOwnership",
            error: "DelayOwnershipLocked",
            data: () => delayAbi.encodeFunctionData("renounceOwnership"),
          },
          {
            name: "enableModule",
            error: "DelayModulesLocked",
            data: (s) =>
              delayAbi.encodeFunctionData("enableModule", [s.stranger.address]),
          },
          {
            name: "disableModule",
            error: "DelayModulesLocked",
            data: (s) =>
              delayAbi.encodeFunctionData("disableModule", [
                SENTINEL,
                s.delayModule.address,
              ]),
          },
          {
            name: "setGuard(0), removing PauseGuard",
            error: "DelayGuardLocked",
            data: () => delayAbi.encodeFunctionData("setGuard", [AddressZero]),
          },
          {
            name: "setGuard(another guard)",
            error: "DelayGuardLocked",
            data: (s) =>
              delayAbi.encodeFunctionData("setGuard", [s.otherGuard.address]),
          },
          {
            name: "setAvatar",
            error: "DelayAvatarLocked",
            data: (s) =>
              delayAbi.encodeFunctionData("setAvatar", [s.newOwner.address]),
          },
          {
            name: "setTarget",
            error: "DelayAvatarLocked",
            data: (s) =>
              delayAbi.encodeFunctionData("setTarget", [s.newOwner.address]),
          },
          {
            name: "setTxCooldown(0), skipping the veto window",
            error: "DelayTimingLocked",
            data: () => delayAbi.encodeFunctionData("setTxCooldown", [0]),
          },
          {
            name: "setTxExpiration",
            error: "DelayTimingLocked",
            data: () => delayAbi.encodeFunctionData("setTxExpiration", [120]),
          },
        ];

        for (const c of cases) {
          it(`rejects ${c.name} with ${c.error} and leaves the Delay as it was`, async () => {
            const unguarded = await setupUnguarded();
            const unguardedBefore = await delayState(unguarded.delay);
            await exec(
              unguarded.safe,
              unguarded.owner,
              unguarded.delay.address,
              c.data(unguarded)
            );
            expect(await delayState(unguarded.delay)).to.not.deep.equal(
              unguardedBefore
            );

            const s = await setupGuarded();
            const before = await delayState(s.delay);
            const safeBefore = await safeState(s.safe);
            await expect(
              exec(s.safe, s.owner, s.delay.address, c.data(s))
            ).to.be.revertedWith(customError(c.error));
            expect(await delayState(s.delay)).to.deep.equal(before);
            expect(await safeState(s.safe)).to.deep.equal(safeBefore);
          });
        }

        it("the owners can still veto", async () => {
          const s = await setupGuarded();

          await exec(
            s.safe,
            s.owner,
            s.delay.address,
            delayAbi.encodeFunctionData("setTxNonce", [1])
          );

          expect(await s.delay.txNonce()).to.equal(1);
        });

        it("a second Delay owned by the same Safe is not locked", async () => {
          const s = await setupGuarded();
          const secondDelay = await s.Delay.deploy(
            s.safe.address,
            s.stranger.address,
            s.stranger.address,
            0,
            0
          );

          await exec(
            s.safe,
            s.owner,
            secondDelay.address,
            delayAbi.encodeFunctionData("transferOwnership", [
              s.stranger.address,
            ])
          );

          expect(await secondDelay.owner()).to.equal(s.stranger.address);
        });
      });
    });
  }
});
