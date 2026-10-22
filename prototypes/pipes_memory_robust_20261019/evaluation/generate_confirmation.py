#!/usr/bin/env python3
"""Create a blind confirmation catalog for the delayed-reliability hypothesis."""

from pathlib import Path

from generate_suite import ROOT, write_suite


HERE = Path(__file__).resolve().parent
OUT = HERE / "confirmation"

# The complete seed range and strata are fixed before generation. These inputs
# are independent of calibration and both existing sealed catalogs.
CONFIRMATION: list[dict] = [
    # Twelve ordinary, correlated, and regime-shift streams (12k–30k ops).
    {"id": "B01", "seed": 202610198001, "family": "ordinary-iid-uniform", "n": 12_000, "profile": "uniform", "delete": "random", "p_add": .50, "floor": 32, "cap": 800},
    {"id": "B02", "seed": 202610198002, "family": "ordinary-short-fifo", "n": 16_000, "profile": "short", "delete": "fifo", "p_add": .50, "floor": 32, "cap": 900},
    {"id": "B03", "seed": 202610198003, "family": "ordinary-long-lifo", "n": 20_000, "profile": "long", "delete": "lifo", "p_add": .50, "floor": 32, "cap": 1_000},
    {"id": "B04", "seed": 202610198004, "family": "ordinary-bimodal-young", "n": 24_000, "profile": "bimodal", "delete": "young", "p_add": .50, "floor": 32, "cap": 1_200},
    {"id": "B05", "seed": 202610198005, "family": "ordinary-walk-longest", "n": 28_000, "profile": "walk", "delete": "longest", "p_add": .50, "floor": 32, "cap": 1_600},
    {"id": "B06", "seed": 202610198006, "family": "shift-short-long-uniform", "n": 20_000, "profile_phases": ["short", "long", "uniform"], "delete": "random", "p_add_phases": [.52, .48, .52], "floor": 32, "cap": 1_000},
    {"id": "B07", "seed": 202610198007, "family": "shift-long-bimodal-short", "n": 24_000, "profile_phases": ["long", "bimodal", "short"], "delete": "young", "p_add": .50, "floor": 32, "cap": 1_400},
    {"id": "B08", "seed": 202610198008, "family": "shift-delete-fifo-lifo-random", "n": 30_000, "profile": "uniform", "delete_phases": ["fifo", "lifo", "random"], "p_add": .50, "floor": 32, "cap": 1_600},
    {"id": "B09", "seed": 202610198009, "family": "correlated-cohort-drain", "n": 24_000, "profile": "uniform", "delete": "random", "correlated": "cohort", "p_add": .52, "floor": 32, "cap": 900},
    {"id": "B10", "seed": 202610198010, "family": "correlated-size-band-regime", "n": 30_000, "profile_phases": ["short", "long", "bimodal"], "delete": "random", "correlated": "size-band", "p_add": .52, "floor": 32, "cap": 1_500},
    {"id": "B11", "seed": 202610198011, "family": "correlated-birth-era", "n": 28_000, "profile": "walk", "delete": "random", "correlated": "birth-era", "p_add": .52, "floor": 32, "cap": 1_200},
    {"id": "B12", "seed": 202610198012, "family": "correlated-length-plus-size-shift", "n": 30_000, "profile_phases": ["uniform", "long", "short"], "delete": "random", "correlated": "exact-length", "p_add_phases": [.52, .49, .53], "floor": 32, "cap": 1_800},

    # Eight exact Open15 prefixes, each followed by a fixed changed process.
    {"id": "B13", "seed": 202610198013, "family": "open-prefix-switch-case5", "n": 20_000, "prefix": {"case": 5, "ops": 3_000}, "profile": "short", "delete": "longest", "p_add": .51, "floor": 32, "cap": 1_200},
    {"id": "B14", "seed": 202610198014, "family": "open-prefix-switch-case8", "n": 24_000, "prefix": {"case": 8, "ops": 3_500}, "profile": "long", "delete": "fifo", "p_add": .52, "floor": 32, "cap": 1_200},
    {"id": "B15", "seed": 202610198015, "family": "open-prefix-switch-case9", "n": 30_000, "prefix": {"case": 9, "ops": 2_000}, "profile": "walk", "delete_phases": ["fifo", "random", "young"], "p_add": .51, "floor": 32, "cap": 1_400},
    {"id": "B16", "seed": 202610198016, "family": "open-prefix-switch-case10", "n": 30_000, "prefix": {"case": 10, "ops": 1_000}, "profile": "bimodal", "delete": "random", "correlated": "size-band", "p_add": .52, "floor": 32, "cap": 1_400},
    {"id": "B17", "seed": 202610198017, "family": "open-prefix-switch-case11", "n": 36_000, "prefix": {"case": 11, "ops": 1_800}, "profile_phases": ["long", "short", "uniform"], "delete": "random", "p_add": .51, "floor": 32, "cap": 1_600},
    {"id": "B18", "seed": 202610198018, "family": "open-prefix-switch-case13", "n": 40_000, "prefix": {"case": 13, "ops": 3_000}, "profile": "uniform", "delete": "young", "correlated": "cohort", "p_add": .52, "floor": 32, "cap": 1_200},
    {"id": "B19", "seed": 202610198019, "family": "open-prefix-switch-case14", "n": 50_000, "prefix": {"case": 14, "ops": 1_200}, "profile_phases": ["short", "long", "uniform"], "delete_phases": ["fifo", "young", "random"], "p_add": .51, "floor": 32, "cap": 1_800},
    {"id": "B20", "seed": 202610198020, "family": "open-prefix-switch-case15", "n": 60_000, "prefix": {"case": 15, "ops": 1_000}, "profile_phases": ["long", "short", "bimodal"], "delete": "random", "correlated": "exact-length", "p_add": .52, "floor": 32, "cap": 1_600},

    # Four 200k resource stresses: high live set, small live set, many gaps,
    # and a regime/correlation that activates only in the final quarter.
    {"id": "B21", "seed": 202610198021, "family": "stress-200k-high-live", "n": 200_000, "profile": "uniform", "delete": "random", "p_add": .50, "floor": 5_200, "cap": 7_000},
    {"id": "B22", "seed": 202610198022, "family": "stress-200k-small-live", "n": 200_000, "profile": "short", "delete": "young", "correlated": "size-band", "p_add": .50, "floor": 32, "cap": 128},
    {"id": "B23", "seed": 202610198023, "family": "stress-200k-regime-many-gaps", "n": 200_000, "profile_phases": ["long", "short", "long", "short"], "delete_phases": ["fifo", "young", "fifo", "random"], "p_add_phases": [.53, .48, .53, .49], "floor": 900, "cap": 1_600},
    {"id": "B24", "seed": 202610198024, "family": "stress-200k-late-activation", "n": 200_000, "profile_phases": ["uniform", "uniform", "uniform", "short"], "delete_phases": ["random", "random", "random", "fifo"], "correlated_phases": [None, None, None, "exact-length"], "p_add_phases": [.50, .50, .50, .52], "floor": 32, "cap": 1_500},
]


def main() -> None:
    if OUT.exists():
        raise SystemExit("Refusing to overwrite evaluation/confirmation.")
    assert len(CONFIRMATION) == 24
    assert [x["seed"] for x in CONFIRMATION] == list(range(202610198001, 202610198025))
    assert all(12_000 <= x["n"] <= 30_000 for x in CONFIRMATION[:12])
    assert all(20_000 <= x["n"] <= 60_000 and "prefix" in x for x in CONFIRMATION[12:20])
    assert all(x["n"] == 200_000 for x in CONFIRMATION[20:])
    write_suite(OUT, CONFIRMATION, sealed=True, suite_suffix="-confirmation")
    print(f"confirmation: {len(CONFIRMATION)} fixed inputs, {sum(x['n'] for x in CONFIRMATION)} operations, structurally checked")
    print("No solver, harness, or KPI evaluation was run.")


if __name__ == "__main__":
    main()
