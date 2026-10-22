#!/usr/bin/env python3
"""Create a predeclared, varied geometric size/deletion screen for case 9."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "synthetic"
OUT.mkdir(parents=True, exist_ok=True)

profiles = [
    {"name": "geom2_odd_half_128", "sizes": [1,2,4,8,16,32], "counts": [128]*6, "delete": "odd_half_up"},
    {"name": "geom2_even_half_192", "sizes": [1,2,4,8,16,32], "counts": [192]*6, "delete": "even_half_up"},
    {"name": "geom2_start2_160", "sizes": [2,4,8,16,32], "counts": [160]*5, "delete": "odd_half_up"},
    {"name": "geom2_scale3_256", "sizes": [3,6,12,24], "counts": [256]*4, "delete": "odd_half_up"},
    {"name": "geom2_count_wobble", "sizes": [1,2,4,8,16,32], "counts": [128,192,160,224,256,320], "delete": "odd_half_up"},
    {"name": "geom2_odd_40pct_256", "sizes": [1,2,4,8,16,32], "counts": [256]*6, "delete": "odd_40pct"},
    {"name": "geom2_reverse_deletions_256", "sizes": [1,2,4,8,16,32], "counts": [256]*6, "delete": "odd_half_reverse"},
    {"name": "geom2_noisy_stride_128", "sizes": [1,2,4,8,16,32], "counts": [128]*6, "delete": "odd_half_with_break"},
]
manifest = {"title": "Case 9 early next-class capacity screen", "date": "2026-10-18", "profiles": []}
for profile in profiles:
    commands = []
    next_pid = 1
    for phase, (size, count) in enumerate(zip(profile["sizes"], profile["counts"])):
        first = next_pid
        commands.extend([size] * count)
        pids = list(range(first, first + count))
        next_pid += count
        kind = profile["delete"]
        parity = 1 if kind.startswith("odd") else 0
        if kind == "odd_half_up" or kind == "even_half_up":
            deleted = [p for p in pids if p % 2 == parity]
        elif kind == "odd_40pct":
            deleted = [p for p in pids if p % 2 == 1][: int(count * 0.40)]
        elif kind == "odd_half_reverse":
            deleted = [p for p in pids if p % 2 == 1][::-1]
        elif kind == "odd_half_with_break":
            deleted = [p for p in pids if p % 2 == 1]
            if len(deleted) > 20:
                deleted[20] += 1
                # Replace the skipped odd PID with an even live PID from this block.
                deleted[-1] = pids[-1] if pids[-1] % 2 == 1 else pids[-2]
                deleted = sorted(set(deleted))
        else:
            raise ValueError(kind)
        commands.extend(-p for p in deleted)
    path = OUT / (profile["name"] + ".in")
    path.write_text("1.0 %d\n%s\n0\n" % (len(commands), "\n".join(map(str, commands))), encoding="ascii")
    data = path.read_bytes()
    manifest["profiles"].append({
        **profile,
        "path": str(path.relative_to(ROOT)),
        "operations": len(commands),
        "sha256": hashlib.sha256(data).hexdigest(),
    })
(ROOT / "synthetic_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
