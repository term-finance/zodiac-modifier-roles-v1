#!/usr/bin/env python3
"""Replay the reported packed-key alias against the archived original sources."""
from pathlib import Path, PurePosixPath
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / 'bitwise-memory-diagnostic'
ARCHIVE = SOURCE / 'submitted-inputs.zip'
expected = json.loads((SOURCE / 'manifest.json').read_text())['filesSha256']['submitted-inputs.zip']
assert hashlib.sha256(ARCHIVE.read_bytes()).hexdigest() == expected, 'Submitted archive hash mismatch'

with tempfile.TemporaryDirectory(prefix='roles-packed-key-') as directory:
    root = Path(directory)
    with zipfile.ZipFile(ARCHIVE) as bundle:
        for member in bundle.namelist():
            path = PurePosixPath(member)
            if path.parts[:1] != ('.certora_sources',):
                continue
            relative = PurePosixPath(*path.parts[1:])
            assert '..' not in relative.parts and not relative.is_absolute()
            if not str(relative).startswith(('contracts/', 'certora/harness/', 'node_modules/')):
                continue
            if member.endswith('/'):
                continue
            output = root / relative
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(bundle.read(member))
    test = root / 'native-test'
    test.mkdir()
    shutil.copy2(HERE / 'PackedKey.t.sol', test)
    shutil.copy2(HERE / 'foundry.toml', root)
    compiler = sys.argv[1] if len(sys.argv) > 1 else '0.8.30'
    subprocess.run(['forge', 'test', '--root', str(root), '--use', compiler,
                    '--match-contract', 'PackedKeyTest', '-vv'], check=True)
