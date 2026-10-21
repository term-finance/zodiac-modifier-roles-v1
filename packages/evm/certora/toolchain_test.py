"""Guard the CLI/compiler routing used by CI and the local proof runner."""

from pathlib import Path
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import pull_guards
import toolchain


GIT = ["git", "-c", "user.name=test", "-c", "user.email=test@example.com", "-c", "commit.gpgsign=false"]


class ToolchainTests(unittest.TestCase):
    def test_every_configuration_has_the_expected_pin_and_compiler(self):
        self.assertEqual(set(toolchain.CERTORA_8_CONFIGS), set(toolchain.RELEASES))
        for release in toolchain.RELEASES:
            configs = list((toolchain.CERTORA_DIR / release / "confs").glob("*.conf"))
            self.assertTrue(configs)
            self.assertTrue(toolchain.CERTORA_8_CONFIGS[release] <= {p.name for p in configs})
            for config in configs:
                with self.subTest(release=release, config=config.name):
                    selected = toolchain.toolchain(f"{release}/{config.name}")
                    migrated = config.name in toolchain.CERTORA_8_CONFIGS[release]
                    self.assertEqual(selected["release"], release)
                    self.assertEqual(selected["version"], "8.19.2" if migrated else "7.31.0")
                    self.assertEqual(Path(selected["requirements"]).name,
                                     "requirements-8.txt" if migrated else "requirements.txt")
                    self.assertEqual(selected["solc_version"],
                                     "0.7.6" if config.name.startswith("Safe-") else "0.8.6")
                    self.assertEqual(selected, toolchain.toolchain(config))

    def test_unknown_and_outside_configurations_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            outside = Path(directory) / "Safe-receive.conf"
            outside.write_text("{}\n")
            for invalid in ("missing.conf", "Safe-receive.conf", "2.0.0/missing.conf", "9.9.9/Safe-receive.conf",
                            "../Safe-receive.conf", outside, toolchain.CERTORA_DIR / "toolchain.py"):
                with self.subTest(config=str(invalid)), self.assertRaises(ValueError):
                    toolchain.toolchain(invalid)

    def test_new_configs_remain_on_legacy_and_malformed_pins_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            certora = root / "certora"
            (certora / "2.0.0/confs").mkdir(parents=True)
            (certora / "2.0.0/confs/New.conf").write_text("{}\n")
            (certora / "2.0.0/confs/Safe-receive.conf").write_text("{}\n")
            legacy = root / "requirements.txt"
            upgraded = root / "requirements-8.txt"
            legacy.write_text("certora-cli==7.31.0\n")
            upgraded.write_text("certora-cli==8.19.2\n")
            with patch.object(toolchain, "CERTORA_DIR", certora):
                self.assertEqual(toolchain.toolchain("2.0.0/New.conf")["version"], "7.31.0")
                for path, name in ((legacy, "2.0.0/New.conf"), (upgraded, "2.0.0/Safe-receive.conf")):
                    for invalid in ("certora-cli>=8\n", "", "certora-cli==7.31.0\ncertora-cli==8.19.2\n"):
                        path.write_text(invalid)
                        with self.subTest(config=name, pin=invalid), self.assertRaises(ValueError):
                            toolchain.toolchain(name)

    def test_local_runner_checks_version_and_preserves_compiler_and_arguments(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            certora = root / "certora"
            confs = certora / "2.0.0/confs"
            confs.mkdir(parents=True)
            evm = toolchain.CERTORA_DIR.parent
            for name in ("run-certora.sh", "requirements.txt", "requirements-8.txt"):
                shutil.copyfile(evm / name, root / name)
            for name in ("toolchain.py", "pull_guards.py"):
                shutil.copyfile(toolchain.CERTORA_DIR / name, certora / name)
            for name in ("Safe-receive.conf", "Roles-configIntegrity.conf"):
                (confs / name).write_text('{"files": []}\n')
            # The runner pulls the guards at tag 2.0.0 before it calls the prover.
            (root / "contracts/helpers").mkdir(parents=True)
            for path in pull_guards.GUARDS:
                (root / "contracts" / path).write_text("// guard\n")
            for command in (["init", "-q"], ["add", "contracts"], ["commit", "-q", "-m", "release"], ["tag", "2.0.0"]):
                subprocess.run(GIT + command, cwd=root, check=True, capture_output=True)
            binary = root / "certoraRun"
            binary.write_text(
                "#!/usr/bin/env python3\n"
                "import json, os, pathlib, sys\n"
                "if sys.argv[1:] == ['--version']:\n"
                "    print('certora-cli ' + os.environ['STUB_CLI_VERSION'])\n"
                "else:\n"
                "    pathlib.Path(os.environ['STUB_CALL_LOG']).write_text(json.dumps({\n"
                "        'cwd': os.getcwd(), 'args': sys.argv[1:], 'solc': os.environ['SOLC_VERSION']}))\n"
            )
            binary.chmod(0o755)
            log = root / "calls.json"
            env = {"PATH": str(root) + os.pathsep + os.environ["PATH"], "CERTORAKEY": "test-only",
                   "STUB_CALL_LOG": str(log)}
            script = ["bash", str(root / "run-certora.sh")]
            for config, version, compiler in (("Safe-receive.conf", "8.19.2", "0.7.6"),
                                               ("Roles-configIntegrity.conf", "7.31.0", "0.8.6")):
                with self.subTest(config=config):
                    env["STUB_CLI_VERSION"] = version
                    result = subprocess.run(script + ["2.0.0/" + config, "proof message"], cwd=root.parent,
                                            env=env, capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    call = json.loads(log.read_text())
                    self.assertEqual(call, {"cwd": str(root), "solc": compiler, "args": [
                        str(confs / config), "--msg", "proof message",
                        "--wait_for_results", "all", "--rule_sanity", "basic"]})
                    log.unlink()
                    env["STUB_CLI_VERSION"] = "7.31.0" if version == "8.19.2" else "8.19.2"
                    result = subprocess.run(script + ["2.0.0/" + config], cwd=root.parent,
                                            env=env, capture_output=True, text=True)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("This proof requires certora-cli " + version, result.stderr)
                    self.assertFalse(log.exists())

            # A tagged release whose guards cannot be pulled stops before the prover.
            subprocess.run(GIT + ["tag", "-d", "2.0.0"], cwd=root, check=True, capture_output=True)
            env["STUB_CLI_VERSION"] = "8.19.2"
            result = subprocess.run(script + ["2.0.0/Safe-receive.conf"], cwd=root.parent,
                                    env=env, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("cannot read contracts/helpers/", result.stderr)
            self.assertFalse(log.exists())

    def test_tagged_release_pulls_its_guards_and_their_relative_imports_from_the_tag(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            contracts = root / "contracts"
            (contracts / "helpers").mkdir(parents=True)
            (contracts / "interfaces").mkdir()
            tagged = {
                "helpers/ConfigLockGuard.sol": 'import "../interfaces/IDelay.sol";\n// import "./Missing.sol";\n',
                "helpers/PauseGuard.sol": 'import "@openzeppelin/contracts/access/AccessControl.sol";\n',
                "helpers/SetTxNonceGuard.sol": 'import {BaseGuard} from "@gnosis.pm/zodiac/contracts/guard/BaseGuard.sol";\n',
                "interfaces/IDelay.sol": "interface IDelay {}\n",
            }
            for path, text in tagged.items():
                (contracts / path).write_text(text)
            for command in (["init", "-q"], ["add", "."], ["commit", "-q", "-m", "release"], ["tag", "2.0.0"]):
                subprocess.run(GIT + command, cwd=root, check=True, capture_output=True)
            for path in tagged:
                (contracts / path).write_text("// changed after the tag\n")
            stale = root / "certora/2.0.0/contracts/stale.sol"
            stale.parent.mkdir(parents=True)
            stale.write_text("\n")
            with patch.object(pull_guards, "CERTORA_DIR", root / "certora"):
                self.assertEqual(pull_guards.pull("2.0.0"), sorted(tagged))
                self.assertEqual(pull_guards.pull("2.1.0"), [])
            for path, text in tagged.items():
                self.assertEqual((root / "certora/2.0.0/contracts" / path).read_text(), text)
            self.assertFalse(stale.exists())
            self.assertFalse((root / "certora/2.1.0").exists())


if __name__ == "__main__":
    unittest.main()
