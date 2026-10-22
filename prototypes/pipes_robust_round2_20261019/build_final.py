"""Freeze the public-only Open12 risk improvement with the gated fallback."""
import datetime
import json
import subprocess
from build_online_fallback import HERE,PREV,e

def main():
    p=HERE/'joint_replan/open12/zoom/geometry_open12_zoom_best_positions.txt'
    for name,parent in [('final',HERE/'budgeted-inclusive/solution.cpp'),('final-plan',PREV/'candidate-v3/solution.cpp')]:
        tables=e.decode(parent);cmd=tables[11][0];it=iter(map(int,p.read_text().split()))
        tables[11]=(cmd,[next(it) if c>0 else None for c in cmd]);assert next(it,None) is None
        for i in range(15):
            for j in range(i):
                for c,d,x,y in zip(tables[i][0],tables[j][0],tables[i][1],tables[j][1]):
                    if c!=d:break
                    assert x==y
        source=parent.read_text();a=source.index('static const char* encoded[]={')+len('static const char* encoded[]={');z=source.index('};',a)
        source=source[:a]+'\n'+e.encode(tables)+source[z:]
        dest=HERE/name;dest.mkdir(exist_ok=True);(dest/'solution.cpp').write_text(source)
        subprocess.run(['clang++','-std=c++20','-O2',str(dest/'solution.cpp'),'-o',str(dest/'solver')],capture_output=True,check=True)
        info={'frozen_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_sha256':e.sha(dest/'solution.cpp'),
              'binary_sha256':e.sha(dest/'solver'),'parent_source_sha256':e.sha(parent),'changed_table':12,
              'causal_BF_prefix_length':151,'public_risk_selection':'min full-prefix maximum ratio among exact plans in bounded zoom; no attack outcome used',
              'fallback':'budgeted inclusive online episode' if name=='final' else 'BF',
              'selection':'Open12 public-only zoom added to previously frozen runtime; preserve all Open15 ceilings'}
        (dest/'build.json').write_text(json.dumps(info,indent=2)+'\n');print(name,info['source_sha256'],flush=True)

if __name__=='__main__':main()
