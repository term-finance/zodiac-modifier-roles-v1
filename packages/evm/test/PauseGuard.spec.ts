import { expect } from "chai";
import { Wallet } from "ethers";
import hre, { deployments, waffle, ethers } from "hardhat";

import "@nomiclabs/hardhat-ethers";

import { PauseGuard } from "../typechain-types";

/*
 * PauseGuard as deployed: the Delay Modifier's guard, with admin = the
 * AdminSafe and pauser = the PauseSafe.
 *
 * The Certora specs (specs/PauseGuard/deployment.spec,
 * specs/Delay/pauseGuardSufficient.spec) cover what the constructor sets up
 * and the guard on the real Delay, but with the Delay's target a DummyAvatar
 * and rules that assert only whether a call reverts. These tests check the
 * exact errors and events, that nothing can change the admin, and real block
 * time for cooldowns and expirations across a pause, on the real Delay v1.0.1
 * forwarding to a real GnosisSafe v1.3.0 (the OwnerlessSafe's version,
 * contracts/test/*Imports.sol).
 */

const { AddressZero, HashZero } = ethers.constants;

const CALL = 0;
const DELEGATE_CALL = 1;

const abiOf = (name: string) =>
  new ethers.utils.Interface(hre.artifacts.readArtifactSync(name).abi);

const safeAbi = abiOf("GnosisSafe");
const testContractAbi = abiOf("TestContract");

const DO_NOTHING = testContractAbi.encodeFunctionData("doNothing");

/* hardhat names the guard's custom error, with its arguments, in the revert
 * message. */
const customError = (name: string, ...args: string[]) =>
  `custom error '${name}(${args.map((a) => `"${a}"`).join(", ")})'`;

const notPauser = (caller: string) =>
  customError("NotPauser", ethers.utils.getAddress(caller));

const notAdmin = (caller: string) =>
  customError("NotAdmin", ethers.utils.getAddress(caller));

describe("PauseGuard", async () => {
  const setup = deployments.createFixture(async () => {
    const [deployer, admin, pauser, nextPauser, stranger] =
      waffle.provider.getWallets();

    const Guard = await hre.ethers.getContractFactory("PauseGuard");
    const guard = (await Guard.deploy(
      admin.address,
      pauser.address
    )) as PauseGuard;

    return { Guard, guard, deployer, admin, pauser, nextPauser, stranger };
  });

  const checkTransaction = (guard: PauseGuard, caller: Wallet) =>
    guard
      .connect(caller)
      .checkTransaction(
        AddressZero,
        0,
        "0x",
        CALL,
        0,
        0,
        0,
        AddressZero,
        AddressZero,
        "0x",
        AddressZero
      );

  describe("constructor", async () => {
    it("rejects address(0) for the admin, the pauser or both with ZeroAddress", async () => {
      const { Guard, admin, pauser } = await setup();

      for (const [a, p] of [
        [AddressZero, pauser.address],
        [admin.address, AddressZero],
        [AddressZero, AddressZero],
      ]) {
        await expect(Guard.deploy(a, p)).to.be.revertedWith(
          customError("ZeroAddress")
        );
      }
    });

    it("sets up the admin, the pauser and an unpaused state, and emits PauserSet(0, pauser)", async () => {
      const { guard, admin, pauser } = await setup();

      expect(await guard.admin()).to.equal(admin.address);
      expect(await guard.pauser()).to.equal(pauser.address);
      expect(await guard.paused()).to.equal(false);
      await expect(guard.deployTransaction)
        .to.emit(guard, "PauserSet")
        .withArgs(AddressZero, pauser.address);
    });

    it("the deployer is not the admin and cannot pause, unpause or set the pauser", async () => {
      const { guard, deployer, stranger } = await setup();

      expect(await guard.admin()).to.not.equal(deployer.address);
      await expect(guard.connect(deployer).pause()).to.be.revertedWith(
        notPauser(deployer.address)
      );
      await expect(guard.connect(deployer).unpause()).to.be.revertedWith(
        notAdmin(deployer.address)
      );
      await expect(
        guard.connect(deployer).setPauser(stranger.address)
      ).to.be.revertedWith(notAdmin(deployer.address));
    });

    it("admin and pauser may be one account, which can then pause and unpause", async () => {
      const { Guard, admin } = await setup();
      const guard = (await Guard.deploy(
        admin.address,
        admin.address
      )) as PauseGuard;

      await guard.connect(admin).pause();
      expect(await guard.paused()).to.equal(true);
      await guard.connect(admin).unpause();
      expect(await guard.paused()).to.equal(false);
    });
  });

  describe("pause", async () => {
    it("the pauser pauses, and Paused names it", async () => {
      const { guard, pauser } = await setup();

      await expect(guard.connect(pauser).pause())
        .to.emit(guard, "Paused")
        .withArgs(pauser.address);
      expect(await guard.paused()).to.equal(true);
    });

    it("anyone else gets NotPauser(caller), the admin included", async () => {
      const { guard, deployer, admin, stranger } = await setup();

      for (const caller of [admin, deployer, stranger]) {
        await expect(guard.connect(caller).pause()).to.be.revertedWith(
          notPauser(caller.address)
        );
      }
      expect(await guard.paused()).to.equal(false);
    });

    it("a second pause gets AlreadyPaused", async () => {
      const { guard, pauser } = await setup();

      await guard.connect(pauser).pause();
      await expect(guard.connect(pauser).pause()).to.be.revertedWith(
        customError("AlreadyPaused")
      );
    });

    it("checks the pauser first: anyone else gets NotPauser while paused", async () => {
      const { guard, pauser, stranger } = await setup();

      await guard.connect(pauser).pause();
      await expect(guard.connect(stranger).pause()).to.be.revertedWith(
        notPauser(stranger.address)
      );
    });
  });

  describe("unpause", async () => {
    it("the admin unpauses, and Unpaused names it", async () => {
      const { guard, admin, pauser } = await setup();

      await guard.connect(pauser).pause();
      await expect(guard.connect(admin).unpause())
        .to.emit(guard, "Unpaused")
        .withArgs(admin.address);
      expect(await guard.paused()).to.equal(false);
    });

    it("unpausing when not paused gets NotPaused", async () => {
      const { guard, admin } = await setup();

      await expect(guard.connect(admin).unpause()).to.be.revertedWith(
        customError("NotPaused")
      );
    });

    it("anyone else gets NotAdmin(caller), the pauser included", async () => {
      const { guard, deployer, pauser, stranger } = await setup();

      await guard.connect(pauser).pause();
      for (const caller of [pauser, deployer, stranger]) {
        await expect(guard.connect(caller).unpause()).to.be.revertedWith(
          notAdmin(caller.address)
        );
      }
      expect(await guard.paused()).to.equal(true);
    });

    it("checks the admin first: anyone else gets NotAdmin while not paused", async () => {
      const { guard, stranger } = await setup();

      await expect(guard.connect(stranger).unpause()).to.be.revertedWith(
        notAdmin(stranger.address)
      );
    });
  });

  describe("setPauser", async () => {
    it("the admin replaces the pauser, and PauserSet names both", async () => {
      const { guard, admin, pauser, nextPauser } = await setup();

      await expect(guard.connect(admin).setPauser(nextPauser.address))
        .to.emit(guard, "PauserSet")
        .withArgs(pauser.address, nextPauser.address);
      expect(await guard.pauser()).to.equal(nextPauser.address);

      await expect(guard.connect(pauser).pause()).to.be.revertedWith(
        notPauser(pauser.address)
      );
      await guard.connect(nextPauser).pause();
      expect(await guard.paused()).to.equal(true);
    });

    it("rejects address(0) with ZeroAddress", async () => {
      const { guard, admin, pauser } = await setup();

      await expect(
        guard.connect(admin).setPauser(AddressZero)
      ).to.be.revertedWith(customError("ZeroAddress"));
      expect(await guard.pauser()).to.equal(pauser.address);
    });

    it("anyone else gets NotAdmin(caller), the pauser included", async () => {
      const { guard, deployer, pauser, nextPauser, stranger } = await setup();

      for (const caller of [pauser, deployer, stranger]) {
        await expect(
          guard.connect(caller).setPauser(nextPauser.address)
        ).to.be.revertedWith(notAdmin(caller.address));
      }
      expect(await guard.pauser()).to.equal(pauser.address);
    });

    it("checks the admin first: anyone else gets NotAdmin for address(0) too", async () => {
      const { guard, stranger } = await setup();

      await expect(
        guard.connect(stranger).setPauser(AddressZero)
      ).to.be.revertedWith(notAdmin(stranger.address));
    });

    it("works while paused and leaves the pause in place", async () => {
      const { guard, admin, pauser, nextPauser } = await setup();

      await guard.connect(pauser).pause();
      await guard.connect(admin).setPauser(nextPauser.address);

      expect(await guard.paused()).to.equal(true);
      expect(await guard.pauser()).to.equal(nextPauser.address);
    });

    it("pointed at the admin, gives the admin both powers", async () => {
      const { guard, admin } = await setup();

      await guard.connect(admin).setPauser(admin.address);
      await guard.connect(admin).pause();
      expect(await guard.paused()).to.equal(true);
      await guard.connect(admin).unpause();
      expect(await guard.paused()).to.equal(false);
    });
  });

  describe("a fixed admin", async () => {
    it("has only the guard's own functions", async () => {
      const { guard } = await setup();

      expect(
        guard.interface.fragments
          .filter((f) => f.type === "function")
          .map((f) => f.name)
          .sort()
      ).to.deep.equal([
        "admin",
        "checkAfterExecution",
        "checkTransaction",
        "pause",
        "paused",
        "pauser",
        "setPauser",
        "supportsInterface",
        "unpause",
      ]);
    });

    it("has no AccessControl functions left that could add, move or drop the admin", async () => {
      const { guard, admin, stranger } = await setup();

      const accessControl = new ethers.utils.Interface([
        "function ADMIN_ROLE()",
        "function DEFAULT_ADMIN_ROLE()",
        "function hasRole(bytes32, address)",
        "function getRoleAdmin(bytes32)",
        "function grantRole(bytes32, address)",
        "function revokeRole(bytes32, address)",
        "function renounceRole(bytes32, address)",
      ]);
      const role = ethers.utils.id("ADMIN_ROLE");
      const calls = [
        accessControl.encodeFunctionData("ADMIN_ROLE"),
        accessControl.encodeFunctionData("DEFAULT_ADMIN_ROLE"),
        accessControl.encodeFunctionData("hasRole", [role, admin.address]),
        accessControl.encodeFunctionData("getRoleAdmin", [role]),
        accessControl.encodeFunctionData("grantRole", [role, stranger.address]),
        accessControl.encodeFunctionData("revokeRole", [role, admin.address]),
        accessControl.encodeFunctionData("renounceRole", [role, admin.address]),
      ];

      for (const caller of [admin, stranger]) {
        for (const data of calls) {
          await expect(caller.sendTransaction({ to: guard.address, data })).to
            .be.reverted;
        }
      }
      expect(await guard.admin()).to.equal(admin.address);
    });

    it("supportsInterface answers for IGuard and IERC165 only, no longer IAccessControl", async () => {
      const { guard } = await setup();

      expect(await guard.supportsInterface("0xe6d7a83a")).to.equal(true);
      expect(await guard.supportsInterface("0x01ffc9a7")).to.equal(true);
      expect(await guard.supportsInterface("0x7965db0b")).to.equal(false);
      expect(await guard.supportsInterface("0xffffffff")).to.equal(false);
    });
  });

  describe("the guard functions, called directly", async () => {
    const anyTransaction = (guard: PauseGuard, caller: Wallet) =>
      guard
        .connect(caller)
        .checkTransaction(
          caller.address,
          ethers.utils.parseEther("1"),
          DO_NOTHING,
          DELEGATE_CALL,
          1,
          2,
          3,
          caller.address,
          caller.address,
          "0x1234",
          caller.address
        );

    it("checkTransaction passes any call from anyone while not paused", async () => {
      const { guard, deployer, stranger } = await setup();

      for (const caller of [deployer, stranger]) {
        await expect(checkTransaction(guard, caller)).to.not.be.reverted;
        await expect(anyTransaction(guard, caller)).to.not.be.reverted;
      }
    });

    it("checkTransaction raises ExecutionPaused for any call from anyone while paused", async () => {
      const { guard, deployer, pauser, stranger } = await setup();

      await guard.connect(pauser).pause();
      for (const caller of [deployer, stranger]) {
        await expect(checkTransaction(guard, caller)).to.be.revertedWith(
          customError("ExecutionPaused")
        );
        await expect(anyTransaction(guard, caller)).to.be.revertedWith(
          customError("ExecutionPaused")
        );
      }
    });

    it("checkAfterExecution never reverts, paused or not", async () => {
      const { guard, pauser, stranger } = await setup();

      for (const pause of [false, true]) {
        if (pause) await guard.connect(pauser).pause();
        for (const success of [true, false]) {
          await expect(
            guard
              .connect(stranger)
              .checkAfterExecution(ethers.utils.id("tx"), success)
          ).to.not.be.reverted;
        }
      }
    });
  });

  /*
   * A seeded random sequence of calls checked against a model of PauseGuard's
   * state (paused, pauser, and the admin, which never changes) and of which
   * error each call should raise. A failure reproduces.
   */
  describe("against a model of PauseGuard", async () => {
    // mulberry32
    const prng = (seed: number) => () => {
      seed = (seed + 0x6d2b79f5) | 0;
      let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };

    it("agrees on 300 random calls", async function () {
      this.timeout(120000);
      const { guard, admin, pauser, nextPauser, stranger } = await setup();

      const random = prng(0x9a05e);
      const pick = <T>(xs: T[]) => xs[Math.floor(random() * xs.length)];
      const callers = [admin, pauser, nextPauser, stranger];

      const outcome = (p: Promise<unknown>) =>
        p.then(
          () => "ok",
          (e: Error) =>
            /custom error '(\w+)\(/.exec(e.message)?.[1] ?? e.message
        );

      const model = { paused: false, pauser: pauser.address };

      for (let i = 0; i < 300; i++) {
        const caller = pick(callers);
        const action = pick([
          "pause",
          "pause",
          "unpause",
          "unpause",
          "setPauser",
          "setPauser",
          "checkTransaction",
        ]);
        const account = pick([...callers.map((c) => c.address), AddressZero]);

        let expected: string;
        let actual: string;
        if (action === "pause") {
          expected =
            caller.address !== model.pauser
              ? "NotPauser"
              : model.paused
              ? "AlreadyPaused"
              : "ok";
          actual = await outcome(guard.connect(caller).pause());
          if (expected === "ok") model.paused = true;
        } else if (action === "unpause") {
          expected =
            caller.address !== admin.address
              ? "NotAdmin"
              : !model.paused
              ? "NotPaused"
              : "ok";
          actual = await outcome(guard.connect(caller).unpause());
          if (expected === "ok") model.paused = false;
        } else if (action === "setPauser") {
          expected =
            caller.address !== admin.address
              ? "NotAdmin"
              : account === AddressZero
              ? "ZeroAddress"
              : "ok";
          actual = await outcome(guard.connect(caller).setPauser(account));
          if (expected === "ok") model.pauser = account;
        } else {
          expected = model.paused ? "ExecutionPaused" : "ok";
          actual = await outcome(checkTransaction(guard, caller));
        }

        const at = `step ${i}: ${caller.address} ${action}(${account})`;
        expect(actual, at).to.equal(expected);
        expect(await guard.paused(), at).to.equal(model.paused);
        expect(await guard.pauser(), at).to.equal(model.pauser);
        expect(await guard.admin(), at).to.equal(admin.address);
      }
    });
  });

  /*
   * On the real Delay, as deployed: PauseGuard is the Delay's guard, and the
   * Delay is a module of its target, a GnosisSafe v1.3.0 standing in for the
   * OwnerlessSafe. A wallet stands in for the Delay's owner (the
   * DelayOwnerSafe) and another for the Delay's module (the ProposerSafe).
   * Each queue entry calls a TestContract from the Safe, so an execution shows
   * up as that contract's event.
   */
  describe("on the Delay", async () => {
    const COOLDOWN = 3600;

    // v = 1: the owner approves by sending execTransaction itself.
    const preValidatedSignature = (owner: string) =>
      ethers.utils.hexConcat([
        ethers.utils.hexZeroPad(owner, 32),
        HashZero,
        "0x01",
      ]);

    const increaseTime = async (seconds: number) => {
      await ethers.provider.send("evm_increaseTime", [seconds]);
      await ethers.provider.send("evm_mine", []);
    };

    const setupUnguarded = deployments.createFixture(async () => {
      const [owner, admin, pauser, delayModule, stranger] =
        waffle.provider.getWallets();

      const Singleton = await hre.ethers.getContractFactory("GnosisSafe");
      const singleton = await Singleton.deploy();
      const proxy = await (
        await hre.ethers.getContractFactory("GnosisSafeProxy")
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

      const Delay = await hre.ethers.getContractFactory("Delay");
      const delay = await Delay.deploy(
        owner.address,
        safe.address,
        safe.address,
        COOLDOWN,
        0
      );
      await delay.enableModule(delayModule.address);

      await safe
        .connect(owner)
        .execTransaction(
          safe.address,
          0,
          safeAbi.encodeFunctionData("enableModule", [delay.address]),
          CALL,
          0,
          0,
          0,
          AddressZero,
          AddressZero,
          preValidatedSignature(owner.address)
        );

      const guard = (await (
        await hre.ethers.getContractFactory("PauseGuard")
      ).deploy(admin.address, pauser.address)) as PauseGuard;

      return {
        owner,
        admin,
        pauser,
        delayModule,
        stranger,
        safe,
        testContract,
        delay,
        guard,
      };
    });

    const setupGuarded = deployments.createFixture(async () => {
      const s = await setupUnguarded();
      await s.delay.setGuard(s.guard.address);
      return s;
    });

    type Scene = Awaited<ReturnType<typeof setupUnguarded>>;

    // Entry n calls fnWithSingleParam(n) on the TestContract, so entries can
    // be told apart.
    const entryData = (n: number) =>
      testContractAbi.encodeFunctionData("fnWithSingleParam", [n]);

    const queue = async (s: Scene, ...entries: number[]) => {
      for (const n of entries) {
        await s.delay
          .connect(s.delayModule)
          .execTransactionFromModule(
            s.testContract.address,
            0,
            entryData(n),
            CALL
          );
      }
    };

    const executeNext = (s: Scene, n: number) =>
      s.delay
        .connect(s.stranger)
        .executeNextTx(s.testContract.address, 0, entryData(n), CALL);

    it("the Delay's owner installs it with setGuard", async () => {
      const { delay, guard } = await setupGuarded();

      expect(await delay.guard()).to.equal(guard.address);
    });

    it("not paused: after the cooldown, anyone's executeNextTx goes through", async () => {
      const s = await setupGuarded();
      await queue(s, 0);
      await increaseTime(COOLDOWN);

      await expect(executeNext(s, 0))
        .to.emit(s.testContract, "FnWithSingleParam")
        .withArgs(0);
      expect(await s.delay.txNonce()).to.equal(1);
    });

    it("paused: executeNextTx raises ExecutionPaused and the head entry blocks the rest", async () => {
      const unguarded = await setupUnguarded();
      await queue(unguarded, 0, 1);
      await increaseTime(COOLDOWN);
      await expect(executeNext(unguarded, 0)).to.emit(
        unguarded.testContract,
        "FnWithSingleParam"
      );

      const s = await setupGuarded();
      await queue(s, 0, 1);
      await increaseTime(COOLDOWN);
      await s.guard.connect(s.pauser).pause();

      await expect(executeNext(s, 0)).to.be.revertedWith(
        customError("ExecutionPaused")
      );
      // txNonce stays on entry 0, so entry 1 cannot go first.
      expect(await s.delay.txNonce()).to.equal(0);
      await expect(executeNext(s, 1)).to.be.revertedWith(
        "Transaction hashes do not match"
      );
    });

    it("paused: queueing, the owner's functions and skipExpired stay open", async () => {
      const s = await setupGuarded();
      await s.guard.connect(s.pauser).pause();

      await queue(s, 0, 1);
      expect(await s.delay.queueNonce()).to.equal(2);

      await s.delay.connect(s.owner).setTxNonce(1);
      await s.delay.connect(s.owner).setTxCooldown(60);
      await s.delay.connect(s.owner).setTxExpiration(120);
      await expect(s.delay.connect(s.stranger).skipExpired()).to.not.be
        .reverted;

      expect(await s.delay.txNonce()).to.equal(1);
      expect(await s.delay.txCooldown()).to.equal(60);
      expect(await s.delay.txExpiration()).to.equal(120);
      expect(await s.guard.paused()).to.equal(true);
    });

    it("unpausing makes every ready entry executable at once, by anyone", async () => {
      const s = await setupGuarded();
      await queue(s, 0, 1);
      await s.guard.connect(s.pauser).pause();
      await increaseTime(COOLDOWN);
      await s.guard.connect(s.admin).unpause();

      await expect(executeNext(s, 0))
        .to.emit(s.testContract, "FnWithSingleParam")
        .withArgs(0);
      await expect(executeNext(s, 1))
        .to.emit(s.testContract, "FnWithSingleParam")
        .withArgs(1);
      expect(await s.delay.txNonce()).to.equal(2);
    });

    it("a veto during a pause holds once unpaused: the vetoed entry never runs, the next one does", async () => {
      const s = await setupGuarded();
      await queue(s, 0, 1);
      await increaseTime(COOLDOWN);
      await s.guard.connect(s.pauser).pause();

      await s.delay.connect(s.owner).setTxNonce(1);
      await s.guard.connect(s.admin).unpause();

      await expect(executeNext(s, 0)).to.be.revertedWith(
        "Transaction hashes do not match"
      );
      await expect(executeNext(s, 1))
        .to.emit(s.testContract, "FnWithSingleParam")
        .withArgs(1);
    });

    it("an entry whose expiration passes during a pause never runs", async () => {
      const EXPIRATION = 600;

      // Without a pause, the entry runs inside its window.
      const unguarded = await setupUnguarded();
      await unguarded.delay
        .connect(unguarded.owner)
        .setTxExpiration(EXPIRATION);
      await queue(unguarded, 0);
      await increaseTime(COOLDOWN);
      await expect(executeNext(unguarded, 0)).to.emit(
        unguarded.testContract,
        "FnWithSingleParam"
      );

      const s = await setupGuarded();
      await s.delay.connect(s.owner).setTxExpiration(EXPIRATION);
      await queue(s, 0, 1);
      await s.guard.connect(s.pauser).pause();
      await increaseTime(COOLDOWN + EXPIRATION + 1);
      await s.guard.connect(s.admin).unpause();

      await expect(executeNext(s, 0)).to.be.revertedWith("Transaction expired");
      await s.delay.connect(s.stranger).skipExpired();
      expect(await s.delay.txNonce()).to.equal(2);
      await expect(executeNext(s, 0)).to.be.revertedWith(
        "Transaction queue is empty"
      );
    });
  });
});
