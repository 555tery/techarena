"""Reconstruct physical gaps independently of speculative online reservations."""
import datetime
import json
import subprocess
from common import HERE,e

NEW=r'''void adoptOnline(Allocator& actual,const fallback_online::Allocator& from){
 actual.T=int(from.trenchLength);actual.g.clear();actual.sizes.clear();
 actual.pipes.clear();actual.pipes.push_back({0,0});
 vector<pair<int,int>> live;live.reserve(from.activePipeCount);
 for(size_t id=1;id<from.pipes.size();++id){
  auto p=from.pipes[id];actual.pipes.push_back({int(p.start),p.active?p.length:0});
  if(p.active)live.push_back({int(p.start),int(p.start)+p.length});
 }
 sort(live.begin(),live.end());int cursor=0;
 for(auto [left,right]:live){
  if(left<cursor||right>actual.T)throw runtime_error("invalid occupied snapshot");
  actual.add(cursor,left);cursor=right;
 }
 actual.add(cursor,actual.T);
}
'''

def main():
    parent=HERE/'candidate/solution.cpp';source=parent.read_text()
    start=source.index('void adoptOnline(Allocator& actual,');end=source.index('\nint main(){',start)
    source=source[:start]+NEW+source[end:]
    dest=HERE/'candidate-physical';dest.mkdir(exist_ok=True);(dest/'solution.cpp').write_text(source)
    r=subprocess.run(['clang++','-std=c++20','-O2',str(dest/'solution.cpp'),'-o',str(dest/'solver')],capture_output=True,text=True)
    (dest/'compile.log').write_text(r.stdout+r.stderr);r.check_returncode()
    info=json.loads((HERE/'candidate/build.json').read_text())
    info.update(parent_source_sha256=e.sha(parent),source_sha256=e.sha(dest/'solution.cpp'),binary_sha256=e.sha(dest/'solver'),
                frozen_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                snapshot_fix='gaps are the complement of actual active pipes, including unoccupied speculative reservations',
                selection='independent source invariant audit, before examining round3 final fresh/holdout scores')
    (dest/'build.json').write_text(json.dumps(info,indent=2)+'\n');print(info['source_sha256'])

if __name__=='__main__':main()
