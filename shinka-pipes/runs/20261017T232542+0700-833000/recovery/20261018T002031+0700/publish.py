"""Publish authorized saved-source reevaluations without creating new candidate generations."""
from pathlib import Path
import datetime,hashlib,json,sqlite3,sys,uuid
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT))
from shinka.database import Program
RECOVERY=Path(__file__).resolve().parent
RUN=RECOVERY.parents[1]
report=json.loads((RECOVERY/"reevaluation.json").read_text())
if report["status"]!="complete" or [r["generation"] for r in report["results"]]!=[3,4,8,9,10]:raise RuntimeError("All five reevaluations must finish before publication")
if (RECOVERY/"publication.json").exists():raise FileExistsError("Already published; refusing duplicate accounting")
con=sqlite3.connect(RUN/"programs.sqlite");con.row_factory=sqlite3.Row
before_count=con.execute("select count(*) from programs").fetchone()[0]
if before_count!=9:raise RuntimeError("Unexpected pre-repair program count")
now=datetime.datetime.now(ZoneInfo("Asia/Novosibirsk"));outcome={"status":"preparing","total_generation_budget":20,"results":[],"terminal_slots":[],"validation_accessed":False,"open15_accessed":False}
con.execute("BEGIN IMMEDIATE")
for item in report["results"]:
 generation=item["generation"];directory=Path(item["results_dir"]);metrics=json.loads((directory/"metrics.json").read_text());correct=json.loads((directory/"correct.json").read_text())["correct"]
 row=con.execute("select * from programs where generation=?",(generation,)).fetchone()
 if row is None or row["correct"] or row["combined_score"]!=0:raise RuntimeError("Unexpected row at publication")
 source=RUN/f"gen_{generation}/main.cpp"
 if source.read_text()!=row["code"] or hashlib.sha256(source.read_bytes()).hexdigest()!=item["source_sha256"]:raise RuntimeError("Source changed during reevaluation")
 meta=json.loads(row["metadata"]);meta["reevaluation"]={"at":now.isoformat(),"reason":"false immutable-source rejection: optional EOF newline removed by Shinka diff applier","previous_correct":False,"previous_score":0,"previous_stdout_log":meta.get("stdout_log"),"previous_stderr_log":meta.get("stderr_log"),"results_dir":str(directory),"source_sha256":item["source_sha256"],"evaluator_sha256":hashlib.sha256((ROOT/"synthetic_eval.py").read_bytes()).hexdigest(),"search_manifest_sha256":metrics.get("manifest_sha256"),"elapsed_seconds":item["elapsed_seconds"],"new_correct":correct,"new_score":metrics["combined_score"],"independent_audit_passed":item.get("independent_audit_passed",False)}
 meta["stdout_log"]=f"Reevaluated saved generation {generation}: correct={correct}, score={metrics['combined_score']}; details: {directory}"
 meta["stderr_log"]="" if correct else metrics.get("error","")
 con.execute("update programs set correct=?,combined_score=?,public_metrics=?,private_metrics=?,text_feedback=?,metadata=? where id=?",(correct,metrics["combined_score"],json.dumps(metrics.get("public",{})),json.dumps(metrics.get("private",{})),metrics.get("text_feedback",metrics.get("error","")),json.dumps(meta),row["id"]))
 if correct:con.execute("insert or ignore into archive(program_id) values(?)",(row["id"],))
 outcome["results"].append({"generation":generation,"id":row["id"],"correct":correct,"score":metrics["combined_score"]})
# Three original terminal failures and the interrupted, already-issued proposal
# consume their original IDs, rather than granting extra model proposals.
parent0=con.execute("select id from programs where generation=0 and island_idx=0").fetchone()[0]
for generation in [1,5,6,11]:
 path=RUN/f"gen_{generation}/failure.json"
 if generation==11:
  f={"generation":11,"failure_stage":"proposal","failure_class":"interrupted_by_user_for_evaluator_repair","failure_reason":"User stopped the in-flight proposal to repair evaluator; no returned response/candidate. Original slot consumed to preserve total budget20.","parent_id":parent0,"api_costs":0.0,"cost_status":"not_reported_for_interrupted_request","timestamp":now.isoformat(),"downstream_eval_submitted":False,"generated_code_available":False,"patch_type":"diff","patch_name":"interrupted_for_repair"}
 else:f=json.loads(path.read_text())
 parent=con.execute("select island_idx from programs where id=?",(f.get("parent_id"),)).fetchone();island=parent[0] if parent else 0
 timestamp=datetime.datetime.fromisoformat(f["timestamp"])
 if timestamp.tzinfo is None:timestamp=timestamp.replace(tzinfo=ZoneInfo("Asia/Novosibirsk"))
 metadata={**f,"node_kind":"failed_proposal","failure_persisted":True,"failure_json_path":str(path),"budget_slot_consumed":True,"restored_to_programs_during_repair":True,"source_job_id":f"failed:{f.get('failure_stage','proposal')}:{generation}","api_costs":float(f.get("api_costs",0)),"embed_cost":float(f.get("embed_cost",0)),"novelty_cost":float(f.get("novelty_cost",0))}
 program=Program(id=str(uuid.uuid5(uuid.NAMESPACE_URL,f"{RUN}:terminal:{generation}")),code="",language="cpp",parent_id=f.get("parent_id"),archive_inspiration_ids=f.get("archive_inspiration_ids",[]),top_k_inspiration_ids=f.get("top_k_inspiration_ids",[]),island_idx=island,generation=generation,timestamp=timestamp.timestamp(),correct=False,text_feedback=f["failure_reason"],metadata=metadata)
 data=program.to_dict();columns=[r[1] for r in con.execute("pragma table_info(programs)") if r[1] in data]
 json_fields={"archive_inspiration_ids","top_k_inspiration_ids","public_metrics","private_metrics","embedding","embedding_pca_2d","embedding_pca_3d","migration_history","metadata"}
 values=[json.dumps(data[k]) if k in json_fields else data[k] for k in columns]
 con.execute("insert into programs("+",".join(columns)+") values("+",".join("?" for _ in columns)+")",values)
 if program.parent_id:con.execute("update programs set children_count=children_count+1 where id=?",(program.parent_id,))
 outcome["terminal_slots"].append({"generation":generation,"id":program.id,"reason":f["failure_class"]})
best=con.execute("select id,generation,combined_score from programs where correct=1 order by combined_score desc,timestamp asc limit 1").fetchone()
for key,value in (("last_iteration","11"),("best_program_id",best["id"]),("best_score_ever",str(best["combined_score"])),("best_score_generation",str(best["generation"]))):con.execute("insert or replace into metadata_store(key,value) values(?,?)",(key,value))
ids=[r[0] for r in con.execute("select distinct generation from programs order by generation")]
if ids!=list(range(12)) or con.execute("select count(*) from programs").fetchone()[0]!=13:raise RuntimeError("Budget/generation consistency failure")
if con.execute("select count(*) from archive").fetchone()[0]>20:raise RuntimeError("Archive capacity exceeded")
con.commit();con.close()
# Publish reports at their original generation locations; original reports remain
# preserved in gen_N-results-before, and full new reports stay in reevaluations/.
import shutil
for item in report["results"]:shutil.copytree(item["results_dir"],RUN/f"gen_{item['generation']}/results",dirs_exist_ok=True)
path=RUN/"gen_11/failure.json";path.parent.mkdir(exist_ok=True)
path.write_text(json.dumps({"generation":11,"failure_class":"interrupted_by_user_for_evaluator_repair","failure_stage":"proposal","failure_reason":"Interrupted by user to repair evaluator; budget slot preserved as consumed.","downstream_eval_submitted":False,"generated_code_available":False,"parent_id":parent0,"api_costs":0,"cost_status":"not_reported_for_interrupted_request","timestamp":now.isoformat()},indent=2)+"\n")
outcome.update(status="committed",published_at=now.isoformat(),consumed_generation_slots=12,remaining_generation_slots=8,next_generation=12,best=dict(best),row_count=13)
(RECOVERY/"publication.json").write_text(json.dumps(outcome,indent=2)+"\n")
print(json.dumps(outcome,indent=2))
