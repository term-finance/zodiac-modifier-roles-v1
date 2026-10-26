"""Resolve a proof configuration and its validated Certora CLI version."""

import argparse
from pathlib import Path
import re


CERTORA_DIR = Path(__file__).resolve().parent
# One folder per release, named after its git tag.
RELEASES = ("2.0.0", "2.1.0")
CERTORA_8_CONFIGS = dict.fromkeys(RELEASES, frozenset({
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
    "Governor-veto.conf",
    "Governor-vetoEndToEnd.conf",
    "Governor-voting.conf",
    "MultiSend-shortBatch.conf",
    "PauseGuard-deployment.conf",
    "Roles-configIntegrity.conf",
    "Roles-setTxNonceGuardSufficient.conf",
    "Roles-setTxNonceLands.conf",
    "Roles-setTxNonceRoleConfigSufficient.conf",
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
}))
# 2.1.0 also runs its Safe-v141 rules, and the rules whose scene holds the
# ProposerSafe or OwnerlessSafe, against SafeL2 v1.4.1 and GnosisSafeL2
# v1.3.0, and the DelayOwnerSafe's and PauseSafe's rules against SafeL2
# v1.5.0.
CERTORA_8_CONFIGS["2.1.0"] |= {
    "Delay-SafeL2-v130-devopsEndToEnd.conf",
    "Delay-SafeL2-v130-proposerToOwnerlessSettings.conf",
    "Delay-SafeL2-v141-devopsEndToEnd.conf",
    "Delay-SafeL2-v141-proposerToOwnerlessSettings.conf",
    "Delay-SafeL2-v150-delayOwnerGuard.conf",
    "Delay-SafeL2-v150-vetoSignedPath.conf",
    "Safe-L2-v130-configLockGuard.conf",
    "Safe-L2-v130-executionPaths.conf",
    "Safe-L2-v130-fallbackHandler.conf",
    "Safe-L2-v130-fallbackStorage.conf",
    "Safe-L2-v130-noStateChange.conf",
    "Safe-L2-v130-ownerlessSafeGuard.conf",
    "Safe-L2-v130-receive.conf",
    "Safe-L2-v130-selfCalls.conf",
    "Safe-L2-v130-selfHandler.conf",
    "Safe-L2-v130-signedSettings.conf",
    "Safe-L2-v130-vetoLandsOnDelay.conf",
    "Safe-L2-v141-configLockGuard.conf",
    "Safe-L2-v141-executionPaths.conf",
    "Safe-L2-v141-fallbackHandler.conf",
    "Safe-L2-v141-fallbackStorage.conf",
    "Safe-L2-v141-noStateChange.conf",
    "Safe-L2-v141-ownerlessSafeGuard.conf",
    "Safe-L2-v141-receive.conf",
    "Safe-L2-v141-selfCalls.conf",
    "Safe-L2-v141-selfHandler.conf",
    "Safe-L2-v141-signedSettings.conf",
    "Safe-L2-v141-vetoLandsOnDelay.conf",
    "Safe-L2-v150-configLockGuard.conf",
    "Safe-L2-v150-executionPaths.conf",
    "Safe-L2-v150-noStateChange.conf",
    "Safe-L2-v150-selfCalls.conf",
}


def toolchain(config):
    path = Path(config)
    if len(path.parts) == 2:
        path = CERTORA_DIR / path.parts[0] / "confs" / path.parts[1]
    path = path.resolve()
    release = path.parent.parent.name
    if (path.parent.parent.parent != CERTORA_DIR or release not in RELEASES or path.parent.name != "confs"
            or path.suffix != ".conf" or not path.is_file()):
        raise ValueError("expected an existing configuration in certora/<release>/confs")

    requirements = CERTORA_DIR.parent / (
        "requirements-8.txt" if path.name in CERTORA_8_CONFIGS[release] else "requirements.txt"
    )
    pins = re.findall(r"^certora-cli==([0-9]+\.[0-9]+\.[0-9]+)$", requirements.read_text(), re.M)
    if len(pins) != 1:
        raise ValueError(f"expected exactly one certora-cli version pin in {requirements}")
    return {
        "config": str(path),
        "release": release,
        "requirements": str(requirements),
        "version": pins[0],
        "solc_version": "0.7.6" if path.name.startswith("Safe-") else "0.8.6",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", help="<release>/<configuration basename>, or a path")
    parser.add_argument("--field", choices=("config", "release", "requirements", "version", "solc_version"),
                        default="version")
    args = parser.parse_args()
    try:
        print(toolchain(args.config)[args.field])
    except (OSError, ValueError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
