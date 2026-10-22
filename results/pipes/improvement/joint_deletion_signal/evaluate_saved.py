"""Evaluate only complete, hash-frozen datasets after their separate review gate."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

from pipes_common import (
    FROZEN_BINARY_SHA256,
    FROZEN_SOURCE_SHA256,
    GROUPED_LOG_OR,
    PROTOCOL_VERSION,
)
from prequential_eval import evaluate_trace_pair, summarize_dataset, write_summary

SYNTHETIC_APPROVAL_TOKEN = "synthetic-eval-reviewed-v3"
LOCAL_APPROVAL_TOKEN = "local-diagnostics-reviewed-v3"
EVAL_REPLICATES = 24
OPEN_CASES = tuple(range(1, 16))
HOLDOUT_CASES = tuple(range(1, 13))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def trace_digest(input_sha256: str, reply_sha256: str) -> str:
    payload = f"PipesTrace-v1\n{input_sha256}\n{reply_sha256}".encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def frozen_source_hashes(root: Path) -> tuple[dict[str, str], str]:
    manifest_path = root / "SOURCE_SHA256SUMS"
    manifest_hash = sha256_file(manifest_path)
    result: dict[str, str] = {}
    for line in manifest_path.read_text(encoding="ascii").splitlines():
        if not line.strip():
            continue
        digest, relative = line.split(maxsplit=1)
        result[relative.strip()] = digest
    for relative, expected in result.items():
        actual = sha256_file(root / relative)
        if actual != expected:
            raise RuntimeError(f"frozen source hash mismatch: {relative}")
    return result, manifest_hash


def _expected_synthetic_names(mode: str) -> set[str]:
    names = {"manifest.json"}
    for replicate in range(EVAL_REPLICATES):
        stem = f"{mode}-{replicate:02d}"
        names.update(
            {
                f"{stem}.in",
                f"{stem}.judge_output.txt",
                f"{stem}.metadata.json",
            }
        )
    return names


def synthetic_trace_paths(
    code_root: Path,
    dataset: str,
    source_manifest_hash: str,
    approved_manifest_hash: str,
) -> tuple[list[tuple[str, Path, Path]], list[dict[str, str]]]:
    mode = dataset.removeprefix("synthetic-")
    if mode not in {"independent", "grouped", "phase"}:
        raise ValueError(f"unknown synthetic mode: {mode}")
    eval_parent = code_root / "eval"
    expected_modes = {"independent", "grouped", "phase"}
    actual_modes = {path.name for path in eval_parent.iterdir()}
    if actual_modes != expected_modes or any(
        not (eval_parent / name).is_dir() for name in expected_modes
    ):
        raise RuntimeError(
            f"synthetic eval root must contain exactly three mode directories: "
            f"missing={sorted(expected_modes - actual_modes)}, "
            f"extra={sorted(actual_modes - expected_modes)}"
        )
    eval_root = eval_parent / mode
    expected_names = _expected_synthetic_names(mode)
    children = list(eval_root.iterdir())
    actual_names = {child.name for child in children}
    if actual_names != expected_names or any(not child.is_file() for child in children):
        raise RuntimeError(
            f"synthetic {mode} directory must contain exactly the preregistered files: "
            f"missing={sorted(expected_names - actual_names)}, "
            f"extra={sorted(actual_names - expected_names)}"
        )

    manifest_path = eval_root / "manifest.json"
    actual_manifest_hash = sha256_file(manifest_path)
    if actual_manifest_hash != approved_manifest_hash:
        raise RuntimeError(f"synthetic {mode} manifest SHA differs from reviewed SHA")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_stems = [f"{mode}-{replicate:02d}" for replicate in range(EVAL_REPLICATES)]
    if (
        manifest.get("protocol_version") != PROTOCOL_VERSION
        or manifest.get("mode") != mode
        or manifest.get("replicate_count") != EVAL_REPLICATES
        or manifest.get("epoch_count") != 156
        or manifest.get("grouped_log_odds_ratio") != GROUPED_LOG_OR
        or manifest.get("source_sha256s_sha256") != source_manifest_hash
        or manifest.get("expected_names") != sorted(expected_names)
    ):
        raise RuntimeError(f"synthetic {mode} manifest does not match the frozen protocol")
    entries = manifest.get("entries", [])
    if [entry.get("name") for entry in entries] != expected_stems:
        raise RuntimeError(f"synthetic {mode} manifest has an incorrect stream list")

    traces: list[tuple[str, Path, Path]] = []
    hashes: list[dict[str, str]] = []
    for replicate, entry in enumerate(entries):
        stem = expected_stems[replicate]
        expected_seed = 202610170000 + 1000 * (0 if mode == "independent" else 1 if mode == "grouped" else 2) + replicate
        if entry.get("seed") != expected_seed:
            raise RuntimeError(f"synthetic seed mismatch: {stem}")
        expected_files = {
            "input_file": f"{stem}.in",
            "reply_file": f"{stem}.judge_output.txt",
            "metadata_file": f"{stem}.metadata.json",
        }
        for key, expected_name in expected_files.items():
            if entry.get(key) != expected_name:
                raise RuntimeError(f"synthetic {stem} manifest has an unexpected {key}")
        input_path = eval_root / expected_files["input_file"]
        reply_path = eval_root / expected_files["reply_file"]
        metadata_path = eval_root / expected_files["metadata_file"]
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        actual_input = sha256_file(input_path)
        actual_reply = sha256_file(reply_path)
        actual_metadata = sha256_file(metadata_path)
        if actual_input != entry.get("input_sha256"):
            raise RuntimeError(f"synthetic input hash mismatch: {stem}")
        if actual_reply != entry.get("reply_sha256"):
            raise RuntimeError(f"synthetic reply hash mismatch: {stem}")
        if actual_metadata != entry.get("metadata_sha256"):
            raise RuntimeError(f"synthetic metadata hash mismatch: {stem}")
        if (
            metadata.get("mode") != mode
            or metadata.get("seed") != expected_seed
            or metadata.get("epochs") != 156
            or metadata.get("command_count") != 20_096
            or metadata.get("source_sha256") != FROZEN_SOURCE_SHA256
            or metadata.get("binary_sha256") != FROZEN_BINARY_SHA256
        ):
            raise RuntimeError(f"synthetic metadata differs from frozen protocol: {stem}")
        traces.append((stem, input_path, reply_path))
        hashes.append(
            {
                "name": stem,
                "input_sha256": actual_input,
                "reply_sha256": actual_reply,
                "trace_sha256": trace_digest(actual_input, actual_reply),
            }
        )
    return traces, hashes


def _expected_local_cases(repo: Path, dataset: str) -> list[tuple[str, str, str]]:
    if dataset == "open15":
        return [
            (
                f"open-{case:02d}",
                f"data/pipes/open/{case}.in",
                f"results/pipes/final/open-run-size-cohort-lanes/runs/{case}/judge_output.txt",
            )
            for case in OPEN_CASES
        ]
    if dataset == "holdout-v2":
        return [
            (
                f"case-{case:02d}",
                f"data/pipes/synthetic/final-holdout-v2/case-{case:02d}.in",
                f"results/pipes/final/holdout-run-size-cohort-lanes/runs/case-{case:02d}/judge_output.txt",
            )
            for case in HOLDOUT_CASES
        ]
    raise ValueError(f"unknown local dataset: {dataset}")


def _check_local_file_sets(repo: Path, dataset: str) -> None:
    expected = _expected_local_cases(repo, dataset)
    input_relatives = {item[1] for item in expected}
    reply_relatives = {item[2] for item in expected}
    input_root = repo / ("data/pipes/open" if dataset == "open15" else "data/pipes/synthetic/final-holdout-v2")
    reply_root = repo / (
        "results/pipes/final/open-run-size-cohort-lanes/runs"
        if dataset == "open15"
        else "results/pipes/final/holdout-run-size-cohort-lanes/runs"
    )
    actual_inputs = {
        path.relative_to(repo).as_posix() for path in input_root.rglob("*.in")
    }
    actual_replies = {
        path.relative_to(repo).as_posix() for path in reply_root.rglob("judge_output.txt")
    }
    if actual_inputs != input_relatives:
        raise RuntimeError(
            f"{dataset} input set differs: missing={sorted(input_relatives - actual_inputs)}, "
            f"extra={sorted(actual_inputs - input_relatives)}"
        )
    if actual_replies != reply_relatives:
        raise RuntimeError(
            f"{dataset} reply set differs: missing={sorted(reply_relatives - actual_replies)}, "
            f"extra={sorted(actual_replies - reply_relatives)}"
        )


def _official_local_input_hashes(repo: Path, dataset: str) -> tuple[str, dict[str, str]]:
    if dataset == "open15":
        manifest_path = repo / "results/pipes/final/open-run-size-cohort-lanes/cases.csv"
        with manifest_path.open("r", encoding="utf-8", newline="") as source:
            rows = list(csv.DictReader(source))
        if len(rows) != len(OPEN_CASES):
            raise RuntimeError("Open15 cases.csv must list exactly 15 cases")
        hashes: dict[str, str] = {}
        for row in rows:
            path = Path(row["test_file"])
            if not path.is_absolute():
                path = repo / path
            path = path.resolve()
            relative = path.relative_to(repo).as_posix()
            if relative in hashes:
                raise RuntimeError(f"duplicate Open15 case in cases.csv: {relative}")
            hashes[relative] = row["test_sha256"]
        if set(hashes) != {entry[1] for entry in _expected_local_cases(repo, dataset)}:
            raise RuntimeError("Open15 cases.csv has an unexpected exact file set")
        return manifest_path.relative_to(repo).as_posix(), hashes

    manifest_path = repo / "data/pipes/synthetic/final-holdout-v2/manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    rows = payload.get("per_case", [])
    if payload.get("case_count") != len(HOLDOUT_CASES) or len(rows) != len(HOLDOUT_CASES):
        raise RuntimeError("holdout manifest must list exactly 12 cases")
    hashes = {}
    for row in rows:
        path = Path(row["file"])
        if not path.is_absolute():
            path = repo / path
        relative = path.resolve().relative_to(repo).as_posix()
        if relative in hashes:
            raise RuntimeError(f"duplicate holdout case in manifest: {relative}")
        hashes[relative] = row["sha256"]
    if set(hashes) != {entry[1] for entry in _expected_local_cases(repo, dataset)}:
        raise RuntimeError("holdout manifest has an unexpected exact file set")
    return manifest_path.relative_to(repo).as_posix(), hashes


def _validate_local_manifest_shape(repo: Path, manifest: dict[str, object]) -> None:
    for dataset in ("open15", "holdout-v2"):
        expected_cases = _expected_local_cases(repo, dataset)
        source_manifest_rel, _ = _official_local_input_hashes(repo, dataset)
        frozen_dataset = manifest["datasets"].get(dataset)
        if not isinstance(frozen_dataset, dict):
            raise RuntimeError(f"local trace manifest is missing dataset {dataset}")
        if (
            frozen_dataset.get("source_case_manifest_file") != source_manifest_rel
            or frozen_dataset.get("source_case_manifest_sha256")
            != sha256_file(repo / source_manifest_rel)
            or frozen_dataset.get("case_count") != len(expected_cases)
        ):
            raise RuntimeError(f"{dataset} source manifest hash or case count changed")
        entries = frozen_dataset.get("cases", [])
        expected_names = [row[0] for row in expected_cases]
        if [entry.get("name") for entry in entries] != expected_names:
            raise RuntimeError(f"{dataset} frozen trace manifest has an incorrect case list")
        for expected, entry in zip(expected_cases, entries):
            if entry.get("input_file") != expected[1] or entry.get("reply_file") != expected[2]:
                raise RuntimeError(f"{dataset} frozen paths differ for {expected[0]}")


def local_trace_paths(
    repo: Path,
    dataset: str,
    code_root: Path,
    source_manifest_hash: str,
    approved_manifest_hash: str,
) -> tuple[list[tuple[str, Path, Path]], list[dict[str, str]]]:
    expected_cases = _expected_local_cases(repo, dataset)
    _check_local_file_sets(repo, dataset)
    manifest_path = code_root / "local-trace-manifest.json"
    if not manifest_path.is_file():
        raise RuntimeError("local-trace-manifest.json is not frozen; hash-freeze it before scoring")
    if sha256_file(manifest_path) != approved_manifest_hash:
        raise RuntimeError("local trace manifest SHA differs from reviewed SHA")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (
        manifest.get("protocol_version") != PROTOCOL_VERSION
        or manifest.get("source_sha256s_sha256") != source_manifest_hash
        or manifest.get("hashing_only_no_trace_parsing_or_scoring") is not True
        or set(manifest.get("datasets", {})) != {"open15", "holdout-v2"}
    ):
        raise RuntimeError("local trace manifest does not match frozen v3 source")
    _validate_local_manifest_shape(repo, manifest)

    source_manifest_rel, official_hashes = _official_local_input_hashes(repo, dataset)
    frozen_dataset = manifest["datasets"].get(dataset)
    entries = frozen_dataset.get("cases", [])

    traces: list[tuple[str, Path, Path]] = []
    hashes: list[dict[str, str]] = []
    for expected, entry in zip(expected_cases, entries):
        name, input_rel, reply_rel = expected
        if entry.get("input_file") != input_rel or entry.get("reply_file") != reply_rel:
            raise RuntimeError(f"{dataset} frozen paths differ for {name}")
        input_path = repo / input_rel
        reply_path = repo / reply_rel
        input_hash = sha256_file(input_path)
        reply_hash = sha256_file(reply_path)
        if input_hash != official_hashes[input_rel]:
            raise RuntimeError(f"{dataset} input differs from source case manifest: {name}")
        if input_hash != entry.get("input_sha256"):
            raise RuntimeError(f"{dataset} input hash differs from frozen trace manifest: {name}")
        if reply_hash != entry.get("reply_sha256"):
            raise RuntimeError(f"{dataset} reply hash differs from frozen trace manifest: {name}")
        combined_hash = trace_digest(input_hash, reply_hash)
        if combined_hash != entry.get("trace_sha256"):
            raise RuntimeError(f"{dataset} trace hash differs from frozen trace manifest: {name}")
        traces.append((name, input_path, reply_path))
        hashes.append(
            {
                "name": name,
                "input_sha256": input_hash,
                "reply_sha256": reply_hash,
                "trace_sha256": combined_hash,
            }
        )
    return traces, hashes


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset",
        choices=(
            "synthetic-independent",
            "synthetic-grouped",
            "synthetic-phase",
            "open15",
            "holdout-v2",
        ),
        required=True,
    )
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--approval-token", required=True)
    parser.add_argument("--approved-manifest-sha256", required=True)
    args = parser.parse_args()
    is_synthetic = args.dataset.startswith("synthetic-")
    expected_token = SYNTHETIC_APPROVAL_TOKEN if is_synthetic else LOCAL_APPROVAL_TOKEN
    if args.approval_token != expected_token:
        raise SystemExit("evaluation requires separate v3 approval for the selected data")

    code_root = Path(__file__).resolve().parent
    source_hashes, source_manifest_hash = frozen_source_hashes(code_root)
    repo = args.repo.resolve()
    if is_synthetic:
        trace_paths, trace_hashes = synthetic_trace_paths(
            code_root,
            args.dataset,
            source_manifest_hash,
            args.approved_manifest_sha256,
        )
    else:
        trace_paths, trace_hashes = local_trace_paths(
            repo,
            args.dataset,
            code_root,
            source_manifest_hash,
            args.approved_manifest_sha256,
        )

    # All expected names, manifests and raw file hashes are validated before the
    # first trace parser or metric is invoked.
    results = [evaluate_trace_pair(name, input_path, reply_path)
               for name, input_path, reply_path in trace_paths]
    payload = summarize_dataset(args.dataset, results)
    payload["protocol"] = PROTOCOL_VERSION
    payload["source_hashes"] = source_hashes
    payload["source_sha256s_sha256"] = source_manifest_hash
    payload["traces"] = trace_hashes
    write_summary(args.out / args.dataset / "summary.json", payload)


if __name__ == "__main__":
    main()
