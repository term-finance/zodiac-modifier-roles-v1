"""Pull a tagged release's guard contracts from its git tag.

The release folders share every contract source except the three guards. A
tagged release proves the guards at its tag: this writes them, and the files
they import relatively, to certora/<release>/contracts, mirroring
packages/evm/contracts. The open release compiles packages/evm/contracts as it
is, so it has nothing to pull.
"""

import argparse
from pathlib import Path
import posixpath
import re
import shutil
import subprocess


CERTORA_DIR = Path(__file__).resolve().parent
GUARDS = ("helpers/ConfigLockGuard.sol", "helpers/PauseGuard.sol", "helpers/SetTxNonceGuard.sol")
TAGGED = ("2.0.0",)
COMMENT = re.compile(r"//[^\n]*|/\*.*?\*/", re.S)
IMPORT = re.compile(r"\bimport\s+(?:[^\"';]*\bfrom\s+)?[\"']([^\"']+)[\"']")


def pull(release):
    """Write the guards at tag <release> under certora/<release>/contracts; return what was written."""
    if release not in TAGGED:
        return []
    target = CERTORA_DIR / release / "contracts"
    shutil.rmtree(target, ignore_errors=True)
    pulled = set()
    pending = list(GUARDS)
    while pending:
        path = pending.pop()
        if path in pulled:
            continue
        if path.startswith("../"):
            raise ValueError(f"a guard at tag {release} imports {path}, outside contracts/")
        result = subprocess.run(["git", "show", f"refs/tags/{release}:./contracts/{path}"],
                                cwd=CERTORA_DIR.parent, capture_output=True)
        if result.returncode != 0:
            raise ValueError(f"cannot read contracts/{path} at tag {release}; is the tag fetched?")
        (target / path).parent.mkdir(parents=True, exist_ok=True)
        (target / path).write_bytes(result.stdout)
        pulled.add(path)
        for imported in IMPORT.findall(COMMENT.sub("", result.stdout.decode())):
            if imported.startswith(("./", "../")):
                pending.append(posixpath.normpath(posixpath.join(posixpath.dirname(path), imported)))
    return sorted(pulled)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("release", help="release folder under certora, such as 2.0.0")
    args = parser.parse_args()
    try:
        pulled = pull(args.release)
    except ValueError as error:
        parser.error(str(error))
    if not pulled:
        print(f"{args.release} is not tagged: its confs compile packages/evm/contracts")
    for path in pulled:
        print(f"certora/{args.release}/contracts/{path} <- contracts/{path} at tag {args.release}")


if __name__ == "__main__":
    main()
