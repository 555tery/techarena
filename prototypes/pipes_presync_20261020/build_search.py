"""Third bounded finalist: physical pre-sync search with shared scratch memory."""
import datetime,hashlib,json,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    parent=HERE/'symmetry-9';meta=json.loads((parent/'build.json').read_text());assert sha(parent/'solution.cpp')==meta['source_sha256']
    source=(parent/'solution.cpp').read_text()
    start=source.index('class Planner {');end=source.index('\n};\n}',start)+4
    planner=source[start:end]
    # Both planners execute sequentially. No layout node survives a planner
    # call; delayed probes retain independent Allocator snapshots only.
    planner=planner.replace('unique_ptr<Arena> arena;','shared_ptr<Arena> arena;').replace('unique_ptr<Memo> memo;','shared_ptr<Memo> memo;')
    planner=planner.replace('now-startCpu-usedCpu-currentSearch','now-startCpu-sharedSearchCpu-currentSearch')
    planner=planner.replace('if(!arena)arena=make_unique<Arena>();','if(!arena){arena=sharedArena.lock();if(!arena){arena=make_shared<Arena>();sharedArena=arena;}}')
    planner=planner.replace('if(!memo)memo=make_unique<Memo>();','if(!memo){memo=sharedMemo.lock();if(!memo){memo=make_shared<Memo>();sharedMemo=memo;}}')
    assert planner.count('usedCpu+=cpu()-begin')==3
    planner=planner.replace('usedCpu+=cpu()-begin','charge(cpu()-begin)')
    planner=planner.replace('    static double cpu()', '    void charge(double dt){usedCpu+=dt;sharedSearchCpu+=dt;}\n    static double cpu()')
    globals='static weak_ptr<Arena> sharedArena;static weak_ptr<Memo> sharedMemo;static double sharedSearchCpu=0;\n'
    source=source[:start]+globals+planner+source[end:]
    source=source.replace('  Allocator actual;size_t differing=0;bool coupled=false;',
      '  Allocator actual;size_t differing=0;bool coupled=false;unique_ptr<robust_search::Planner>physicalPlanner;unsigned physicalSearchChanges=0;')
    source=source.replace('   if(!parent.replayed&&!coupled&&differing&&!mirrorReady){',
      '''   if(!parent.replayed&&!coupled&&differing&&!physicalPlanner){
    physicalPlanner=make_unique<robust_search::Planner>();
    for(int previous:parent.observed)physicalPlanner->observe(previous);
   }
   if(!parent.replayed&&!coupled&&differing&&!mirrorReady){''')
    # Import only public commands already observed, and only on an actual
    # uncoupled branch. The virtual parent consumed the current command;
    # physical history is deliberately updated after choosing its placement.
    old='      return actual.bf(c);'
    new='''      if(!physicalPlanner)throw runtime_error("physical history missing");
      int bf=actual.bf(c),chosen=physicalPlanner->choose(actual,c,bf);
      if(chosen!=bf)++physicalSearchChanges;return chosen;'''
    assert old in source;source=source.replace(old,new)
    source=source.replace('   if(coupled&&!coverage.empty())throw runtime_error("coupling coverage");',
      '''   if(coupled&&!coverage.empty())throw runtime_error("coupling coverage");
   if(physicalPlanner){if(coupled)physicalPlanner.reset();else physicalPlanner->observe(c,actual.g.size());}''')
    source=source.replace('  parent.report();','''  parent.report();
  fprintf(stderr,"PHYSICAL_SEARCH committed=%u shared_scratch=1\\n",physicalSearchChanges);
  if(physicalPlanner){physicalPlanner->report();physicalPlanner->reportValidation();}''')
    out=HERE/'symmetry-9-search';out.mkdir(exist_ok=False);(out/'solution.cpp').write_text(source)
    cmd=['clang++','-std=c++20','-O2',str(out/'solution.cpp'),'-o',str(out/'solver')]
    result=subprocess.run(cmd,capture_output=True,text=True);(out/'compile.log').write_text(result.stdout+result.stderr);result.check_returncode()
    meta.update(source_sha256=sha(out/'solution.cpp'),binary_sha256=sha(out/'solver'),profile=out.name,
      build_command=cmd,built_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
      derivation_source_sha256=sha(parent/'solution.cpp'),shared_workspace='One80MiBArena and32MiBMemo shared sequentially; separate history/probes/confidence. Global process CPU and shared search-CPU accounting.',
      limitation='No universal pre-sync guarantee. Both planners consume the same global CPU budget and may change the timed virtual parent. Memo counters are shared diagnostic counters, not independent work counts.')
    (out/'build.json').write_text(json.dumps(meta,indent=2)+'\n');print(out.name,meta['source_sha256'],flush=True)
if __name__=='__main__':main()
