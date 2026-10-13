"""Resolve a proof configuration and its validated Certora CLI version."""

import argparse
from pathlib import Path
import re


CERTORA_DIR = Path(__file__).resolve().parent
CERTORA_8_CONFIGS = frozenset({
    "Delay-delayOwnerGuard.conf",
    "Delay-delayOwnerSettings.conf",
    "Delay-devopsEndToEnd.conf",
    "Delay-moduleIntegrity.conf",
    "Delay-pauseGuardSufficient.conf",
    "Delay-proposerToOwnerlessSettings.conf",
    "Delay-queueProvenance.conf",
    "Delay-vetoSignedPath.conf",
    "Governor-proposalThreshold.conf",
    "Governor-settings.conf",
    "Governor-tallies.conf",
    "Governor-voting.conf",
    "MultiSend-shortBatch.conf",
    "PauseGuard-deployment.conf",
    "Roles-setTxNonceGuardSufficient.conf",
    "Roles-setTxNonceLands.conf",
    "Safe-configLockGuard.conf",
    "Safe-executionPaths.conf",
    "Safe-fallbackHandler.conf",
    "Safe-fallbackStorage.conf",
    "Safe-noStateChange.conf",
    "Safe-ownerlessSafeGuard.conf",
    "Safe-receive.conf",
    "Safe-selfCalls.conf",
    "Safe-selfHandler.conf",
    "Safe-signedSettings.conf",
    "Safe-v141-configLockGuard.conf",
    "Safe-v141-executionPaths.conf",
    "Safe-v141-fallbackHandler.conf",
    "Safe-v141-fallbackStorage.conf",
    "Safe-v141-noStateChange.conf",
    "Safe-v141-receive.conf",
    "Safe-v141-selfCalls.conf",
    "Safe-v141-selfHandler.conf",
    "Safe-v141-signedSettings.conf",
    "Safe-v141-vetoLandsOnDelay.conf",
})


def toolchain(config):
    path = Path(config)
    if path.parent == Path("."):
        path = CERTORA_DIR / "confs" / path
    path = path.resolve()
    if path.parent != CERTORA_DIR / "confs" or path.suffix != ".conf" or not path.is_file():
        raise ValueError("expected an existing configuration in certora/confs")

    requirements = CERTORA_DIR.parent / (
        "requirements-8.txt" if path.name in CERTORA_8_CONFIGS else "requirements.txt"
    )
    pins = re.findall(r"^certora-cli==([0-9]+\.[0-9]+\.[0-9]+)$", requirements.read_text(), re.M)
    if len(pins) != 1:
        raise ValueError(f"expected exactly one certora-cli version pin in {requirements}")
    return {
        "config": str(path),
        "requirements": str(requirements),
        "version": pins[0],
        "solc_version": "0.7.6" if path.name.startswith("Safe-") else "0.8.6",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", help="configuration basename or path")
    parser.add_argument("--field", choices=("config", "requirements", "version", "solc_version"), default="version")
    args = parser.parse_args()
    try:
        print(toolchain(args.config)[args.field])
    except (OSError, ValueError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
