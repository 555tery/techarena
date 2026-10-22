#!/usr/bin/env python3
"""Build reproducible online Pipes heuristic candidates into this directory."""
import hashlib
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SRC = HERE / "adaptive_allocator.cpp"
OUT = HERE / "binaries"
OUT.mkdir(parents=True, exist_ok=True)

CONFIGS = [
    ("all_right", 1, 128, 20),
    ("recent_unfit_s10", 2, 128, 10),
    ("recent_unfit_s25", 2, 128, 25),
    ("recent_unfit_s50", 2, 128, 50),
    ("recent_unfit_w32_s25", 2, 32, 25),
    ("recent_unfit_w512_s25", 2, 512, 25),
    ("recent_residue_s20", 3, 128, 20),
    ("recent_residue_s50", 3, 128, 50),
]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

entries = []
for name, strategy, window, scale in CONFIGS:
    binary = OUT / name
    cmd = [
        "g++", "-O2", "-std=c++17", "-Wall", "-Wextra", "-pedantic",
        f"-DPIPES_STRATEGY={strategy}",
        f"-DPIPES_HISTORY_WINDOW={window}",
        f"-DPIPES_PENALTY_SCALE={scale}",
        str(SRC), "-o", str(binary),
    ]
    subprocess.run(cmd, cwd=ROOT, check=True)
    entries.append({
        "name": name,
        "strategy": strategy,
        "history_window": window,
        "penalty_scale": scale,
        "command": " ".join(cmd),
        "source_sha256": sha(SRC),
        "binary": str(binary),
        "binary_sha256": sha(binary),
    })

manifest = {"source": str(SRC), "source_sha256": sha(SRC), "candidates": entries}
(HERE / "build_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
for item in entries:
    print(item["name"], item["binary_sha256"])
