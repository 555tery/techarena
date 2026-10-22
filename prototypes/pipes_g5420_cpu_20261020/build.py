"""Separate one-core Windows profile; never modify frozen generalization evidence."""
import datetime
import hashlib
import json
import subprocess
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PARENT=ROOT/'prototypes/pipes_memory_robust_20261019/causal-final/solution.cpp'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    assert sha(PARENT)=='41c487a7b1f303f7eefe2630986d1493ba728459a781560b53ae04fe63200aad'
    source=PARENT.read_text()
    needle='namespace robust_search {\n'
    assert source.count(needle)==1
    source=source.replace(needle,(HERE/'process_cpu.hpp').read_text()+'\n'+needle)
    edits={
      'double startCpu=double(clock())/CLOCKS_PER_SEC;':'double startCpu=pipes_cpu::seconds();',
      'static double cpu(){return double(clock())/CLOCKS_PER_SEC;}':'static double cpu(){return pipes_cpu::seconds();}',
      'static constexpr size_t count=1u<<21;':'static constexpr size_t count=1u<<PIPES_MEMO_BUCKET_LOG2;',
      'return 4.35-now-reserve;':'return kHardwareProcessEnvelope-now-reserve*kHardwareReserveSafety;',
      'usedCpu>3.4':'usedCpu>kHardwarePlannerCpu',
      'usedCpu+cpu()-begin>3.4':'usedCpu+cpu()-begin>kHardwarePlannerCpu',
      'cpu()>4.1':'cpu()>kHardwareSearchStopCpu',
    }
    for old,new in edits.items():
        assert old in source,old
        source=source.replace(old,new)
    source=source.replace('table_MiB=128 releases=', 'table_MiB=%u releases=')
    old='(unsigned long long)(savedStores+(memo?memo->stores:0)),releases,'
    assert old in source
    source=source.replace(old,'(unsigned long long)(savedStores+(memo?memo->stores:0)),unsigned((Memo::count*sizeof(MemoBucket))/1048576),releases,')
    source=source.replace('80 MiB node arena, 128 MiB memo, and delayed real-suffix probes.',
       '80 MiB node arena, configurable memo (32 MiB default), and delayed probes.')
    source=source.replace('// Two entries per cache line. LRU replacement retains recurring suffixes.',
       '// Two entries per cache line; compare 32/128 MiB on the actual target.')
    for name,bits in [('cache32',19),('cache128',21)]:
        out=HERE/name;out.mkdir(exist_ok=True);(out/'solution.cpp').write_text(source)
        argv=['clang++','-std=c++20','-O2',f'-DPIPES_MEMO_BUCKET_LOG2={bits}',str(out/'solution.cpp'),'-o',str(out/'solver')]
        r=subprocess.run(argv,capture_output=True,text=True);(out/'compile.log').write_text(r.stdout+r.stderr);r.check_returncode()
        meta={'source_sha256':sha(out/'solution.cpp'),'binary_sha256':sha(out/'solver'),'parent_source_sha256':sha(PARENT),
          'built_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'build_command':argv,'local_host_arch':'arm64; not G5420',
          'target':'Windows10 22H2 x64, Pentium Gold G5420, one worker/core','target_benchmark_performed':False,
          'cpu_accounting':'GetProcessTimes(user+kernel) on Windows; getrusage(user+system) on POSIX; never wall time or divide by cores',
          'memo_MiB':(1<<bits)*64/1048576,'arena_cap_MiB':80,'planner_cpu_budget_s':2.5,
          'search_stop_cpu_s':3.8,'process_envelope_s':4.0,'remaining_work_reserve_factor':1.25,
          'parameter_status':'conservative provisional profile, pending native G5420 measurements','public_tables_unchanged':True}
        (out/'build.json').write_text(json.dumps(meta,indent=2)+'\n');print(name,meta['source_sha256'],meta['binary_sha256'])
if __name__=='__main__':main()
