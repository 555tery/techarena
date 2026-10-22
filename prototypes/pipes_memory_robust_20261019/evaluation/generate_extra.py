#!/usr/bin/env python3
"""Build the separate sealed-final-extra catalog; never touches the first final set."""

from pathlib import Path

from generate_suite import ROOT, write_suite


HERE = Path(__file__).resolve().parent
EXTRA_DIR = HERE / "sealed-final-extra"

# Fixed strata and seeds selected before generation, with no solver outcomes.
EXTRA: list[dict] = [
    {"id": "E01", "seed": 940201, "family": "iid-uniform-random", "n": 12_000, "profile": "uniform", "delete": "random", "p_add": .50, "floor": 32, "cap": 600},
    {"id": "E02", "seed": 940202, "family": "short-fifo-survival", "n": 18_000, "profile": "short", "delete": "fifo", "p_add": .50, "floor": 32, "cap": 1_200},
    {"id": "E03", "seed": 940203, "family": "long-longest-first", "n": 24_000, "profile": "long", "delete": "longest", "p_add": .50, "floor": 32, "cap": 1_600},
    {"id": "E04", "seed": 940204, "family": "bimodal-shortest-first", "n": 30_000, "profile": "bimodal", "delete": "shortest", "p_add": .50, "floor": 32, "cap": 2_000},
    {"id": "E05", "seed": 940205, "family": "walk-size-young-delete", "n": 40_000, "profile": "walk", "delete": "young", "p_add": .51, "floor": 32, "cap": 1_500},
    {"id": "E06", "seed": 940206, "family": "size-regime-short-long-uniform", "n": 32_000, "profile_phases": ["short", "long", "uniform"], "delete": "random", "p_add_phases": [.52, .48, .52], "floor": 32, "cap": 1_200},
    {"id": "E07", "seed": 940207, "family": "lifetime-regime-fifo-random-lifo", "n": 36_000, "profile_phases": ["long", "bimodal", "short"], "delete_phases": ["fifo", "random", "lifo"], "p_add": .50, "floor": 32, "cap": 1_800},
    {"id": "E08", "seed": 940208, "family": "correlated-cohort-drain", "n": 28_000, "profile": "uniform", "delete": "random", "correlated": "cohort", "p_add": .52, "floor": 32, "cap": 800},
    {"id": "E09", "seed": 940209, "family": "correlated-size-band-with-regime-shift", "n": 36_000, "profile_phases": ["short", "long", "bimodal"], "delete": "random", "correlated": "size-band", "p_add": .52, "floor": 32, "cap": 1_400},
    {"id": "E10", "seed": 940210, "family": "correlated-birth-era-switching-profile", "n": 40_000, "profile_phases": ["uniform", "long", "short", "uniform"], "delete": "random", "correlated": "birth-era", "p_add_phases": [.52, .49, .53, .50], "floor": 32, "cap": 2_000},
    {"id": "E11", "seed": 940211, "family": "open-prefix-switch-case5", "n": 20_000, "prefix": {"case": 5, "ops": 2_000}, "profile": "short", "delete": "longest", "p_add": .51, "floor": 32, "cap": 1_000},
    {"id": "E12", "seed": 940212, "family": "open-prefix-switch-case8", "n": 24_000, "prefix": {"case": 8, "ops": 6_000}, "profile": "long", "delete": "young", "p_add": .52, "floor": 32, "cap": 1_200},
    {"id": "E13", "seed": 940213, "family": "open-prefix-switch-case9", "n": 30_000, "prefix": {"case": 9, "ops": 1_500}, "profile": "walk", "delete_phases": ["shortest", "fifo", "random"], "p_add": .51, "floor": 32, "cap": 1_200},
    {"id": "E14", "seed": 940214, "family": "open-prefix-switch-case11", "n": 32_000, "prefix": {"case": 11, "ops": 1_400}, "profile": "bimodal", "delete": "random", "correlated": "cohort", "p_add": .52, "floor": 32, "cap": 1_400},
    {"id": "E15", "seed": 940215, "family": "open-prefix-switch-case14", "n": 36_000, "prefix": {"case": 14, "ops": 1_800}, "profile_phases": ["short", "long", "uniform"], "delete": "fifo", "p_add": .51, "floor": 32, "cap": 1_800},
    {"id": "E16", "seed": 940216, "family": "open-prefix-switch-case15", "n": 40_000, "prefix": {"case": 15, "ops": 1_500}, "profile_phases": ["long", "short", "bimodal"], "delete": "random", "correlated": "exact-length", "p_add": .52, "floor": 32, "cap": 1_600},
]


def main() -> None:
    if EXTRA_DIR.exists():
        raise SystemExit("Refusing to overwrite sealed-final-extra.")
    write_suite(EXTRA_DIR, EXTRA, sealed=True, suite_suffix="-extra")
    total_ops = sum(item["n"] for item in EXTRA)
    print(f"sealed-final-extra: {len(EXTRA)} fixed inputs, {total_ops} operations, structurally checked")
    print("No solver or KPI evaluation was run. The original sealed-final directory was not touched.")


if __name__ == "__main__":
    main()
