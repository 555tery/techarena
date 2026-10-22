"""Build an isolated solver; public tables and frozen ancestors remain untouched."""
import datetime
import hashlib
import json
import subprocess
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PARENT=ROOT/'prototypes/pipes_robust_round3_20261019/candidate-physical/solution.cpp'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    assert sha(PARENT)=='e7a88219417219faa925ec9d91641eb15d02aafeab76fdb9ef9d7144c7c25112'
    source=PARENT.read_text()
    marker='\nint main(){'
    index=source.rindex(marker)
    source=source[:index]+'\n'+(HERE/'planner.hpp').read_text()+source[index:]
    replacements={
      'vector<int>observed;observed.reserve(200000);':'vector<int>observed;observed.reserve(200000);robust_search::Planner planner;',
      'observed.push_back(c);fflush(stdout);++step;continue;':'observed.push_back(c);planner.observe(c,state.g.size());fflush(stdout);++step;continue;',
      'if(!answered){if(c>0)state.place(c,state.bf(c));else state.remove(-c);}':'if(!answered){if(c>0){int x=planner.choose(state,c,state.bf(c));state.place(c,x);}else state.remove(-c);}planner.observe(c,online?0:state.g.size());',
      'fprintf(stderr,"OPEN15_FULL_OVERFIT replay=':'planner.report();planner.reportMemo();planner.reportValidation();fprintf(stderr,"OPEN15_FULL_OVERFIT replay=',
    }
    for old,new in replacements.items():
        assert source.count(old)==1,old
        source=source.replace(old,new)
    source=source.replace('Any mismatch permanently switches to Best Fit from\n// the ACTUAL occupied layout.',
        'Any mismatch permanently exits public replay. Causal bounded search\n// compares alternatives with Best Fit from the ACTUAL occupied layout.')
    out=HERE/'candidate';out.mkdir(exist_ok=True)
    (out/'solution.cpp').write_text(source)
    result=subprocess.run(['clang++','-std=c++20','-O2','-Wall','-Wextra',str(out/'solution.cpp'),'-o',str(out/'solver')],capture_output=True,text=True)
    (out/'compile.log').write_text(result.stdout+result.stderr);result.check_returncode()
    metadata={'source_sha256':sha(out/'solution.cpp'),'binary_sha256':sha(out/'solver'),
       'parent_source_sha256':sha(PARENT),'public_tables_unchanged':True,
       'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
       'arena_cap_MiB':80,'memo_table_MiB':128,'planner_CPU_budget_s':3.4,'process_CPU_search_stop_s':4.1,
       'scenarios':64,'horizon':128,'logical_event_budget':12000000,
       'scenario_mix':'40 historical blocks, 8 no-deletion bursts, 16 changed deletion-rank probes',
       'acceptance':'no simulated final-trench regression on any paired scenario, >=3 historical wins, mean saving >=1m',
       'workspace_release':'on exhausted search budget or physical scale limit; scale exit after allocation is permanent',
       'CPU_reserve':'4.35s process envelope minus remaining_commands * max(16us, observed non-search CPU/command)',
       'causal_validation':'delayed128actualcommands, BF continuation on both same-state alternatives; confidence+2win,+1tie,-4loss; commit threshold4; cap8',
       'max_pending_physical_snapshots':8,
       'causal_inputs':'only actual observed commands, physical coordinates and deletion ranks'}
    (out/'build.json').write_text(json.dumps(metadata,indent=2)+'\n')
    print(json.dumps(metadata))
if __name__=='__main__':main()
