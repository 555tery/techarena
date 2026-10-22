#!/usr/bin/env python3
"""Independent on-disk audit of inputs, metadata, hashes and public prefixes."""
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def main():
    seen = set()
    summary = {}
    for split, count in [("calibration", 64), ("final", 128), ("stress", 3)]:
        path = HERE / split / "manifest.json"
        rows = json.loads(path.read_text())["cases"]
        assert len(rows) == count
        for row in rows:
            raw = (HERE / split / row["file"]).read_bytes()
            tokens = raw.split()
            assert tokens[0] == b"1" and tokens[-1] == b"0"
            commands = list(map(int, tokens[2:-1]))
            assert len(commands) == int(tokens[1]) == row["n"] <= 200000
            digest = hashlib.sha256(raw).hexdigest()
            assert digest == row["sha256"] and digest not in seen
            command_raw = ("\n".join(map(str, commands)) + "\n").encode()
            assert hashlib.sha256(command_raw).hexdigest() == row["commands_sha256"]
            seen.add(digest)
            live = {}
            pid, volume, peak, peak_count = 1, 0, 0, 0
            for c in commands:
                if c > 0:
                    assert c <= 40
                    live[pid] = c
                    pid += 1
                    volume += c
                else:
                    assert c < 0 and -c in live
                    volume -= live.pop(-c)
                peak = max(peak, volume)
                peak_count = max(peak_count, len(live))
            assert volume == row["final_live_volume"] > 0 and live
            assert peak == row["peak_live_volume"]
            assert volume/peak == row["final_to_peak_volume"]
            assert len(live) == row["final_live_count"] and peak_count == row["peak_live_count"]
            q = row["public_prefix"]
            if q:
                source = (ROOT / q["source"]).read_bytes()
                assert hashlib.sha256(source).hexdigest() == q["source_sha256"]
                public = list(map(int, source.split()[2:-1]))
                assert commands[:q["prefix_n"]] == public[:q["prefix_n"]]
                prefix_raw = ("\n".join(map(str, commands[:q["prefix_n"]])) + "\n").encode()
                assert hashlib.sha256(prefix_raw).hexdigest() == q["prefix_commands_sha256"]
        strata = dict(Counter(r["stratum"] for r in rows))
        assert strata == ({"stress": 3} if split == "stress" else {"ordinary": count//2, "prefix": count//2})
        prefixes = [r["public_prefix"] for r in rows if r["public_prefix"]]
        if split != "stress":
            assert {r["case"] for r in prefixes} == set(range(1, 16))
            assert {r["suffix"] for r in prefixes} >= {"stop_after_prefix", "retained_background_reversal", "death_age_reversal", "random_deaths", "batch_deaths", "equal_run_breaks", "lifetime_resampling", "terminal_fill", "near_public_perturbation"}
        summary[split] = {"cases": len(rows), "strata": strata,
            "n_min": min(r["n"] for r in rows), "n_max": max(r["n"] for r in rows),
            "families": len(set(r["family"] for r in rows)),
            "volume_ratio_ge_0_9": sum(r["final_to_peak_volume"] >= .9 for r in rows),
            "public_prefix_suffixes": dict(Counter(r["suffix"] for r in prefixes)),
            "manifest_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    generation = json.loads((HERE / "generation-summary.json").read_text())
    known = set()
    for entry in generation["known_manifests_checked"]:
        raw = (ROOT / entry["path"]).read_bytes()
        known.update(x.decode().lower() for x in re.findall(rb"(?<![0-9a-fA-F])[0-9a-fA-F]{64}(?![0-9a-fA-F])", raw))
    known.update(hashlib.sha256((ROOT / "data/pipes/open" / f"{i}.in").read_bytes()).hexdigest() for i in range(1,16))
    assert not known & seen
    for split,entry in generation["manifests"].items():
        assert summary[split]["manifest_sha256"] == entry["sha256"]
    output = {"all_checks_passed": True, "unique_input_hashes": len(seen),
              "known_hash_overlap": [], "known_sha256_tokens": len(known), "summary": summary}
    (HERE / "disk-validation.json").write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
