"""Freeze exact local trace hashes without parsing commands or scoring outcomes."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

from pipes_common import PROTOCOL_VERSION

APPROVAL_TOKEN = "local-trace-freeze-reviewed-v3"
OPEN_CASES = tuple(range(1, 16))
HOLDOUT_CASES = tuple(range(1, 13))
MANIFEST_NAME = "local-trace-manifest.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def trace_digest(input_sha256: str, reply_sha256: str) -> str:
    payload = f"PipesTrace-v1\n{input_sha256}\n{reply_sha256}".encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def _input_hashes_from_open_cases(repo: Path) -> dict[str, str]:
    csv_path = repo / "results/pipes/final/open-run-size-cohort-lanes/cases.csv"
    by_name: dict[str, str] = {}
    with csv_path.open("r", encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    if len(rows) != len(OPEN_CASES):
        raise RuntimeError("Open15 cases.csv must contain exactly 15 rows")
    for row in rows:
        test_path = Path(row["test_file"])
        if not test_path.is_absolute():
            test_path = repo / test_path
        test_path = test_path.resolve()
        if test_path.parent != (repo / "data/pipes/open").resolve():
            raise RuntimeError("Open15 cases.csv contains an unexpected input path")
        name = test_path.name
        if name in by_name:
            raise RuntimeError(f"duplicate Open15 input in cases.csv: {name}")
        by_name[name] = row["test_sha256"]
    expected = {f"{case}.in" for case in OPEN_CASES}
    if set(by_name) != expected:
        raise RuntimeError("Open15 cases.csv does not name the exact 1.in–15.in set")
    return by_name


def _exact_input_set(root: Path, expected_names: set[str], dataset: str) -> None:
    actual_names = {path.relative_to(root).as_posix() for path in root.rglob("*.in")}
    if actual_names != expected_names:
        raise RuntimeError(
            f"{dataset} input set differs: missing={sorted(expected_names - actual_names)}, "
            f"extra={sorted(actual_names - expected_names)}"
        )


def _exact_reply_set(root: Path, expected_relative: set[str], dataset: str) -> None:
    actual_relative = {
        path.relative_to(root).as_posix() for path in root.rglob("judge_output.txt")
    }
    if actual_relative != expected_relative:
        raise RuntimeError(
            f"{dataset} reply set differs: "
            f"missing={sorted(expected_relative - actual_relative)}, "
            f"extra={sorted(actual_relative - expected_relative)}"
        )


def _freeze_open15(repo: Path) -> dict[str, object]:
    input_root = repo / "data/pipes/open"
    output_root = repo / "results/pipes/final/open-run-size-cohort-lanes/runs"
    expected_inputs = {f"{case}.in" for case in OPEN_CASES}
    expected_replies = {f"{case}/judge_output.txt" for case in OPEN_CASES}
    _exact_input_set(input_root, expected_inputs, "Open15")
    _exact_reply_set(output_root, expected_replies, "Open15")
    official_hashes = _input_hashes_from_open_cases(repo)

    entries = []
    for case in OPEN_CASES:
        input_path = input_root / f"{case}.in"
        reply_path = output_root / str(case) / "judge_output.txt"
        input_hash = sha256_file(input_path)
        if input_hash != official_hashes[input_path.name]:
            raise RuntimeError(f"Open15 input hash differs from cases.csv: {input_path.name}")
        reply_hash = sha256_file(reply_path)
        entries.append(
            {
                "name": f"open-{case:02d}",
                "input_file": input_path.relative_to(repo).as_posix(),
                "input_sha256": input_hash,
                "reply_file": reply_path.relative_to(repo).as_posix(),
                "reply_sha256": reply_hash,
                "trace_sha256": trace_digest(input_hash, reply_hash),
            }
        )
    cases_manifest = repo / "results/pipes/final/open-run-size-cohort-lanes/cases.csv"
    return {
        "source_case_manifest_file": cases_manifest.relative_to(repo).as_posix(),
        "source_case_manifest_sha256": sha256_file(cases_manifest),
        "case_count": len(entries),
        "cases": entries,
    }


def _freeze_holdout(repo: Path) -> dict[str, object]:
    input_root = repo / "data/pipes/synthetic/final-holdout-v2"
    output_root = repo / "results/pipes/final/holdout-run-size-cohort-lanes/runs"
    expected_inputs = {f"case-{case:02d}.in" for case in HOLDOUT_CASES}
    expected_replies = {
        f"case-{case:02d}/judge_output.txt" for case in HOLDOUT_CASES
    }
    _exact_input_set(input_root, expected_inputs, "holdout-v2")
    _exact_reply_set(output_root, expected_replies, "holdout-v2")

    source_manifest_path = input_root / "manifest.json"
    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    source_rows = source_manifest.get("per_case", [])
    if source_manifest.get("case_count") != len(HOLDOUT_CASES) or len(source_rows) != len(HOLDOUT_CASES):
        raise RuntimeError("holdout source manifest must list exactly 12 cases")
    official_hashes: dict[str, str] = {}
    for row in source_rows:
        source_path = Path(row["file"])
        if not source_path.is_absolute():
            source_path = repo / source_path
        source_path = source_path.resolve()
        name = source_path.name
        if source_path != (input_root / name).resolve():
            raise RuntimeError("holdout source manifest contains an unexpected input path")
        if name in official_hashes:
            raise RuntimeError(f"duplicate holdout input in source manifest: {name}")
        official_hashes[name] = row["sha256"]
    if set(official_hashes) != expected_inputs:
        raise RuntimeError("holdout source manifest does not name case-01.in–case-12.in")

    entries = []
    for case in HOLDOUT_CASES:
        name = f"case-{case:02d}.in"
        input_path = input_root / name
        reply_path = output_root / f"case-{case:02d}" / "judge_output.txt"
        input_hash = sha256_file(input_path)
        if input_hash != official_hashes[name]:
            raise RuntimeError(f"holdout input hash differs from source manifest: {name}")
        reply_hash = sha256_file(reply_path)
        entries.append(
            {
                "name": f"case-{case:02d}",
                "input_file": input_path.relative_to(repo).as_posix(),
                "input_sha256": input_hash,
                "reply_file": reply_path.relative_to(repo).as_posix(),
                "reply_sha256": reply_hash,
                "trace_sha256": trace_digest(input_hash, reply_hash),
            }
        )
    return {
        "source_case_manifest_file": source_manifest_path.relative_to(repo).as_posix(),
        "source_case_manifest_sha256": sha256_file(source_manifest_path),
        "case_count": len(entries),
        "cases": entries,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--approval-token", required=True)
    args = parser.parse_args()
    if args.approval_token != APPROVAL_TOKEN:
        raise SystemExit("freezing local trace hashes requires separate v3 review approval")

    repo = args.repo.resolve()
    artifact_root = Path(__file__).resolve().parent
    source_manifest = artifact_root / "SOURCE_SHA256SUMS"
    payload = {
        "protocol_version": PROTOCOL_VERSION,
        "source_sha256s_sha256": sha256_file(source_manifest),
        "hashing_only_no_trace_parsing_or_scoring": True,
        "datasets": {
            "open15": _freeze_open15(repo),
            "holdout-v2": _freeze_holdout(repo),
        },
    }
    destination = artifact_root / MANIFEST_NAME
    with destination.open("x", encoding="utf-8") as output:
        json.dump(payload, output, indent=2)
        output.write("\n")


if __name__ == "__main__":
    main()
