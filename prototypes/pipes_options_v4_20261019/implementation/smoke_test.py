#!/usr/bin/env python3
"""Tiny handmade correctness/export fixtures only; no experimental evaluation."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

HERE=Path(__file__).resolve().parent

def run(args,**kwargs):
    return subprocess.run(list(map(str,args)),check=True,text=True,capture_output=True,**kwargs)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    report={"schema":"pipes-options-v4-smoke","scope":"tiny handmade fixtures only; no real teacher/fit/evaluation wave"}
    run(["make","-j2"],cwd=HERE)
    with tempfile.TemporaryDirectory(prefix="options-v4-smoke-") as temp:
        temp=Path(temp)
        run(["c++","-O2","-std=c++17","-Wall","-Wextra","-Wpedantic",HERE/"smoke.cpp","-o",temp/"smoke"])
        report["policy"]=json.loads(run([temp/"smoke"]).stdout)
        fixture=temp/"tiny.in"
        commands=[7,7,6,-2,5,-1,-3,15]
        fixture.write_text("1 8\n"+"\n".join(map(str,commands))+"\n0\n")
        anchored=temp/"anchored.hpp"
        anchored.write_text('#pragma once\n#include <array>\nnamespace options_v4 {\ninline constexpr bool ModelTrained=true;\ninline constexpr const char* ModelProvenance="handmade-smoke-only";\ninline std::array<double,4> predict(const std::array<float,128>&){return {{0,0,0,1}};}\n}\n')
        for name in ["teacher","solver"]:
            run(["c++","-O2","-std=c++17",f'-DMODEL_HEADER="{anchored}"',HERE/(name+".cpp"),"-o",temp/name])
        run([temp/"teacher","--input",fixture,"--output",temp/"labels.jsonl","--stats",temp/"stats.json"])
        stats=json.loads((temp/"stats.json").read_text())
        labels=[json.loads(s) for s in (temp/"labels.jsonl").read_text().splitlines()]
        solver=run([temp/"solver"],input="\n".join(map(str,commands))+"\n0\n")
        replies=solver.stdout.splitlines()
        placements=[list(map(int,replies[p["command_index"]].split())) for p in stats["rollin_witness"]]
        assert placements==[[p["digs"],p["start"]] for p in stats["rollin_witness"]]
        assert stats["rollin_final_trench"]==20 and stats["rollin_counters"]["active_crossed_deletions"]==1
        assert labels[0]["options"][3]["cost"]==20
        assert all(len(row["features"])==128 and len(row["gains"])==4 for row in labels)
        report["teacher_runtime"]={"status":"pass","model":"handmade constant anchored selector","labeled_states":len(labels),"rollin_placement_replies_equal":True,"final_trench":20,"rollin_counters":stats["rollin_counters"]}
        # Test exporter on artificial feature/cost rows, not teacher or real data.
        rows=[]
        for i in range(32):
            x=[0.]*128;x[0]=i/31.
            costs=[40,40,40,40 if i<16 else 20]
            rows.append({"schema":"pipes-options-v4","feature_schema":"causal_state128_bf_v1","observable_key":f"handmade-{i}","features":x,"gains":[(40-c)/20 for c in costs],"options":[{"index":j,"cost":c,"reference_cost":40} for j,c in enumerate(costs)]})
        rows.extend([rows[0]]*3)
        labeldir=temp/"artificial-labels";labeldir.mkdir()
        (labeldir/"fixture.jsonl").write_text("".join(json.dumps(r)+"\n" for r in rows))
        model=temp/"artificial-model"
        fit=json.loads(run([sys.executable,"-B",HERE/"train.py","--labels-dir",labeldir,"--out",model]).stdout)
        assert fit["label_states"]==35 and fit["observable_groups"]==32 and fit["depth"]==1
        report["export_parity"]=json.loads(run([sys.executable,"-B",HERE/"parity.py","--model-dir",model]).stdout)
        report["artificial_fit"]={k:fit[k] for k in ["label_states","observable_groups","ties","depth","node_count"]}
    report["status"]="pass"
    (HERE/"smoke_report.json").write_text(json.dumps(report,indent=2)+"\n")
    sources={p.name:sha(p) for p in sorted(HERE.iterdir()) if p.is_file() and (p.suffix in {".cpp",".hpp",".py",".md"} or p.name=="Makefile")}
    manifest={"schema":"pipes-options-v4-implementation-manifest","source_hashes_sha256":sources,"smoke_report_sha256":sha(HERE/"smoke_report.json"),"copied_primitive_source":"prototypes/pipes_hindsight_v3_20261019/implementation/allocator.hpp","default_model":"untrained-BF","real_training_or_evaluation":False}
    (HERE/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    print(json.dumps(report))

if __name__=="__main__":
    main()
