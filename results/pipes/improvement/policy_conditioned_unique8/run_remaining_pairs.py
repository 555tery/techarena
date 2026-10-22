#!/usr/bin/env python3
"""Run only the five predeclared missing pairs; never rerun completed cases."""
from __future__ import annotations

import csv
import hashlib
import json
import os
from pathlib import Path

import run_validation as rv

HERE = Path(__file__).resolve().parent
EXPECTED_MISSING = {
    "200000_short-heavy_oldest",
    "200000_short-heavy_newest",
    "200000_long-heavy_random",
    "200000_long-heavy_oldest",
    "200000_long-heavy_newest",
}
PARTIAL_CASE = "200000_short-heavy_oldest"
PARTIAL_RECOVERY_ROOT = HERE / "validation" / "recovery_docker_eof_20261017"


def save_rows(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def main() -> None:
    validation = HERE / "validation"
    csv_path = validation / "per_case.csv"
    input_manifest = json.loads((HERE / "inputs/validation_manifest.json").read_text())
    manifest = json.loads((HERE / "manifest.json").read_text())
    source = HERE / "src/policy_conditioned.cpp"
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    if source_hash != manifest["candidate_source"]["sha256"]:
        raise RuntimeError("frozen candidate source hash changed; refusing to run")

    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames
        rows = list(reader)
    if fields is None or len(rows) != 18:
        raise RuntimeError("expected preserved 18-row per_case.csv")
    missing = {row["case"] for row in rows if row["candidate_status"] == "not_run"}
    if missing != EXPECTED_MISSING:
        raise RuntimeError(f"missing set differs from approved five: {sorted(missing)}")
    by_case = {row["case"]: row for row in rows}

    items = [item for item in input_manifest["records"] if item["case"] in EXPECTED_MISSING]
    if {item["case"] for item in items} != EXPECTED_MISSING:
        raise RuntimeError("input manifest does not contain exactly the approved cases")

    for item in items:
        if item["case"] == PARTIAL_CASE:
            # The previous Docker session left unaccepted baseline artifacts at
            # the canonical output path. Preserve them and use a unique path.
            if PARTIAL_RECOVERY_ROOT.exists():
                raise RuntimeError(f"recovery output already exists; refusing overwrite: {PARTIAL_RECOVERY_ROOT}")
            rv.OUT = PARTIAL_RECOVERY_ROOT
            output_root = PARTIAL_RECOVERY_ROOT
        else:
            case_dir = validation / "runs" / item["case"]
            if case_dir.exists():
                raise RuntimeError(f"partial or completed run directory exists; refusing rerun: {case_dir}")
            rv.OUT = validation
            output_root = validation
        row = rv.run_pair(item)
        by_case[item["case"]] = {key: str(row.get(key, "")) for key in fields}
        rows = [by_case[row["case"]] for row in rows]
        save_rows(csv_path, rows, fields)
        manifest.setdefault("recovered_pair_outputs", {})[item["case"]] = {
            "output_root": str(output_root.relative_to(HERE)),
            "baseline_summary": str((output_root / "runs" / item["case"] / "frozen-final" / "summary.json").relative_to(HERE)),
            "candidate_summary": str((output_root / "runs" / item["case"] / "policy-conditioned" / "summary.json").relative_to(HERE)),
            "seed": item["seed"],
            "input_sha256": item["sha256"],
        }
        manifest_tmp = HERE / "manifest.json.tmp"
        manifest_tmp.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(manifest_tmp, HERE / "manifest.json")
        print(
            f"finished {item['case']}: "
            f"dKPI={row['delta_kpi_candidate_minus_baseline']:+.9f}, "
            f"dTrench={row['delta_trench_m_candidate_minus_baseline']:+d}m, "
            f"CPU={row['candidate_cpu_s']:.3f}s, RSS={row['candidate_rss_mib']:.2f}MiB",
            flush=True,
        )

    print("all five previously missing pairs completed; no diagnostics replayed", flush=True)


if __name__ == "__main__":
    main()
