"""Post-freeze coverage audit: mismatch while repaired PID2 is still alive.

The original independent46 mostly diverge after PID2 has been removed. This
additional seed set is not used to switch or tune the frozen candidate.
"""
import hashlib,json,random
from pathlib import Path
HERE=Path(__file__).resolve().parent;OUT=HERE/'evaluation/early-diagnostics'
SEED=2026102004103
def main():
    OUT.mkdir(parents=True,exist_ok=False);rows=[]
    for k in range(24):
        rng=random.Random(SEED+k*1009);commands=[3,2];active={1:3,2:2};pid=2
        def add(L):
            nonlocal pid
            pid+=1;active[pid]=L;commands.append(L)
        def remove(p):commands.append(-p);del active[p]
        if k<8:
            remove(1)
            # The nine tail metres and a random partition of the229m first gap
            # are known geometric mechanisms, with newly seeded event order.
            lengths=[];left=229
            while left:
                L=rng.randint(1,min(40,left));lengths.append(L);left-=L
            lengths.append(9);rng.shuffle(lengths)
            for L in lengths:add(L)
            family='random-exact-capacity-partition'
        else:
            if k%3==0:remove(1)
            else:add(rng.choice([9,19,20,29,38,39,40]))
            family='retained-marker-regime-shift'
            target=800+(k%4)*500
            while len(commands)<target:
                choices=[p for p in active if p!=2]
                if choices and (len(active)>80 or rng.random()<.47):
                    mode=(len(commands)//100)%4
                    victim=(min(choices) if mode==0 else max(choices) if mode==1 else
                            min(choices,key=lambda p:(active[p],p)) if mode==2 else rng.choice(choices))
                    remove(victim)
                else:
                    phase=(len(commands)//150)%3
                    L=rng.randint(1,10) if phase==0 else rng.randint(29,40) if phase==1 else rng.randint(1,40)
                    add(L)
                if len(commands)>target*4//5 and 2 in active and k%2:remove(2)
        # Validate source format and PID lifetimes independently from builders.
        live={};next_pid=0
        for c in commands:
            if c>0:assert 1<=c<=40;next_pid+=1;live[next_pid]=c
            else:assert -c in live;del live[-c]
        assert live and len(commands)<=200000 and commands[:2]==[3,2] and commands[2]!=-2
        name=f'E{k+1:02d}';path=OUT/(name+'.in');path.write_text('1\n'+str(len(commands))+'\n'+'\n'.join(map(str,commands))+'\n')
        rows.append({'id':name,'input_file':path.name,'input_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                     'seed':SEED+k*1009,'family':family,'n':len(commands),'prefix_commands':2,
                     'selection':'post-freeze coverage audit, no use in model selection'})
    (OUT/'manifest.json').write_text(json.dumps({'streams':rows,'seed':SEED,'candidate_read':False,
      'scope':'24 newseed inputs of retained-marker mechanism, not independent-agent confirmation or hidden-distribution sample',
      'reason':'Independent48 set has only two deterministic controls for livePID2; add targeted pre-coupling coverage without tuning candidate'},indent=2)+'\n')
    print('Wrote24post-freeze early diagnostics')
if __name__=='__main__':main()
