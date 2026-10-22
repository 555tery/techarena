"""Exercise state transfer after very long replay, near the 200k input limit."""
import json
from build_online_fallback import HERE,ROOT,e

def main():
    out=HERE/'safety';out.mkdir(exist_ok=True);rows=[]
    for case,cut,total in [(15,4999,5200),(15,199950,200000),(8,388,1000),(11,5000,6000)]:
        public=e.commands(ROOT/f'data/pipes/open/{case}.in');cmd=public[:cut]
        active={};pid=0
        for c in cmd:
            if c>0:pid+=1;active[pid]=c
            else:del active[-c]
        first=next(i for i in sorted(active) if -i!=public[cut]);cmd.append(-first);del active[first]
        while len(cmd)<total:
            if len(cmd)%3==0 and active:
                i=min(active);cmd.append(-i);del active[i]
            else:
                length=[1,7,20,40][len(cmd)%4];pid+=1;active[pid]=length;cmd.append(length)
        p=out/f'safety-open{case}-p{cut}.in';p.write_text('1\n'+str(len(cmd))+'\n'+'\n'.join(map(str,cmd))+'\n')
        rows.append({'file':str(p.relative_to(ROOT)),'sha256':e.sha(p),'prefix_length':cut,'case':case,**e.harness.parse_test(p)})
    (out/'manifest.json').write_text(json.dumps({'purpose':'correctness/resource diagnostics, not neutral selection data','tests':rows},indent=2)+'\n')

if __name__=='__main__':main()
