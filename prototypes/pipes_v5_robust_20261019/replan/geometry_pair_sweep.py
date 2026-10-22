#!/usr/bin/env python3
"""Small offset sweep for optimal shared-prefix plans on Open8/13 and 11/15."""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from geometry_replan import (
    AUDIT, CONT, OUT, PROBE, TAPE, SOURCE, build_conditioned, causal_bf_pins,
    decode, read_case, read_positions, sha,
)


def main() -> None:
    audit = json.loads(AUDIT.read_text())
    targets = {c["case"]: c["lower_T"] for c in audit["cases"]}
    tables = decode(SOURCE)
    cases = {i: read_case(i)[1] for i in (8, 11, 13, 15)}
    binary = OUT / "geometry_conditioned"
    assert binary.exists()
    report = {"scope": "bounded offset sweep; only local Open15 plan artifacts",
              "source_sha256": sha(SOURCE), "attempts": {}, "shared_prefixes": {},
              "selected": {}}

    # Open8 and Open13 share 388 commands (210 allocations). First p1 remains
    # compact at zero; sweep the second 20 m allocation around its BF position.
    prefix8, _ = causal_bf_pins(8, cases[8], 2)
    assert prefix8 == 2
    found8 = False
    seen8: set[str] = set()
    for x in [6, 7, 8, 12, 20, 32, 64, 128, 256, 512, 1024, 3064]:
        d8 = OUT / f"sweep8_x{x}"
        rows8 = build_conditioned(binary, 8, cases[8], 2, [0, x], d8)
        entry = {"pinned_positions": [0, x], "open8_modes": rows8, "open13_seeds": []}
        report["attempts"][f"open8_x{x}"] = entry
        for candidate in rows8:
            if candidate["returncode"] or candidate["T"] != targets[8]:
                continue
            plan8 = Path(candidate["positions"])
            shared = list(map(int, plan8.read_text().split()))[:210]
            digest = hashlib.sha256(("\n".join(map(str, shared)) + "\n").encode()).hexdigest()
            if digest in seen8:
                continue
            seen8.add(digest)
            d13 = OUT / f"sweep13_from8_x{x}_m{candidate['mode']}"
            rows13 = build_conditioned(binary, 13, cases[13], 388, shared, d13)
            seed = {"seed_mode": candidate["mode"], "seed_plan": str(plan8),
                    "shared_prefix_positions_sha256": digest, "open13_modes": rows13}
            entry["open13_seeds"].append(seed)
            match13 = [r for r in rows13 if r["returncode"] == 0 and r["T"] == targets[13]]
            if match13:
                chosen13 = match13[0]
                prefix8_positions = shared
                candidate13_positions = read_positions(Path(chosen13["positions"]), cases[13])
                assert candidate13_positions[:210] == prefix8_positions
                dest8 = OUT / "geometry_open8_positions.txt"
                dest13 = OUT / "geometry_open13_positions.txt"
                shutil.copyfile(plan8, dest8)
                shutil.copyfile(chosen13["positions"], dest13)
                report["selected"].update({
                    "8": {"plan": str(dest8), "T": candidate["T"], "mode": candidate["mode"],
                          "positions_sha256": sha(dest8), "position_count": len(read_positions(dest8, cases[8]))},
                    "13": {"plan": str(dest13), "T": chosen13["T"], "mode": chosen13["mode"],
                           "positions_sha256": sha(dest13), "position_count": len(candidate13_positions)},
                })
                report["shared_prefixes"]["8_13"] = {
                    "common_commands": 388, "common_allocations": 210,
                    "positions_identical": candidate13_positions[:210] == prefix8_positions,
                    "positions_sha256": digest, "prefix_seed_case": 8,
                    "prefix_seed_mode": candidate["mode"], "pinned_first2": [0, x],
                }
                found8 = True
                break
        if found8:
            break

    # Open11 and Open15 share 4,999 commands (4,006 allocations). Relocate
    # the short-lived second pipe, then propagate the selected shared prefix.
    found11 = False
    seen11: set[str] = set()
    for x in [3, 4, 5, 8, 12, 20, 40, 80, 160, 320, 640, 1280, 2560, 5120, 10240, 16384, 19518]:
        d11 = OUT / f"sweep11_x{x}"
        rows11 = build_conditioned(binary, 11, cases[11], 2, [0, x], d11)
        entry = {"pinned_positions": [0, x], "open11_modes": rows11, "open15_seeds": []}
        report["attempts"][f"open11_x{x}"] = entry
        for candidate in rows11:
            if candidate["returncode"] or candidate["T"] != targets[11]:
                continue
            plan11 = Path(candidate["positions"])
            shared = list(map(int, plan11.read_text().split()))[:4006]
            digest = hashlib.sha256(("\n".join(map(str, shared)) + "\n").encode()).hexdigest()
            if digest in seen11:
                continue
            seen11.add(digest)
            d15 = OUT / f"sweep15_from11_x{x}_m{candidate['mode']}"
            rows15 = build_conditioned(binary, 15, cases[15], 4999, shared, d15)
            seed = {"seed_mode": candidate["mode"], "seed_plan": str(plan11),
                    "shared_prefix_positions_sha256": digest, "open15_modes": rows15}
            entry["open15_seeds"].append(seed)
            match15 = [r for r in rows15 if r["returncode"] == 0 and r["T"] == targets[15]]
            if match15:
                chosen15 = match15[0]
                candidate15_positions = read_positions(Path(chosen15["positions"]), cases[15])
                assert candidate15_positions[:4006] == shared
                dest11 = OUT / "geometry_open11_positions.txt"
                dest15 = OUT / "geometry_open15_positions.txt"
                shutil.copyfile(plan11, dest11)
                shutil.copyfile(chosen15["positions"], dest15)
                report["selected"].update({
                    "11": {"plan": str(dest11), "T": candidate["T"], "mode": candidate["mode"],
                           "positions_sha256": sha(dest11), "position_count": len(read_positions(dest11, cases[11]))},
                    "15": {"plan": str(dest15), "T": chosen15["T"], "mode": chosen15["mode"],
                           "positions_sha256": sha(dest15), "position_count": len(candidate15_positions)},
                })
                report["shared_prefixes"]["11_15"] = {
                    "common_commands": 4999, "common_allocations": 4006,
                    "positions_identical": candidate15_positions[:4006] == shared,
                    "positions_sha256": digest, "prefix_seed_case": 11,
                    "prefix_seed_mode": candidate["mode"], "pinned_first2": [0, x],
                }
                found11 = True
                break
        if found11:
            break

    # Report the tightest observed T even where no fully optimal pair was found.
    for pair, seed_case, follower, seed_k, follow_k in [
        ("8_13", 8, 13, 2, 388), ("11_15", 11, 15, 2, 4999)
    ]:
        if pair in report["shared_prefixes"]:
            continue
        best_seed = None
        for key, entry in report["attempts"].items():
            if not key.startswith(f"open{seed_case}_"):
                continue
            for row in entry[f"open{seed_case}_modes"]:
                if row["returncode"] == 0 and (best_seed is None or row["T"] < best_seed["seed_T"]):
                    best_seed = {"seed_T": row["T"], "seed_mode": row["mode"],
                                 "pin": entry["pinned_positions"], "plan": row["positions"],
                                 "follower_tests": []}
                    for seed in entry[f"open{follower}_seeds"]:
                        best_follower = min((r["T"] for r in seed[f"open{follower}_modes"] if r["returncode"] == 0), default=None)
                        best_seed["follower_tests"].append({"seed_mode": seed["seed_mode"], "best_follower_T": best_follower})
        report["shared_prefixes"][pair] = {"status": "no_exact_pair_found_in_bounded_sweep",
                                            "target_T": {str(seed_case): targets[seed_case], str(follower): targets[follower]},
                                            "best_seed_candidate": best_seed}

    # Preserve independently useful Open10/Open14 candidate tables in this report.
    report["already_selected_independent"] = json.loads((OUT / "geometry_open10_14_candidates.json").read_text())
    (OUT / "geometry_pair_sweep.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"selected": report["selected"], "shared_prefixes": report["shared_prefixes"]}, indent=2))


if __name__ == "__main__":
    main()
