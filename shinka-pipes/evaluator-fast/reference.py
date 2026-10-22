"""Load the fixed SEARCH-v2 implementation without writing into its snapshot."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import types

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent / "search-v2"
SNAPSHOT_SHA256 = "75f5aa18525a00bb83b18fd8dfbbbbdde88da0d877cb0c357bc8aabca87876d7"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot() -> dict:
    data = (BASE / "snapshot.json").read_bytes()
    if hashlib.sha256(data).hexdigest() != SNAPSHOT_SHA256:
        raise ValueError("reference snapshot changed; review and repin before use")
    return json.loads(data)


def check_reference() -> dict:
    """Check the 33 support files, including only the SEARCH manifest, no streams."""
    spec = snapshot()
    checked = {}
    for directory, entries in ((BASE, spec["files"]), (BASE.parent, spec["shared_files"])):
        for name, expected in entries.items():
            path = directory / name
            actual = digest(path)
            if actual != expected:
                raise ValueError(f"reference file changed: {path}")
            checked[str(path.relative_to(BASE.parent))] = actual
    return {"snapshot_sha256": SNAPSHOT_SHA256, "checked_files": checked}


def load_frozen(name: str, *, shared: bool = False) -> types.ModuleType:
    spec = snapshot()
    expected = spec["shared_files" if shared else "files"][name]
    path = (BASE.parent if shared else BASE) / name
    source = path.read_bytes()
    if hashlib.sha256(source).hexdigest() != expected:
        raise ValueError(f"reference module changed: {path}")
    module = types.ModuleType("_pipes_reference_" + path.stem)
    module.__file__ = str(path)
    # compile/exec avoids a __pycache__ write beside the frozen module. Its
    # imports are also read-only; in particular no suite loaders are called.
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        exec(compile(source, str(path), "exec"), module.__dict__)
    finally:
        sys.dont_write_bytecode = previous
    return module
