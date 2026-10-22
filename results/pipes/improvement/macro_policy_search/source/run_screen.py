#!/usr/bin/env python3
"""Run state-stratified macro blocks under the official interactive harness."""
import concurrent.futures
import csv
import hashlib
import json
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[5]
BASE=ROOT/"results/pipes/final/open-run-size-cohort-lanes"
PLAN=ROOT/"results/pipes/improvement/macro_policy_search/analysis/block_plan.json"
SOLVER=ROOT/"results/pipes/improvement/macro_policy_search/bin/macro_policy_runner"
INTERACTOR=ROOT/"results/pipes/final/bin/interactor"
HARNESS=ROOT/"tools/pipes_harness.py"
OUT=ROOT/"results/pipes/improvement/macro_policy_search/runs/blocks"
POLICIES={1:"first_fit",2:"tail_first",3:"tail_only",4:"no_cohort"}
plan=json.loads(PLAN.read_text())
jobs=[]
for i,b in enumerate(plan["blocks"],1):
  for pid,pname in POLICIES.items():
    run_id=f"b{i:02d}-c{b['case']}-o{b['block_start_op']}-n{b['block_length']}-{pname}"
    out=OUT/run_id
    solver=f"{SOLVER} {pid} {b['block_start_op']} {b['block_end_op']}"
    cmd=["python3",str(HARNESS),"--solver",solver,"--interactor",str(INTERACTOR),
      "--tests",str(ROOT/f"data/pipes/open/{b['case']}.in"),"--out",str(out),
      "--name",run_id,"--cpu-limit","5","--memory-limit-mb","256","--wall-timeout","120"]
    jobs.append((run_id,b,pid,pname,out,cmd))

def run(job):
  run_id,b,pid,pname,out,cmd=job
  p=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True)
  (out/"harness.stdout.txt").write_text(p.stdout)
  (out/"harness.stderr.txt").write_text(p.stderr)
  summary_path=out/"summary.json"
  summary=json.loads(summary_path.read_text()) if summary_path.exists() else {}
  r=(summary.get("records") or [{}])[0]
  input_path=ROOT/f"data/pipes/open/{b['case']}.in"
  output_path=out/f"runs/{b['case']}/judge_output.txt"
  rec={
    "run_id":run_id,"case":b["case"],"block_start_op":b["block_start_op"],
    "block_end_op":b["block_end_op"],"block_length":b["block_length"],
    "selection_stratum":b["selection_stratum"],"start_state":b["start_state"],
    "policy_id":pid,"policy":pname,"harness_exit_code":p.returncode,
    "status":r.get("status"),"baseline_trench_m":None,"candidate_trench_m":r.get("trench_length_m"),
    "candidate_kpi":r.get("kpi"),"candidate_weighted_score":r.get("weighted_score"),
    "candidate_cpu_s":r.get("solver_cpu_total_s"),"candidate_rss_mib":r.get("solver_peak_rss_mb"),
    "input_sha256":hashlib.sha256(input_path.read_bytes()).hexdigest(),
    "output_sha256":hashlib.sha256(output_path.read_bytes()).hexdigest() if output_path.exists() else None,
    "official_replay_suffix_commands":max(0,summary.get("records",[{}])[0].get("operation_count",0)-b["block_end_op"]),
    "run_output_dir":str(out.relative_to(ROOT)),"harness_command":cmd
  }
  # Baseline values are taken from the checked-in final run manifest.
  manifest=json.loads((ROOT/"results/pipes/final/manifest.json").read_text())
  base=next(x for x in manifest["open15"]["per_case"] if x["case"]==str(b["case"]))
  rec["baseline_trench_m"]=base["trench_length_m"]
  rec["baseline_weighted_score"]=base["weighted_score"]
  rec["delta_trench_m"]=(rec["candidate_trench_m"]-rec["baseline_trench_m"] if rec["candidate_trench_m"] is not None else None)
  rec["delta_weighted_score"]=(rec["candidate_weighted_score"]-rec["baseline_weighted_score"] if rec["candidate_weighted_score"] is not None else None)
  return rec,p.stdout,p.stderr

OUT.mkdir(parents=True,exist_ok=True)
results=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
  futures={ex.submit(run,j):j for j in jobs}
  for i,f in enumerate(concurrent.futures.as_completed(futures),1):
    j=futures[f]
    try:
      rec,stdout,stderr=f.result()
    except Exception as e:
      rec={"run_id":j[0],"case":j[1]["case"],"block_start_op":j[1]["block_start_op"],"block_length":j[1]["block_length"],"policy":j[3],"error":repr(e)}
      stdout=stderr=""
    results.append(rec)
    print(f"{i}/{len(jobs)} {rec.get('run_id')} status={rec.get('status',rec.get('error'))} dH={rec.get('delta_trench_m')} scoreΔ={rec.get('delta_weighted_score')} CPU={rec.get('candidate_cpu_s')}",flush=True)
results.sort(key=lambda r:r.get("run_id",""))
with (OUT/"variant_results.jsonl").open("w") as f:
  for r in results:f.write(json.dumps(r,sort_keys=True)+"\n")
fields=[]
for r in results:
  for k in r:
    if k not in fields:fields.append(k)
with (OUT/"variant_results.csv").open("w",newline="") as f:
  w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore");w.writeheader();w.writerows(results)
summary={
  "variants":len(results),"protocol_ok":sum(r.get("status")=="ok" for r in results),
  "policies":POLICIES,"cases":[5,9,15],"block_sizes":[256,512,1024,2048,4096],
  "source_sha256":hashlib.sha256((ROOT/"results/pipes/improvement/macro_policy_search/source/macro_policy_runner.cpp").read_bytes()).hexdigest(),
  "binary_sha256":hashlib.sha256(SOLVER.read_bytes()).hexdigest(),
  "baseline_source_sha256":hashlib.sha256((ROOT/"results/pipes/final/solution.cpp").read_bytes()).hexdigest(),
  "input_hashes":{str(c):hashlib.sha256((ROOT/f"data/pipes/open/{c}.in").read_bytes()).hexdigest() for c in (5,9,15)},
  "results":results
}
(OUT/"macro_screen_summary.json").write_text(json.dumps(summary,indent=2)+"\n")
print("FINISHED",len(results),"variants; protocol OK",summary["protocol_ok"],flush=True)
