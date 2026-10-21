"""Resolve a proof configuration and its validated Certora CLI version."""

import argparse
from pathlib import Path
import re


CERTORA_DIR = Path(__file__).resolve().parent
# One folder per release, named after its git tag.
RELEASES = ("2.0.0", "2.1.0")
CERTORA_8_CONFIGS = dict.fromkeys(RELEASES, frozenset({
    "MultiSend-shortBatch.conf",
    "PauseGuard-deployment.conf",
    "Safe-fallbackStorage.conf",
    "Safe-noStateChange.conf",
    "Safe-receive.conf",
    "Safe-v141-fallbackStorage.conf",
    "Safe-v141-noStateChange.conf",
    "Safe-v141-receive.conf",
}))


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
