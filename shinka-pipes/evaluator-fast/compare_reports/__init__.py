"""Compare saved old/fast SEARCH-v2 evaluator reports without rerunning them.

This module reads only report JSON, the SEARCH-v2 manifest, and each reported
``judge_output.txt`` transcript. It never opens a suite ``.in`` file.

Public API::

    compare(old_dir: Path, fast_dir: Path, manifest: dict, suite: Path) -> dict

The returned mapping has stable top-level keys ``schema_version``, ``ok``,
``scope``, ``counts``, ``identity``, ``score``, ``resources``, ``artifacts``,
and ``mismatches``. Mismatch entries use ``scope``, ``field``, ``reason``,
``old``, and ``fast``; fields that do not apply are ``None``.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
SEARCH_V2_SUITE = ROOT.parent / "search-v2" / "task" / "data" / "search"

CPU_LIMIT_S = 5.0
RSS_LIMIT_MIB = 256.0
EXPECTED_CASES = 128
EXPECTED_FAMILIES = 16
CASES_PER_FAMILY = 8

RESOURCE_FIELDS = {
    "wall_orchestration_s",
    "solver_cpu_user_s",
    "solver_cpu_system_s",
    "solver_cpu_total_s",
    "solver_peak_rss_mb",
    "interactor_cpu_user_s",
    "interactor_cpu_system_s",
    "interactor_cpu_total_s",
    "interactor_peak_rss_mb",
}

SUMMARY_SCORE_FIELDS = (
    "weighted_score_sum",
    "weight_sum",
    "mean_kpi_upper_bound_from_live_volume",
    "mean_kpi_fraction_of_bound",
    "worst_relative_regret_vs_bound",
    "mean_lower_bound_to_actual_trench_ratio",
    "min_lower_bound_to_actual_trench_ratio",
    "mean_trench_to_lower_bound_ratio",
)

SUMMARY_MEASUREMENT_FIELDS = (
    "cpu_measurement",
    "rss_measurement",
    "wall_measurement",
)

# The harness label is a run annotation: the reference and fast wrappers use
# different names while executing the same evaluation contract.
RUN_LABEL_FIELDS = {"strategy"}

REQUIRED_DETERMINISTIC_RECORD_FIELDS = {
    "test_sha256", "operation_count", "placement_count", "peak_live_pipe_length_m",
    "minimum_trench_lower_bound_m", "final_occupied_length_m",
    "kpi_upper_bound_from_live_volume", "case", "test_file", "status", "detail",
    "judge_commands_seen_including_final_zero", "occupied_length_m", "trench_length_m",
    "kpi", "weighted_score", "official_weight", "fraction_of_bound",
    "lower_bound_to_actual_trench_ratio", "candidate_stderr", "interactor_stderr",
    "strategy", "cpu_limit_s", "memory_limit_mb", "solver_cpu_limit_exceeded",
    "solver_memory_limit_exceeded", "judge_output_file",
}

METRIC_SCORE_FIELDS = (
    "combined_score",
    "suite",
    "corpus_version",
    "family_scores",
    "fitness_definition",
)

METRIC_PUBLIC_SCORE_FIELDS = (
    "valid_cases",
    "family_count",
    "worst_family_score",
    "mean_raw_kpi",
)


def _json_safe(value: Any) -> Any:
    """Keep mismatch values serializable, including malformed NaN/Inf inputs."""
    if isinstance(value, float) and not math.isfinite(value):
        return repr(value)
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return repr(value)


def _add_mismatch(
    mismatches: list[dict[str, Any]], scope: str, field: str, reason: str,
    old: Any = None, fast: Any = None,
) -> None:
    mismatches.append({
        "scope": scope,
        "field": field,
        "reason": reason,
        "old": _json_safe(old),
        "fast": _json_safe(fast),
    })


def _read_json(path: Path, label: str, mismatches: list[dict[str, Any]]) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        _add_mismatch(mismatches, label, str(path), f"cannot read JSON: {exc}")
        return None


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def _valid_sha(value: Any) -> bool:
    return (isinstance(value, str) and len(value) == 64
            and all(ch in "0123456789abcdef" for ch in value.lower()))


def _ratio(old: float, fast: float) -> float | None:
    return old / fast if fast > 0 else None


def _diff(old: float, fast: float) -> float:
    """Signed delta: fast minus old."""
    return fast - old


def _load_run(label: str, directory: Path, mismatches: list[dict[str, Any]]) -> dict[str, Any]:
    root = Path(directory)
    metrics = _read_json(root / "metrics.json", label, mismatches)
    correct = _read_json(root / "correct.json", label, mismatches)
    summary = _read_json(root / "harness" / "summary.json", label, mismatches)
    return {
        "directory": str(root.resolve()),
        "metrics": metrics if isinstance(metrics, dict) else {},
        "correct": correct if isinstance(correct, dict) else {},
        "summary": summary if isinstance(summary, dict) else {},
    }


def _expected_case_map(
    manifest: dict[str, Any], suite: Path, mismatches: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], list[str], list[str]]:
    cases = manifest.get("cases")
    families = manifest.get("families")
    if not isinstance(cases, list):
        _add_mismatch(mismatches, "manifest", "cases", "must be a list", fast=cases)
        return {}, [], []
    if not isinstance(families, list) or any(not isinstance(f, str) for f in families):
        _add_mismatch(mismatches, "manifest", "families", "must be a list of strings", fast=families)
        families = []
    if (manifest.get("split") != "search" or manifest.get("version") != "search-v2"
            or manifest.get("case_count") != EXPECTED_CASES
            or manifest.get("cases_per_family") != CASES_PER_FAMILY
            or len(families) != EXPECTED_FAMILIES or len(set(families)) != len(families)
            or len(cases) != EXPECTED_CASES):
        _add_mismatch(
            mismatches, "manifest", "SEARCH-v2 contract",
            "expected SEARCH-v2 with 128 cases and 16 families of 8",
            fast={"split": manifest.get("split"), "version": manifest.get("version"),
                  "case_count": manifest.get("case_count"),
                  "cases_per_family": manifest.get("cases_per_family"),
                  "family_count": len(families), "case_rows": len(cases)},
        )

    counts = {family: 0 for family in families}
    expected: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(cases):
        if not isinstance(item, dict):
            _add_mismatch(mismatches, "manifest", f"cases[{index}]", "must be an object", fast=item)
            continue
        name, family, sha = item.get("file"), item.get("family"), item.get("sha256")
        if (not isinstance(name, str) or Path(name).name != name or not name.endswith(".in")
                or not isinstance(family, str) or family not in counts or not _valid_sha(sha)):
            _add_mismatch(mismatches, "manifest", f"cases[{index}]", "invalid file/family/SHA row", fast=item)
            continue
        case_id = Path(name).stem
        if case_id in expected:
            _add_mismatch(mismatches, "manifest", name, "duplicate case filename", fast=item)
            continue
        expected[case_id] = item
        counts[family] += 1

    wrong_counts = {family: count for family, count in counts.items() if count != CASES_PER_FAMILY}
    if wrong_counts:
        _add_mismatch(mismatches, "manifest", "family coverage",
                      "each SEARCH-v2 family must have exactly 8 cases", fast=wrong_counts)
    expected_paths = [str((suite / item["file"]).resolve()) for item in expected.values()]
    expected_names = [item["file"] for item in expected.values()]
    return expected, expected_names, expected_paths


def _validate_report(
    label: str,
    run: dict[str, Any],
    expected: dict[str, dict[str, Any]],
    expected_names: list[str],
    expected_paths: list[str],
    suite: Path,
    mismatches: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    metrics = run["metrics"]
    correctness = run["correct"]
    summary = run["summary"]

    if correctness.get("correct") is not True:
        _add_mismatch(mismatches, label, "correct.json.correct", "must be true",
                      fast=correctness.get("correct"))

    records = summary.get("records")
    if not isinstance(records, list):
        _add_mismatch(mismatches, label, "harness.records", "must be a list",
                      fast=summary.get("records"))
        records = []
    if len(records) != EXPECTED_CASES:
        _add_mismatch(mismatches, label, "harness.record_count", "must be exactly 128",
                      fast=len(records))
    if summary.get("case_count") != EXPECTED_CASES:
        _add_mismatch(mismatches, label, "harness.case_count", "must be 128",
                      fast=summary.get("case_count"))
    if summary.get("ok_count") != EXPECTED_CASES:
        _add_mismatch(mismatches, label, "harness.ok_count", "must be 128",
                      fast=summary.get("ok_count"))
    if summary.get("is_official_open_test_set") is not False:
        _add_mismatch(mismatches, label, "harness.is_official_open_test_set",
                      "SEARCH-v2 must not be identified as Open15",
                      fast=summary.get("is_official_open_test_set"))
    for field in SUMMARY_MEASUREMENT_FIELDS:
        value = summary.get(field)
        if not isinstance(value, str) or not value.strip():
            _add_mismatch(mismatches, label, f"harness.{field}",
                          "measurement definition must be a nonempty string", fast=value)

    actual_tests = summary.get("tests")
    if not isinstance(actual_tests, list):
        _add_mismatch(mismatches, label, "harness.tests", "must be a list",
                      fast=actual_tests)
    else:
        normalized = []
        for value in actual_tests:
            try:
                normalized.append(str(Path(value).resolve()))
            except (TypeError, OSError):
                normalized.append(None)
        if len(normalized) != EXPECTED_CASES or len(set(normalized)) != EXPECTED_CASES or set(normalized) != set(expected_paths):
            _add_mismatch(mismatches, label, "harness.tests",
                          "must list each fixed SEARCH-v2 file exactly once",
                          fast={"count": len(normalized), "unique": len(set(normalized)),
                                "matches_manifest": set(normalized) == set(expected_paths)})

    by_case: dict[str, dict[str, Any]] = {}
    transcript_hashes: dict[str, str] = {}
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            _add_mismatch(mismatches, label, f"harness.records[{index}]", "must be an object", fast=record)
            continue
        case = record.get("case")
        if not isinstance(case, str) or case not in expected:
            _add_mismatch(mismatches, label, f"harness.records[{index}].case",
                          "unexpected case", fast=case)
            continue
        if case in by_case:
            _add_mismatch(mismatches, label, f"case[{case}]", "duplicate report record")
            continue
        by_case[case] = record
        spec = expected[case]
        file_name = spec["file"]
        if case != Path(file_name).stem:
            _add_mismatch(mismatches, label, f"manifest.{file_name}.case",
                          "case id must match file stem", fast=case)
        if record.get("test_sha256") != spec["sha256"]:
            _add_mismatch(mismatches, label, f"case[{case}].test_sha256",
                          "does not match SEARCH-v2 manifest", fast=record.get("test_sha256"))
        try:
            actual_file = str(Path(record.get("test_file", "")).resolve())
        except (TypeError, OSError):
            actual_file = ""
        expected_file = str((suite / file_name).resolve())
        if actual_file != expected_file:
            _add_mismatch(mismatches, label, f"case[{case}].test_file",
                          "must point to the fixed SEARCH-v2 file", fast=actual_file)
        if record.get("status") != "ok":
            _add_mismatch(mismatches, label, f"case[{case}].status", "must be ok",
                          fast=record.get("status"))
        for field in REQUIRED_DETERMINISTIC_RECORD_FIELDS:
            if field not in record:
                _add_mismatch(mismatches, label, f"case[{case}].{field}",
                              "required deterministic field is missing")

        for field in RESOURCE_FIELDS:
            number = _finite_number(record.get(field))
            if number is None or number < 0:
                _add_mismatch(mismatches, label, f"case[{case}].{field}",
                              "must be finite and nonnegative", fast=record.get(field))
        solver_cpu = _finite_number(record.get("solver_cpu_total_s"))
        solver_rss = _finite_number(record.get("solver_peak_rss_mb"))
        if solver_cpu is not None and solver_cpu >= CPU_LIMIT_S:
            _add_mismatch(mismatches, label, f"case[{case}].solver_cpu_total_s",
                          "must remain below the 5 s limit", fast=solver_cpu)
        if solver_rss is not None and solver_rss >= RSS_LIMIT_MIB:
            _add_mismatch(mismatches, label, f"case[{case}].solver_peak_rss_mb",
                          "must remain below the 256 MiB limit", fast=solver_rss)
        if record.get("solver_cpu_limit_exceeded") is not False:
            _add_mismatch(mismatches, label, f"case[{case}].solver_cpu_limit_exceeded",
                          "must be false", fast=record.get("solver_cpu_limit_exceeded"))
        if record.get("solver_memory_limit_exceeded") is not False:
            _add_mismatch(mismatches, label, f"case[{case}].solver_memory_limit_exceeded",
                          "must be false", fast=record.get("solver_memory_limit_exceeded"))
        if record.get("cpu_limit_s") != CPU_LIMIT_S:
            _add_mismatch(mismatches, label, f"case[{case}].cpu_limit_s",
                          "must be the unchanged 5 s limit", fast=record.get("cpu_limit_s"))
        if record.get("memory_limit_mb") != RSS_LIMIT_MIB:
            _add_mismatch(mismatches, label, f"case[{case}].memory_limit_mb",
                          "must be the unchanged 256 MiB limit", fast=record.get("memory_limit_mb"))

        for prefix in ("solver", "interactor"):
            user = _finite_number(record.get(f"{prefix}_cpu_user_s"))
            system = _finite_number(record.get(f"{prefix}_cpu_system_s"))
            total = _finite_number(record.get(f"{prefix}_cpu_total_s"))
            if user is not None and system is not None and total is not None:
                if not math.isclose(user + system, total, rel_tol=0.0, abs_tol=1e-9):
                    _add_mismatch(mismatches, label, f"case[{case}].{prefix}_cpu_total_s",
                                  "does not equal user plus system CPU", fast=total)

        output_path_value = record.get("judge_output_file")
        try:
            run_root = Path(run["directory"]).resolve()
            expected_output = (run_root / "harness" / "runs" / case / "judge_output.txt").resolve(strict=True)
            output_path = Path(output_path_value).resolve(strict=True)
            if (not expected_output.is_relative_to(run_root)
                    or output_path != expected_output
                    or not output_path.is_file()):
                raise ValueError("path must resolve exactly to this run's harness/runs/<case>/judge_output.txt")
            transcript_hashes[case] = _sha256_file(output_path)
        except (TypeError, OSError) as exc:
            _add_mismatch(mismatches, label, f"case[{case}].judge_output_file",
                          f"cannot hash complete judge transcript: {exc}",
                          fast=output_path_value)
        except ValueError as exc:
            _add_mismatch(mismatches, label, f"case[{case}].judge_output_file",
                          str(exc), fast=output_path_value)

    if set(by_case) != set(expected):
        _add_mismatch(mismatches, label, "harness.case_coverage",
                      "report records must cover all manifest cases exactly once",
                      fast={"missing": sorted(set(expected) - set(by_case)),
                            "unexpected_or_duplicate_count": max(0, len(records) - len(by_case))})

    if metrics.get("suite") != "search" or metrics.get("corpus_version") != "search-v2":
        _add_mismatch(mismatches, label, "metrics suite/version",
                      "must identify SEARCH-v2",
                      fast={"suite": metrics.get("suite"), "corpus_version": metrics.get("corpus_version")})
    if "error" in metrics:
        _add_mismatch(mismatches, label, "metrics.error", "successful baseline report must have no error",
                      fast=metrics.get("error"))
    for field in ("combined_score",):
        number = _finite_number(metrics.get(field))
        if number is None:
            _add_mismatch(mismatches, label, f"metrics.{field}", "must be finite", fast=metrics.get(field))
    family_scores = metrics.get("family_scores")
    expected_families = {spec["family"] for spec in expected.values()}
    if not isinstance(family_scores, dict) or set(family_scores) != expected_families:
        _add_mismatch(mismatches, label, "metrics.family_scores",
                      "must contain exactly all 16 SEARCH-v2 families", fast=family_scores)
    elif any(_finite_number(value) is None for value in family_scores.values()):
        _add_mismatch(mismatches, label, "metrics.family_scores", "all scores must be finite", fast=family_scores)
    public = metrics.get("public")
    if not isinstance(public, dict):
        _add_mismatch(mismatches, label, "metrics.public", "must be an object", fast=public)
        public = {}
    for field in ("max_solver_cpu_seconds", "max_solver_rss_mib"):
        if _finite_number(public.get(field)) is None:
            _add_mismatch(mismatches, label, f"metrics.public.{field}",
                          "must be finite", fast=public.get(field))
    cpu_values = [_finite_number(record.get("solver_cpu_total_s")) for record in by_case.values()]
    rss_values = [_finite_number(record.get("solver_peak_rss_mb")) for record in by_case.values()]
    if cpu_values and all(value is not None for value in cpu_values):
        reported = _finite_number(public.get("max_solver_cpu_seconds"))
        if reported is not None and not math.isclose(reported, max(cpu_values), rel_tol=0.0, abs_tol=1e-12):
            _add_mismatch(mismatches, label, "metrics.public.max_solver_cpu_seconds",
                          "must match the maximum fresh per-case solver CPU", fast=reported)
    if rss_values and all(value is not None for value in rss_values):
        reported = _finite_number(public.get("max_solver_rss_mib"))
        if reported is not None and not math.isclose(reported, max(rss_values), rel_tol=0.0, abs_tol=1e-12):
            _add_mismatch(mismatches, label, "metrics.public.max_solver_rss_mib",
                          "must match the maximum fresh per-case solver RSS", fast=reported)

    return by_case, transcript_hashes


def compare(old_dir: Path, fast_dir: Path, manifest: dict, suite: Path) -> dict[str, Any]:
    """Compare old and selector transports on saved baseline reports.

    ``suite`` must be the fixed SEARCH-v2 directory. Only its ``manifest.json``
    is read; no ``.in`` streams are opened. Both reports must contain all 128
    cases, each input hash must match the supplied manifest, and each complete
    judge transcript is hashed independently.
    """
    mismatches: list[dict[str, Any]] = []
    suite = Path(suite).resolve()
    canonical_suite = SEARCH_V2_SUITE.resolve()
    if suite != canonical_suite:
        _add_mismatch(mismatches, "scope", "suite_path",
                      "only the fixed SEARCH-v2 directory is allowed",
                      old=str(canonical_suite), fast=str(suite))
        # Fail closed before probing a wrong suite path, especially a
        # Validation or Open15 directory.
        return {
            "schema_version": 1,
            "ok": False,
            "scope": {"suite": "SEARCH-v2", "suite_path": str(suite),
                      "expected_cases": EXPECTED_CASES,
                      "expected_families": EXPECTED_FAMILIES,
                      "cases_per_family": CASES_PER_FAMILY},
            "counts": {"manifest_cases": 0, "manifest_families": 0,
                       "old_records": 0, "fast_records": 0,
                       "old_unique_cases": 0, "fast_unique_cases": 0,
                       "paired_cases": 0, "deterministic_fields_compared": 0,
                       "deterministic_fields_per_case": 0,
                       "cases_with_identical_deterministic_fields": 0,
                       "transcripts_compared": 0, "transcripts_identical": 0},
            "identity": {"sha256": {}, "manifest_sha256_expected": None,
                         "snapshot_sha256_expected": None,
                         "source_hashes_may_differ": {}},
            "score": {"old": None, "fast": None,
                      "combined_score_delta_fast_minus_old": None, "equal": False},
            "resources": {"old": None, "fast": None,
                          "deltas_fast_minus_old": {},
                          "speedups_old_over_fast": {},
                          "per_case": {}, "per_family": {}},
            "artifacts": {"per_case": {}, "run_metadata": {}},
            "mismatches": mismatches,
        }

    manifest_path = suite / "manifest.json"
    try:
        manifest_bytes = manifest_path.read_bytes()
        manifest_sha = hashlib.sha256(manifest_bytes).hexdigest()
        disk_manifest = json.loads(manifest_bytes.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        manifest_sha = None
        disk_manifest = None
        _add_mismatch(mismatches, "manifest", str(manifest_path), f"cannot read SEARCH manifest: {exc}")
    if isinstance(disk_manifest, dict) and disk_manifest != manifest:
        _add_mismatch(mismatches, "manifest", "provided_manifest",
                      "must exactly match the fixed SEARCH-v2 manifest on disk")

    expected, expected_names, expected_paths = _expected_case_map(manifest, suite, mismatches)
    old = _load_run("old", Path(old_dir), mismatches)
    fast = _load_run("fast", Path(fast_dir), mismatches)
    old_records, old_transcripts = _validate_report(
        "old", old, expected, expected_names, expected_paths, suite, mismatches)
    fast_records, fast_transcripts = _validate_report(
        "fast", fast, expected, expected_names, expected_paths, suite, mismatches)

    old_metrics, fast_metrics = old["metrics"], fast["metrics"]
    hashes: dict[str, dict[str, Any]] = {}
    for field in ("program_sha256", "manifest_sha256", "snapshot_sha256"):
        old_value, fast_value = old_metrics.get(field), fast_metrics.get(field)
        valid = _valid_sha(old_value) and _valid_sha(fast_value)
        equal = valid and old_value == fast_value
        hashes[field] = {"old": old_value, "fast": fast_value, "equal": equal}
        if not valid:
            _add_mismatch(mismatches, "identity", field, "both values must be SHA-256 hex digests",
                          old=old_value, fast=fast_value)
        elif not equal:
            _add_mismatch(mismatches, "identity", field, "must match between evaluators",
                          old=old_value, fast=fast_value)
    if manifest_sha is not None:
        for label, metrics in (("old", old_metrics), ("fast", fast_metrics)):
            if metrics.get("manifest_sha256") != manifest_sha:
                _add_mismatch(mismatches, label, "metrics.manifest_sha256",
                              "must match the fixed SEARCH-v2 manifest file",
                              fast=metrics.get("manifest_sha256"))
    snapshot_path = suite.parents[2] / "snapshot.json"
    try:
        actual_snapshot_sha = _sha256_file(snapshot_path)
    except OSError as exc:
        actual_snapshot_sha = None
        _add_mismatch(mismatches, "identity", "snapshot_sha256",
                      f"cannot hash fixed support snapshot: {exc}")
    if actual_snapshot_sha is not None:
        for label, metrics in (("old", old_metrics), ("fast", fast_metrics)):
            if metrics.get("snapshot_sha256") != actual_snapshot_sha:
                _add_mismatch(mismatches, label, "metrics.snapshot_sha256",
                              "must match the fixed SEARCH-v2 support snapshot",
                              fast=metrics.get("snapshot_sha256"))

    # Evaluator and transport sources are expected to differ. Keep their SHAs
    # visible in the report but deliberately do not require equality.
    source_hashes = {
        "evaluator_sha256": {"old": old_metrics.get("evaluator_sha256"),
                             "fast": fast_metrics.get("evaluator_sha256")},
        "transport_sha256": {"old": old_metrics.get("transport_sha256"),
                             "fast": fast_metrics.get("transport_sha256")},
    }

    for field in METRIC_SCORE_FIELDS:
        old_value, fast_value = old_metrics.get(field), fast_metrics.get(field)
        if old_value != fast_value:
            _add_mismatch(mismatches, "metrics", field, "score definition/result must be identical",
                          old=old_value, fast=fast_value)
    old_public = old_metrics.get("public") if isinstance(old_metrics.get("public"), dict) else {}
    fast_public = fast_metrics.get("public") if isinstance(fast_metrics.get("public"), dict) else {}
    for field in METRIC_PUBLIC_SCORE_FIELDS:
        if old_public.get(field) != fast_public.get(field):
            _add_mismatch(mismatches, "metrics.public", field, "deterministic score summary must be identical",
                          old=old_public.get(field), fast=fast_public.get(field))
    for field in SUMMARY_SCORE_FIELDS:
        old_value, fast_value = old["summary"].get(field), fast["summary"].get(field)
        if old_value != fast_value:
            _add_mismatch(mismatches, "harness.summary", field, "deterministic summary must be identical",
                          old=old_value, fast=fast_value)
    for field in SUMMARY_MEASUREMENT_FIELDS:
        old_value, fast_value = old["summary"].get(field), fast["summary"].get(field)
        if not isinstance(old_value, str) or not old_value.strip():
            _add_mismatch(mismatches, "harness.summary", field,
                          "old measurement definition must be a nonempty string", old=old_value)
        if not isinstance(fast_value, str) or not fast_value.strip():
            _add_mismatch(mismatches, "harness.summary", field,
                          "fast measurement definition must be a nonempty string", fast=fast_value)
        if old_value != fast_value:
            _add_mismatch(mismatches, "harness.summary", field,
                          "measurement definition must be identical", old=old_value, fast=fast_value)
    deterministic_compared = 0
    paired = 0
    matching_deterministic_cases = 0
    equal_transcripts = 0
    case_comparison: dict[str, dict[str, Any]] = {}
    artifact_paths: dict[str, dict[str, Any]] = {}
    all_fields = set()
    for case in expected:
        old_record, fast_record = old_records.get(case), fast_records.get(case)
        if old_record is None or fast_record is None:
            continue
        paired += 1
        dynamic = RESOURCE_FIELDS
        keys = (set(old_record) | set(fast_record)) - dynamic
        # All per-case artifact paths are reported separately. The input path
        # remains part of case identity and is checked against the manifest.
        path_keys = {key for key in keys if key.endswith("_file") and key != "test_file"}
        deterministic_keys = keys - path_keys - RUN_LABEL_FIELDS
        case_equal = True
        for field in sorted(deterministic_keys):
            deterministic_compared += 1
            all_fields.add(field)
            old_value, fast_value = old_record.get(field), fast_record.get(field)
            if old_value != fast_value:
                case_equal = False
                _add_mismatch(mismatches, f"case[{case}]", field,
                              "deterministic per-case value must be identical",
                              old=old_value, fast=fast_value)
        if case_equal:
            matching_deterministic_cases += 1

        old_hash, fast_hash = old_transcripts.get(case), fast_transcripts.get(case)
        transcript_equal = old_hash is not None and old_hash == fast_hash
        if transcript_equal:
            equal_transcripts += 1
        else:
            _add_mismatch(mismatches, f"case[{case}]", "judge_output_sha256",
                          "complete official-checker transcript SHA-256 must match",
                          old=old_hash, fast=fast_hash)

        artifact_paths[case] = {
            "old": {key: old_record.get(key) for key in sorted(path_keys)},
            "fast": {key: fast_record.get(key) for key in sorted(path_keys)},
            "judge_output_sha256": {"old": old_hash, "fast": fast_hash,
                                    "equal": transcript_equal},
        }
        spec = expected[case]
        timing: dict[str, Any] = {"family": spec["family"]}
        metric_pairs = (
            ("wall_orchestration_s", "wall"),
            ("solver_cpu_total_s", "solver_cpu"),
            ("interactor_cpu_total_s", "interactor_cpu"),
            ("solver_peak_rss_mb", "solver_rss_mib"),
            ("interactor_peak_rss_mb", "interactor_rss_mib"),
        )
        for field, key in metric_pairs:
            old_num = _finite_number(old_record.get(field))
            fast_num = _finite_number(fast_record.get(field))
            timing[key] = {
                "old": old_num,
                "fast": fast_num,
                "delta_fast_minus_old": (fast_num - old_num) if old_num is not None and fast_num is not None else None,
                "speedup_old_over_fast": _ratio(old_num, fast_num) if old_num is not None and fast_num is not None else None,
            }
        case_comparison[case] = timing

    old_resource = _summarize_resources(old_records)
    fast_resource = _summarize_resources(fast_records)
    family_resource = _family_speedups(expected, old_records, fast_records)
    resources = {
        "old": old_resource,
        "fast": fast_resource,
        "deltas_fast_minus_old": {
            field: (fast_resource[field] - old_resource[field])
            for field in ("wall_sum_s", "solver_cpu_sum_s", "interactor_cpu_sum_s", "all_child_cpu_sum_s")
            if old_resource.get(field) is not None and fast_resource.get(field) is not None
        },
        "speedups_old_over_fast": {
            field: _ratio(old_resource[field], fast_resource[field])
            for field in ("wall_sum_s", "solver_cpu_sum_s", "interactor_cpu_sum_s", "all_child_cpu_sum_s")
            if old_resource.get(field) is not None and fast_resource.get(field) is not None
        },
        "per_case": case_comparison,
        "per_family": family_resource,
    }

    score = {
        "old": _score_summary(old_metrics, old["correct"]),
        "fast": _score_summary(fast_metrics, fast["correct"]),
        "combined_score_delta_fast_minus_old": _finite_number(fast_metrics.get("combined_score"))
        - _finite_number(old_metrics.get("combined_score"))
        if _finite_number(fast_metrics.get("combined_score")) is not None
        and _finite_number(old_metrics.get("combined_score")) is not None else None,
        "equal": all(old_metrics.get(field) == fast_metrics.get(field) for field in METRIC_SCORE_FIELDS)
        and all(old_public.get(field) == fast_public.get(field) for field in METRIC_PUBLIC_SCORE_FIELDS)
        and old["correct"].get("correct") == fast["correct"].get("correct") is True,
    }

    return {
        "schema_version": 1,
        "ok": not mismatches,
        "scope": {
            "suite": "SEARCH-v2",
            "suite_path": str(suite),
            "expected_cases": EXPECTED_CASES,
            "expected_families": EXPECTED_FAMILIES,
            "cases_per_family": CASES_PER_FAMILY,
        },
        "counts": {
            "manifest_cases": len(expected),
            "manifest_families": len(manifest.get("families", [])) if isinstance(manifest.get("families"), list) else 0,
            "old_records": len(old["summary"].get("records", [])) if isinstance(old["summary"].get("records"), list) else 0,
            "fast_records": len(fast["summary"].get("records", [])) if isinstance(fast["summary"].get("records"), list) else 0,
            "old_unique_cases": len(old_records),
            "fast_unique_cases": len(fast_records),
            "paired_cases": paired,
            "deterministic_fields_compared": deterministic_compared,
            "deterministic_fields_per_case": len(all_fields),
            "cases_with_identical_deterministic_fields": matching_deterministic_cases,
            "transcripts_compared": sum(case in old_records and case in fast_records for case in expected),
            "transcripts_identical": equal_transcripts,
        },
        "identity": {
            "sha256": hashes,
            "manifest_sha256_expected": manifest_sha,
            "snapshot_sha256_expected": actual_snapshot_sha,
            "source_hashes_may_differ": source_hashes,
        },
        "score": score,
        "resources": resources,
        "artifacts": {
            "per_case": artifact_paths,
            "run_metadata": {
                label: {
                    "strategy": run["summary"].get("strategy"),
                    "solver_argv": run["summary"].get("solver_argv"),
                    "interactor": run["summary"].get("interactor"),
                }
                for label, run in (("old", old), ("fast", fast))
            },
        },
        "mismatches": mismatches,
    }


def _score_summary(metrics: dict[str, Any], correct: dict[str, Any]) -> dict[str, Any]:
    public = metrics.get("public") if isinstance(metrics.get("public"), dict) else {}
    return {
        "correct": correct.get("correct"),
        "combined_score": _finite_number(metrics.get("combined_score")),
        "family_scores": metrics.get("family_scores"),
        "fitness_definition": metrics.get("fitness_definition"),
        "public": {key: public.get(key) for key in (*METRIC_PUBLIC_SCORE_FIELDS,
                                                     "max_solver_cpu_seconds", "max_solver_rss_mib")},
    }


def _summarize_resources(records: dict[str, dict[str, Any]]) -> dict[str, Any]:
    fields = {
        "wall_orchestration_s": "wall_sum_s",
        "solver_cpu_total_s": "solver_cpu_sum_s",
        "interactor_cpu_total_s": "interactor_cpu_sum_s",
    }
    values = {
        field: [number for record in records.values()
                if (number := _finite_number(record.get(field))) is not None]
        for field in (*fields, "solver_cpu_total_s", "interactor_cpu_total_s",
                      "solver_peak_rss_mb", "interactor_peak_rss_mb")
    }
    output: dict[str, Any] = {key: sum(values[field]) for field, key in fields.items()}
    output["all_child_cpu_sum_s"] = output["solver_cpu_sum_s"] + output["interactor_cpu_sum_s"]
    output["max_solver_cpu_s"] = max(values["solver_cpu_total_s"], default=None)
    output["max_interactor_cpu_s"] = max(values["interactor_cpu_total_s"], default=None)
    output["max_solver_rss_mib"] = max(values["solver_peak_rss_mb"], default=None)
    output["max_interactor_rss_mib"] = max(values["interactor_peak_rss_mb"], default=None)
    output["resource_rows"] = min(len(v) for v in values.values()) if values else 0
    output["cases"] = len(records)
    return output


def _family_speedups(
    expected: dict[str, dict[str, Any]],
    old_records: dict[str, dict[str, Any]],
    fast_records: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    families = sorted({spec["family"] for spec in expected.values()})
    result: dict[str, Any] = {}
    for family in families:
        cases = [case for case, spec in expected.items()
                 if spec["family"] == family and case in old_records and case in fast_records]
        old_wall = [number for case in cases
                    if (number := _finite_number(old_records[case].get("wall_orchestration_s"))) is not None]
        fast_wall = [number for case in cases
                     if (number := _finite_number(fast_records[case].get("wall_orchestration_s"))) is not None]
        old_cpu = [number for case in cases
                   if (number := _finite_number(old_records[case].get("solver_cpu_total_s"))) is not None]
        fast_cpu = [number for case in cases
                    if (number := _finite_number(fast_records[case].get("solver_cpu_total_s"))) is not None]
        old_wall_sum, fast_wall_sum = sum(old_wall), sum(fast_wall)
        old_cpu_sum, fast_cpu_sum = sum(old_cpu), sum(fast_cpu)
        result[family] = {
            "cases": len(cases),
            "old_wall_sum_s": old_wall_sum,
            "fast_wall_sum_s": fast_wall_sum,
            "wall_delta_fast_minus_old_s": fast_wall_sum - old_wall_sum,
            "wall_speedup_old_over_fast": _ratio(old_wall_sum, fast_wall_sum),
            "old_solver_cpu_sum_s": old_cpu_sum,
            "fast_solver_cpu_sum_s": fast_cpu_sum,
            "solver_cpu_delta_fast_minus_old_s": fast_cpu_sum - old_cpu_sum,
            "solver_cpu_speedup_old_over_fast": _ratio(old_cpu_sum, fast_cpu_sum),
        }
    return result
