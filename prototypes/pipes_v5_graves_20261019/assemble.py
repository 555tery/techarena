"""Integrate independently constructed inputs, deduplicate and validate syntax."""
import hashlib
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "tools"))
from pipes_harness import parse_test


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    rows = []
    for row in json.loads((HERE / "reservation-manifest.json").read_text())["tests"]:
        rows.append({"name": row["name"], "original": row["file"],
                     "family": "early-reservation", "open_case": row["case"],
                     "common_prefix": row["prefix"],
                     "predicted_prefix_max_ratio": row["prefix_max_trench_ratio"],
                     "provenance": "reservation-manifest.json"})
    for suffix in ["open1", "open2_beam"]:
        path = HERE / "diagnostics" / ("geometry_quiet_" + suffix + ".json")
        d = json.loads(path.read_text())
        rows.append({"name": "quiet-" + suffix.replace("_", "-"), "original": d["test"]["file"],
                     "family": "strict-quiet-geometry", "open_case": d["shared_prefix"]["open_case"],
                     "common_prefix": d["shared_prefix"]["prefix_length"],
                     "predicted_prefix_max_ratio": d["shared_prefix"].get("max_T_target_over_T_plain_BF", d["shared_prefix"].get("max_T_target_over_plain_BF")),
                     "provenance": str(path.relative_to(HERE))})
    for d in json.loads((HERE / "shape_manifest.json").read_text())["cases"]:
        rows.append({"name": d["name"].replace("_", "-"), "original": d["file"],
                     "family": "moderate-quiet-geometry", "open_case": d["case"],
                     "common_prefix": d["cut"], "predicted_prefix_max_ratio": d["max_prefix_ratio"],
                     "provenance": "shape_manifest.json"})
    inputs = HERE / "suite"
    inputs.mkdir(exist_ok=True)
    selected, seen = [], {}
    for row in rows:
        source = REPO / row["original"]
        digest = sha(source)
        if digest in seen:
            seen[digest].setdefault("duplicate_public_cases", []).append(row["open_case"])
            continue
        target = inputs / (row["name"] + ".in")
        if target.exists():
            assert sha(target) == digest
        else:
            shutil.copy2(source, target)
        meta = parse_test(target)
        assert meta["final_occupied_length_m"] > 0
        tokens = target.read_text().split()
        cmd = list(map(int, tokens[2:2+int(tokens[1])]))
        pub = REPO / "data/pipes/open" / f"{row['open_case']}.in"
        raw = pub.read_text().split()
        public = list(map(int, raw[2:2+int(raw[1])]))
        cut = row["common_prefix"]
        assert cmd[:cut] == public[:cut]
        assert cut == len(public) or cmd[cut] != public[cut]
        item = {**row, **meta, "file": str(target.relative_to(REPO)),
                "public_input_sha256": sha(pub)}
        selected.append(item)
        seen[digest] = item
    assert len(selected) == 9
    manifest = {"target": json.loads((HERE / "target.json").read_text()),
                "purpose": "User-authorized local adversarial tests against release-v5, including cumulative quiet prefixes; no solver optimization or platform use.",
                "suite_size": len(selected), "tests": selected,
                "selection": "Deterministic early-reservation selection plus two independent bounded geometry searches. This is a targeted stress suite, not an unseen distribution.",
                "platform_actions": 0}
    (HERE / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print([(x["name"], x["operation_count"], x["family"]) for x in selected])


if __name__ == "__main__":
    main()
