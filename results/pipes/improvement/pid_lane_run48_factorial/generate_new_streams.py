#!/usr/bin/env python3
"""Generate new, fixed Pipes streams using the archived causal generator."""
from __future__ import annotations
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE_GENERATOR = Path(__file__).resolve().parents[1] / "run48_synthetic_independent" / "generate_streams.py"
spec = importlib.util.spec_from_file_location("pipes_stream_generator", BASE_GENERATOR)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)

SCENARIOS = [
    {"name":"new_uniform_random_n50000", "operations":50000, "seed":62021,
     "phases":[{"start":0,"end":50000,"length_profile":"uniform","churn":0.42,"deletion_policy":"random","batch":0,"repeat_probability":0.02}]},
    {"name":"new_bimodal_oldest_n65000", "operations":65000, "seed":62039,
     "phases":[{"start":0,"end":65000,"length_profile":"bimodal","churn":0.46,"deletion_policy":"oldest","batch":400,"repeat_probability":0.75}]},
    {"name":"new_short_newest_n50000", "operations":50000, "seed":62057,
     "phases":[{"start":0,"end":50000,"length_profile":"short-heavy","churn":0.50,"deletion_policy":"newest","batch":384,"repeat_probability":0.20}]},
    {"name":"new_long_oldest_n70000", "operations":70000, "seed":62077,
     "phases":[{"start":0,"end":70000,"length_profile":"long-heavy","churn":0.42,"deletion_policy":"oldest","batch":480,"repeat_probability":0.32}]},
    {"name":"new_three_phase_shift_n100000", "operations":100000, "seed":62113,
     "phases":[
      {"start":0,"end":35000,"length_profile":"short-heavy","churn":0.35,"deletion_policy":"random","batch":320,"repeat_probability":0.15},
      {"start":35000,"end":70000,"length_profile":"long-heavy","churn":0.47,"deletion_policy":"newest","batch":600,"repeat_probability":0.28},
      {"start":70000,"end":100000,"length_profile":"uniform","churn":0.40,"deletion_policy":"longest","batch":0,"repeat_probability":0.03},
     ]},
    {"name":"new_delete_phase_shift_n120000", "operations":120000, "seed":62131,
     "phases":[
      {"start":0,"end":30000,"length_profile":"uniform","churn":0.38,"deletion_policy":"random","batch":500,"repeat_probability":0.05},
      {"start":30000,"end":60000,"length_profile":"bimodal","churn":0.52,"deletion_policy":"oldest","batch":300,"repeat_probability":0.72},
      {"start":60000,"end":90000,"length_profile":"long-heavy","churn":0.44,"deletion_policy":"newest","batch":420,"repeat_probability":0.12},
      {"start":90000,"end":120000,"length_profile":"short-heavy","churn":0.36,"deletion_policy":"longest","batch":0,"repeat_probability":0.20},
     ]},
]

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

outdir = ROOT / "inputs" / "new_seed_streams"
outdir.mkdir(parents=True, exist_ok=True)
if list(outdir.glob("*.in")):
    raise SystemExit("refusing to overwrite existing synthetic inputs")
records = {}
for scenario in SCENARIOS:
    commands, stats = module.generate(scenario)
    path = outdir / f"{scenario['name']}.in"
    path.write_text("\n".join([f"1.0 {len(commands)}", *map(str, commands), "0"]) + "\n", encoding="ascii")
    records[scenario["name"]] = {"path":str(path.relative_to(ROOT)),"sha256":sha(path),"scenario":scenario,"stream_stats":stats}

# Check exact input uniqueness against all existing repository .in files and the prior eight fresh streams.
known_hashes = {}
for base in (Path("data/pipes"), Path("results/pipes")):
    for path in base.rglob("*.in"):
        if path.resolve().is_relative_to(outdir.resolve()):
            continue
        try:
            known_hashes.setdefault(sha(path), str(path))
        except OSError:
            pass
collisions = {name:known_hashes[row["sha256"]] for name,row in records.items() if row["sha256"] in known_hashes}
if collisions:
    raise SystemExit(f"input hash collision with existing input(s): {collisions}")
manifest = {
 "purpose":"Six previously unused synthetic robustness streams for the frozen 2x2 policy comparison; seeds fixed before candidate runs.",
 "generation_rule":"Archived causal generator: current phase, seeded PRNG, active-pipe set and configured causal deletion policy; final command forced to placement.",
 "generator_path":str(BASE_GENERATOR),"generator_sha256":sha(BASE_GENERATOR),
 "this_script_sha256":sha(Path(__file__)),"weight_per_stream":1.0,
 "known_inputs_scanned":len(known_hashes),"hash_collisions":collisions,"inputs":records,
}
(ROOT / "new_synthetic_manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False,sort_keys=True)+"\n")
for name,row in records.items():
    s=row["stream_stats"]
    print(f"{name}: ops={s['operations']} placements={s['placements']} deletions={s['deletions']} peak_live={s['peak_live_pipes']} sha256={row['sha256']}")
print(f"unique against {len(known_hashes)} saved .in files; manifest={ROOT/'new_synthetic_manifest.json'}")
