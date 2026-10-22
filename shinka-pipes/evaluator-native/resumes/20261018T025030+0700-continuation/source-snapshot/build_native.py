"""Pinned official checker + native adapter; source transformation only buffers tout."""

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
FAST = ROOT.parent / "evaluator-fast"
sys.path.insert(0, str(FAST))
from reference import BASE, check_reference, digest


def build(directory: Path) -> Path:
    check_reference()
    directory.mkdir(parents=True, exist_ok=True)
    source = (BASE / "task/vendor/interactor.cpp").read_text()
    replacements = {
        'tout << cnt << " " << shift << endl;': 'tout << cnt << " " << shift << \'\\n\';',
        'tout << shift << endl;': 'tout << shift << \'\\n\';',
    }
    for original, replacement in replacements.items():
        if source.count(original) != 1:
            raise ValueError("official checker no longer matches the reviewed transformation")
        source = source.replace(original, replacement)
    (directory / "official_checker.cpp").write_text(source)
    compiler = shutil.which("g++")
    command = [compiler, "-O2", "-std=c++17", "-pipe", "-pthread", "-I", str(BASE / "task/vendor"),
               "-I", str(directory), str(ROOT / "native_runner.cpp"), "-o", str(directory / "native_runner")]
    subprocess.run(command, capture_output=True, text=True, timeout=120, check=True)
    (directory / "build.json").write_text(json.dumps({
        "command": command, "official_source_sha256": digest(BASE / "task/vendor/interactor.cpp"),
        "testlib_sha256": digest(BASE / "task/vendor/testlib.h"),
        "adapter_sha256": digest(ROOT / "native_runner.cpp"),
        "transformed_source_sha256": digest(directory / "official_checker.cpp"),
        "transformations": replacements, "binary_sha256": digest(directory / "native_runner"),
    }, indent=2) + "\n")
    return directory / "native_runner"


if __name__ == "__main__":
    print(build(Path(sys.argv[1]).resolve()))
