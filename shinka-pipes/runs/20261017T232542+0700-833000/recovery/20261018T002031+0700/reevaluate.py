"""Authorized reevaluation of saved false EOF rejects; fixed SEARCH-v1 only."""
from pathlib import Path
import datetime,hashlib,json,sqlite3,sys,time
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT))
from synthetic_eval import evaluate,aggregate_report,SEARCH
RECOVERY=Path(__file__).resolve().parent
RUN=RECOVERY.parents[1]
GENERATIONS=(3,4,8,9,10)
manifest=json.loads((SEARCH/"manifest.json").read_text())
conn=sqlite3.connect("file:"+str(RUN/"programs.sqlite")+"?mode=ro",uri=True)
report={"status":"running","generations":list(GENERATIONS),"scope":"SEARCH-v1 only","model_requests":0,"validation_accessed":False,"open15_accessed":False,"results":[]}
def save():
 (RECOVERY/"reevaluation.json").write_text(json.dumps(report,indent=2)+"\n")
save()
for generation in GENERATIONS:
 source=RUN/f"gen_{generation}/main.cpp"
 row=conn.execute("select code from programs where generation=?",(generation,)).fetchone()
 if not row or source.read_text()!=row[0]:raise RuntimeError(f"Saved source differs from DB at generation {generation}")
 target=RECOVERY/f"reevaluations/gen_{generation}"
 if target.exists():raise FileExistsError(target)
 before=hashlib.sha256(source.read_bytes()).hexdigest()
 print(f"START generation={generation}",flush=True)
 started=time.monotonic()
 correct=evaluate(source,target)
 metrics=json.loads((target/"metrics.json").read_text())
 item={"generation":generation,"correct":correct,"score":metrics.get("combined_score"),"error":metrics.get("error"),"results_dir":str(target),"source_sha256":before,"elapsed_seconds":time.monotonic()-started}
 if "error" not in metrics:
  summary=json.loads((target/"harness/summary.json").read_text())
  computed,ok=aggregate_report(summary,manifest,SEARCH,0)
  if not ok or computed["combined_score"]!=metrics["combined_score"]:raise RuntimeError("Independent score audit failed")
  if metrics["program_sha256"]!=before:raise RuntimeError("Source provenance mismatch")
  item["valid_cases"]=metrics["public"]["valid_cases"]
  item["independent_audit_passed"]=True
 if hashlib.sha256(source.read_bytes()).hexdigest()!=before:raise RuntimeError("Saved source modified")
 report["results"].append(item);save()
 print("DONE "+json.dumps(item),flush=True)
report["status"]="complete";save();conn.close()
