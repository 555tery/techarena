from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path


ROOT = Path(__file__).resolve().parent
TRACES = ROOT / "relative_parity_v2"
TRACES.mkdir(parents=True, exist_ok=True)


SPECS = [
    {
        "name": "odd_count_rel0_full",
        "seed": 20261101,
        "sizes": list(range(3, 20)),
        "counts": [101] * 17,
        "relative_delete_offset": 0,
        "fraction_blocks": 17,
    },
    {
        "name": "even_count_rel0_full",
        "seed": 20261102,
        "sizes": list(range(5, 23)),
        "counts": [100] * 18,
        "relative_delete_offset": 0,
        "fraction_blocks": 18,
    },
    {
        "name": "odd_count_rel1_full",
        "seed": 20261103,
        "sizes": list(range(4, 21)),
        "counts": [99] * 17,
        "relative_delete_offset": 1,
        "fraction_blocks": 17,
    },
    {
        "name": "varcounts_rel0_full",
        "seed": 20261104,
        "sizes": list(range(3, 21)),
        "counts": [92, 100, 108, 96, 104, 92, 100, 108, 96, 104, 92, 100, 108, 96, 104, 92, 100, 108],
        "relative_delete_offset": 0,
        "fraction_blocks": 18,
    },
    {
        "name": "two_phase_rel0",
        "seed": 20261105,
        "sizes": list(range(3, 10)) + list(range(12, 21)),
        "counts": [100] * 16,
        "relative_delete_offset": 0,
        "fraction_blocks": 16,
    },
    {
        "name": "early_stop_rel1",
        "seed": 20261106,
        "sizes": list(range(6, 22)),
        "counts": [100] * 16,
        "relative_delete_offset": 1,
        "fraction_blocks": 9,
    },
    {
        "name": "late_stop_rel0",
        "seed": 20261107,
        "sizes": list(range(2, 31)),
        "counts": [100] * 29,
        "relative_delete_offset": 0,
        "fraction_blocks": 27,
    },
    {
        "name": "phase_shift_varcounts_rel1",
        "seed": 20261108,
        "sizes": list(range(4, 11)) + list(range(14, 22)) + list(range(25, 31)),
        "counts": [92, 100, 108, 96, 104, 92, 100, 108, 96, 104, 92, 100, 108, 96, 104, 92, 100, 108, 96, 104, 92],
        "relative_delete_offset": 1,
        "fraction_blocks": 21,
    },
]


def generate(spec: dict) -> list[int]:
    rng = random.Random(spec["seed"])
    del rng
    commands: list[int] = []
    next_pid = 1
    block_count = spec["fraction_blocks"]
    for size, count in list(zip(spec["sizes"], spec["counts"], strict=True))[:block_count]:
        block = list(range(next_pid, next_pid + count))
        commands.extend([size] * count)
        remove_count = count // 2
        offset = spec["relative_delete_offset"]
        deleted = [pid for local_index, pid in enumerate(block)
                   if local_index % 2 == offset][:remove_count]
        commands.extend(-pid for pid in deleted)
        next_pid += count
    return commands


manifest = {
    "prepared_before_v2_candidate_runs": True,
    "suite": "fresh streams with stable deletion parity relative to each size block",
    "seeds": [spec["seed"] for spec in SPECS],
    "streams": [],
}
for spec in SPECS:
    commands = generate(spec)
    data = f"1.0 {len(commands)}\n" + "\n".join(map(str, commands)) + "\n"
    path = TRACES / f"{spec['name']}.in"
    path.write_text(data)
    item = {key: value for key, value in spec.items() if key != "fraction_blocks"}
    item.update(
        {
            "blocks_included": spec["fraction_blocks"],
            "commands": len(commands),
            "placements": sum(command > 0 for command in commands),
            "sha256": hashlib.sha256(data.encode()).hexdigest(),
        }
    )
    manifest["streams"].append(item)
(ROOT / "relative_parity_v2_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(json.dumps(manifest, indent=2))
