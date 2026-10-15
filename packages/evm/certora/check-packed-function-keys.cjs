// Replay permission-key reads in a local EVM using the proof's Solidity compiler
// settings. No RPC, signer, deployment script or Certora credential is used.
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const { createRequire } = require("module");
const { spawnSync } = require("child_process");
const vmRequire = createRequire(require.resolve("@ethereumjs/vm/package.json"));
const VM = vmRequire("@ethereumjs/vm").default;
const Common = vmRequire("@ethereumjs/common").default;
const { Address, BN } = vmRequire("ethereumjs-util");
const { utils } = require("ethers");

const evm = path.resolve(__dirname, "..");
const compiler = process.env.SOLC_BINARY || "solc";
const sha256 = (value) =>
  crypto.createHash("sha256").update(value).digest("hex");
const ensure = (condition, message) => {
  if (!condition) throw new Error(message);
};

(async () => {
  const version = spawnSync(compiler, ["--version"], { encoding: "utf8" });
  ensure(
    version.status === 0 && /Version: 0\.8\.6\+/.test(version.stdout),
    "SOLC_BINARY must select Solidity 0.8.6"
  );
  const builds = [];
  for (const [label, optimizer] of [
    [
      "certora-default",
      { enabled: true, runs: 1, details: { inliner: false } },
    ],
    ["standard-optimizer", { enabled: true, runs: 1 }],
    ["unoptimized", { enabled: false }],
  ]) {
    const input = {
      language: "Solidity",
      sources: {
        "certora/harness/RolesHarness.sol": {
          urls: ["certora/harness/RolesHarness.sol"],
        },
      },
      settings: {
        optimizer,
        evmVersion: "berlin",
        remappings: [
          "@gnosis.pm/=node_modules/@gnosis.pm/",
          "@openzeppelin/=node_modules/@openzeppelin/",
        ],
        outputSelection: {
          "*": { "*": ["abi", "evm.deployedBytecode", "storageLayout"] },
        },
      },
    };
    const compilation = spawnSync(
      compiler,
      [
        "--base-path",
        evm,
        "--allow-paths",
        evm + "," + fs.realpathSync(path.join(evm, "node_modules")),
        "--standard-json",
      ],
      {
        cwd: evm,
        input: JSON.stringify(input),
        encoding: "utf8",
        maxBuffer: 32 * 1024 * 1024,
      }
    );
    ensure(
      compilation.status === 0,
      compilation.stderr || "Solidity compiler failed"
    );
    const compiled = JSON.parse(compilation.stdout);
    const errors = (compiled.errors || []).filter(
      (error) => error.severity === "error"
    );
    ensure(errors.length === 0, JSON.stringify(errors));
    const harness =
      compiled.contracts["certora/harness/RolesHarness.sol"].RolesHarness;
    const permissions =
      compiled.contracts["contracts/Permissions.sol"].Permissions;
    const libraryAddress = "0x0000000000000000000000000000000000000030";
    const harnessAddress = Address.fromString(
      "0x0000000000000000000000000000000000000040"
    );
    let code = harness.evm.deployedBytecode.object;
    for (const libraries of Object.values(
      harness.evm.deployedBytecode.linkReferences
    )) {
      for (const [name, references] of Object.entries(libraries)) {
        ensure(name === "Permissions", "Unexpected linked library: " + name);
        for (const ref of references) {
          ensure(ref.length === 20, "Unexpected link width");
          code =
            code.slice(0, ref.start * 2) +
            libraryAddress.slice(2) +
            code.slice((ref.start + ref.length) * 2);
        }
      }
    }
    ensure(/^[0-9a-f]+$/i.test(code), "Unresolved bytecode links");
    const vm = await VM.create({
      common: new Common({ chain: "mainnet", hardfork: "berlin" }),
    });
    const libraryCode = Buffer.from(
      permissions.evm.deployedBytecode.object,
      "hex"
    );
    const harnessCode = Buffer.from(code, "hex");
    await vm.stateManager.putContractCode(
      Address.fromString(libraryAddress),
      libraryCode
    );
    await vm.stateManager.putContractCode(harnessAddress, harnessCode);
    const abi = new utils.Interface(harness.abi);
    const roles = harness.storageLayout.storage.find(
      (item) => item.label === "roles"
    );
    const roleType =
      harness.storageLayout.types[
        harness.storageLayout.types[roles.type].value
      ];
    const functions = roleType.members.find(
      (item) => item.label === "functions"
    );
    const lengths = [0, 1, 2, 3, 4, 5, 31, 32, 35, 36, 37, 64, 96, 257];
    const targets = [
      "0x" + "00".repeat(20),
      "0x" + "00".repeat(18) + "2546",
      "0x" + "ff".repeat(20),
    ];
    const cases = [];
    for (const length of lengths) {
      for (let pattern = 0; pattern < 4; pattern++) {
        const repeated =
          pattern === 0
            ? "00".repeat(32)
            : pattern === 1
            ? "ff".repeat(32)
            : pattern === 2
            ? "46ba2307" + "00".repeat(28)
            : utils
                .keccak256(utils.toUtf8Bytes("roles-key-" + length))
                .slice(2);
        const data =
          "0x" + repeated.repeat(Math.ceil(length / 32)).slice(0, length * 2);
        const selector = data.slice(2, 10).padEnd(8, "0");
        for (const target of targets) {
          const role = [0, 1, 65535][cases.length % 3];
          const key = target + selector + "00".repeat(8);
          const base = BigInt(
            utils.keccak256(
              utils.defaultAbiCoder.encode(
                ["uint16", "uint256"],
                [role, roles.slot]
              )
            )
          );
          const functionsBase = (base + BigInt(functions.slot)) % (1n << 256n);
          const slot = utils.keccak256(
            utils.defaultAbiCoder.encode(
              ["bytes32", "uint256"],
              [key, functionsBase.toString()]
            )
          );
          const expected = utils.keccak256(
            utils.toUtf8Bytes("scope-value-" + cases.length)
          );
          await vm.stateManager.putContractStorage(
            harnessAddress,
            Buffer.from(slot.slice(2), "hex"),
            Buffer.from(expected.slice(2), "hex")
          );
          for (const [method, arg] of [
            ["functionScopeConfigForData", data],
            [
              "functionScopeConfigForSelector",
              BigInt("0x" + selector).toString(),
            ],
          ]) {
            const result = await vm.runCode({
              code: harnessCode,
              data: Buffer.from(
                abi.encodeFunctionData(method, [role, target, arg]).slice(2),
                "hex"
              ),
              address: harnessAddress,
              gasLimit: new BN("10000000"),
            });
            ensure(
              !result.exceptionError,
              method + ": " + result.exceptionError?.error
            );
            ensure(
              "0x" + result.returnValue.toString("hex") === expected,
              method +
                " read the wrong storage key: " +
                JSON.stringify({ length, pattern, role, target, selector })
            );
          }
          cases.push({
            length,
            pattern,
            role,
            target,
            selector: "0x" + selector,
            key,
            expected,
          });
        }
      }
    }
    const libraryAbi = new utils.Interface(permissions.abi);
    const replayedCalls = [];
    for (const [target, selector] of [
      [targets[0], "0x00000002"],
      [targets[0], "0x000078f1"],
      ["0xfffffffffffffffffffffffffffffffffffff87e", "0x00000000"],
      [targets[0], "0xc0000000"],
      ["0x0000000000000000000000000000000080000000", "0x80000000"],
    ]) {
      const result = await vm.runCode({
        code: libraryCode,
        address: Address.fromString(libraryAddress),
        data: Buffer.from(
          libraryAbi
            .encodeFunctionData("keyForFunctions", [target, selector])
            .slice(2),
          "hex"
        ),
        gasLimit: new BN("10000000"),
      });
      const expected = target + selector.slice(2) + "00".repeat(8);
      ensure(
        !result.exceptionError &&
          "0x" + result.returnValue.toString("hex") === expected,
        "Library-call counterexample replay failed"
      );
      replayedCalls.push({ target, selector, expected });
    }
    const report = {
      label,
      compiler: version.stdout.trim(),
      optimizer,
      evm_version: "berlin",
      sources_sha256: Object.fromEntries(
        Object.keys(compiled.sources).map((name) => [
          name,
          sha256(fs.readFileSync(path.join(evm, name))),
        ])
      ),
      harness_runtime_sha256: sha256(harnessCode),
      permissions_runtime_sha256: sha256(libraryCode),
      getter_cases: cases.length,
      all_getters_match_expected_key: true,
      cases,
      replayed_library_calls: replayedCalls,
    };
    builds.push(report);
    console.log(
      `${label}: both getters passed ${cases.length} storage-key cases; ${replayedCalls.length} library-call counterexamples replayed correctly.`
    );
  }
  if (process.argv[2])
    fs.writeFileSync(
      process.argv[2],
      JSON.stringify({ builds }, null, 2) + "\n"
    );
})().catch((error) => {
  console.error(error.message);
  process.exitCode = 1;
});
