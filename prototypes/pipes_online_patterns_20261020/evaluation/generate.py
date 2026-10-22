#!/usr/bin/env python3
"""Predeclared patterned and neutral workloads; never imports a solver."""
import hashlib
import json
import math
import random
import re
from pathlib import Path
from stream import Stream

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
FAMILIES=['motif_fifo','motif_lifo','markov_profiles','block_size_grammar','age_conditional',
          'size_conditional_lifetime','cohort_batches','periodic_events','noisy_motif',
          'affine_motif','nested_runs','alternating_lifetime_classes']
STRATA=['stable_patterns','changing_patterns','neutral','public_prefix']

def sha(raw):return hashlib.sha256(raw).hexdigest()

def parameters(r,final,index):
    m=r.randint(7,11) if final else r.randint(3,6)
    return {'motif':[r.randint(1,40) for _ in range(m)],
        'period':r.randint(151,313) if final else r.randint(67,137),
        'affine_a':r.choice([9,11,13,17]) if final else r.choice([1,3,7]),
        'affine_b':r.randint(21,39) if final else r.randint(0,17),
        'short_life':r.randint(41,97) if final else r.randint(9,35),
        'long_life':r.randint(900,2100) if final else r.randint(280,750),
        'noise':([.015,.04,.075,.11][index//12%4] if final else [.01,.055][index//12%2]),
        'transition_p':r.uniform(.013,.031) if final else r.uniform(.045,.085),
        'markov_state':0,'index':index,'final':final}

def sample_size_delete(s,longest):
    if len(s.live)<=1:return None
    sample=[s.ids[s.rng.randrange(len(s.ids))] for _ in range(24)]
    return (max if longest else min)(sample,key=lambda p:s.live[p])

def patterned_event(s,family,t,params,invert=False,noise_override=False):
    r=s.rng; p=params['period']; motif=params['motif']; pos=s.next_pid-1
    m=motif[::-1] if invert else motif
    length=m[pos%len(m)]
    policy='random'; prob=.42; life=1000000; pid=None
    if family=='motif_fifo':policy='oldest'
    elif family=='motif_lifo':policy='newest'
    elif family=='markov_profiles':
        if r.random()<params['transition_p']:
            step=1 if not params['final'] or r.random()<.72 else 2
            params['markov_state']=(params['markov_state']+step)%3
        state=params['markov_state']
        length=r.randint(*[(1,9),(13,23),(28,40)][state])
        policy=['old','young','random'][state];prob=[.27,.52,.40][state]
    elif family=='block_size_grammar':
        block=(t//p)%len(m)
        # Persistent size grammar, with subblocks sharing a small vocabulary.
        length=m[(block+(t//max(3,p//7))%2)%len(m)]
        prob=.16 if t%p<p*.55 else .67
        policy='oldest' if block%2 else 'young'
    elif family=='age_conditional':
        policy='young' if t%p<p*.62 else 'old'
        prob=.45
        length=m[pos%len(m)] if t%p<p*.7 else 1+(m[pos%len(m)]+11)%40
    elif family=='size_conditional_lifetime':
        life=params['short_life'] if length>20 else params['long_life']
        if invert:life=params['long_life'] if length>20 else params['short_life']
        pid=s.due();prob=0
    elif family=='cohort_batches':
        if t%p==int(p*.66):s.batch_remaining=min(max(0,len(s.live)-1),p//3)
        if s.batch_remaining:
            pid=s.choose('oldest' if not invert else 'newest');s.batch_remaining-=1
        prob=.08 if pid is None else 0
        length=m[(t//p)%len(m)]
    elif family=='periodic_events':
        prob=.07 if t%p<p*.59 else .83
        policy='oldest' if (t//p)%3 else 'newest'
    elif family=='noisy_motif':
        prob=.43;policy='newest' if pos%len(m)<len(m)//2 else 'oldest'
    elif family=='affine_motif':
        length=1+(params['affine_a']*(length-1)+params['affine_b'])%40
        policy='oldest';prob=.39
    elif family=='nested_runs':
        lengths=[p//3,p//2,p-p//3-p//2]
        offset=t%p;which=0 if offset<lengths[0] else (1 if offset<sum(lengths[:2]) else 2)
        length=m[((t//p)+which)%len(m)]
        prob=[.13,.54,.72][which];policy=['random','oldest','newest'][which]
    elif family=='alternating_lifetime_classes':
        life=params['short_life'] if pos%len(m)<len(m)//2 else params['long_life']
        if invert:life=params['short_life']+params['long_life']-life
        pid=s.due();prob=0
    if invert and family not in ('size_conditional_lifetime','alternating_lifetime_classes'):
        length=41-length
        policy={'oldest':'newest','newest':'oldest','old':'young','young':'old'}.get(policy,policy)
    if noise_override or r.random()<params['noise']:
        length=r.randint(1,40)
        if noise_override:prob=.47;policy='random'
    if pid is None and r.random()<prob:pid=s.choose(policy)
    s.emit(-pid if pid is not None else length,life)

def pattern_schedule(s,kind,index,n,final,start=0):
    r=s.rng;params=parameters(r,final,index)
    a=FAMILIES[index%12];b=FAMILIES[(index%12+5+index//12)%12]
    fill=(index%8==3) if final else (index%7==2)
    for j in range(n):
        t=start+j;family=a;inverse=False;interrupt=False
        if kind=='stable_patterns' and final:
            # A recurring higher-order grammar, not a one-off distribution shift.
            if index//12==1:family=a if (j//params['period'])%3<2 else b
            elif index//12==2:family=a if (j//params['period'])%2==0 else b
            elif index//12==3:family=a if j%params['period']<params['period']*.72 else b
        if kind=='changing_patterns':
            frac=j/max(1,n)
            if not final:
                if index//12==0:inverse=frac>=.53
                else:interrupt=.46<=frac<.73
            else:
                if index//12==0:inverse=.32<=frac<.59 or frac>=.86
                elif index//12==1:
                    interrupt=.37<=frac<.58
                    family=b if frac>=.79 else a
                elif index//12==2:
                    family=b if .34<=frac<.68 else a
                    inverse=frac>=.87
                else:
                    inverse=.29<=frac<.48
                    interrupt=.62<=frac<.83
        if fill and j>=n*.82:s.emit(r.randint(18,40))
        else:patterned_event(s,family,t,params,inverse,interrupt)
    return {'primary_mechanism':a,'secondary_mechanism':b if final else None,
            'parameters':{k:v for k,v in params.items() if k!='markov_state'},'terminal_fill':fill,
            'schedule':f'{kind}/'+('final' if final else 'calibration')+f'/variant{index//12}'}

def neutral(s,index,n,final):
    r=s.rng;profile=index%6
    active_target=([19,75,220,650,1200,60] if final else [8,40,150,450,900,110])[profile]
    for t in range(n):
        if profile==0:length=r.randint(1,40)
        elif profile==1:length=r.randint(1,9) if r.random()<.76 else r.randint(15,40)
        elif profile==2:length=r.randint(24,40) if r.random()<.77 else r.randint(1,23)
        elif profile==3:length=r.choice([3,11,23,37] if not final else [2,7,18,29,40])
        elif profile==4:length=r.randint(1,40)
        else:length=max(1,min(40,round(r.gauss(21,7 if final else 11))))
        prob=.19 if len(s.live)<active_target else .57
        life=r.randint(40,650) if final else r.randint(10,290)
        if profile in (1,5):pid=s.due()
        else:pid=s.choose('random') if r.random()<prob else None
        if profile==4 and t>=n*.87:pid=None
        s.emit(-pid if pid is not None else length,life if profile in (1,5) else 1000000)
    return {'profile':profile,'target_active':active_target,'terminal_fill':profile==4,'kind':'IID/independent_lifetimes'}

def shuffled_control(source,seed):
    s=Stream(random.Random(seed))
    values=[c for c in source.commands if c>0]
    s.rng.shuffle(values);it=iter(values)
    for command in source.commands:
        if command>0:s.emit(next(it))
        else:
            assert len(s.live)>1
            s.emit(-s.ids[s.rng.randrange(len(s.ids))])
    return s

def public_prefix(seed,index,final):
    r=random.Random(seed);case=index%15+1
    long=final and index in (46,47)
    if long:case=14 if index==46 else 15
    source=ROOT/'data/pipes/open'/f'{case}.in';raw=source.read_bytes()
    tokens=raw.split();commands=list(map(int,tokens[2:-1]))
    if long:plen=17213 if case==14 else 17813
    elif len(commands)<=32:plen=max(1,len(commands)-1-index%3)
    else:plen=r.randint(41,min(3300,len(commands)-1))
    suffix=['stable_motif','changing_grammar','neutral_renewal','noisy_inverse_motif',
            'cohort_return','affine_periodic','terminal_fill','stop_after_prefix'][index%8]
    if suffix=='stop_after_prefix':
        if len(commands)<1102:suffix='stable_motif'
        else:plen=max(plen,min(len(commands)-1,1301+index*7))
    if long:suffix='cohort_return' if index==46 else 'changing_grammar'
    s=Stream(r)
    for command in commands[:plen]:s.emit(command)
    while not s.live:s.emit(commands[plen]);plen+=1
    suffix_n=0 if suffix=='stop_after_prefix' else (2400 if long else r.randint(1350,2400))
    if suffix=='terminal_fill':
        for _ in range(suffix_n):s.emit(r.randint(10,40))
    elif suffix=='neutral_renewal':neutral(s,index+1,suffix_n,final)
    elif suffix in ('stable_motif','changing_grammar','cohort_return'):
        idx=index if suffix!='cohort_return' else 6+12*(index//12)
        pattern_schedule(s,'stable_patterns' if suffix=='stable_motif' else 'changing_patterns',idx,suffix_n,final,plen)
    else:
        params=parameters(r,final,index)
        family='noisy_motif' if suffix=='noisy_inverse_motif' else 'affine_motif'
        for t in range(suffix_n):patterned_event(s,family,plen+t,params,t>suffix_n*.55, t%params['period']==0)
    info={'case':case,'source':str(source.relative_to(ROOT)),'source_sha256':sha(raw),
        'source_command_count':len(commands),'prefix_n':plen,'suffix_n':suffix_n,'suffix':suffix,
        'prefix_commands_sha256':sha(('\n'.join(map(str,commands[:plen]))+'\n').encode())}
    return s,info

def save(split,index,s,family,stratum,seed,details=None,prefix=None,control=None):
    assert len(s.commands)<=200000 and s.volume>0
    commands=('\n'.join(map(str,s.commands))+'\n').encode()
    raw=f'1 {len(s.commands)}\n'.encode()+commands+b'0\n'
    folder=HERE/split;folder.mkdir(exist_ok=True);file=f'case-{index:03d}.in'
    (folder/file).write_bytes(raw)
    return {'id':f'{split}-{index:03d}','file':file,'family':family,'stratum':stratum,'seed':seed,
        'n':len(s.commands),'sha256':sha(raw),'commands_sha256':sha(commands),
        'final_live_volume':s.volume,'peak_live_volume':s.peak,'final_live_count':len(s.live),
        'peak_live_count':s.peak_count,'final_to_peak_volume':s.volume/s.peak,
        'public_prefix':prefix,'mechanism_details':details,'matched_control_for':control}

def main():
    manifests={}
    for split,count,base in [('calibration',24,315020261020000),('final',48,415020261020000)]:
        final=split=='final';rows=[];stable=[]
        for stratum in STRATA:
            for i in range(count):
                seed=base+1000*STRATA.index(stratum)+i
                n=(3101 if final else 2303)+(i*(571 if final else 439))%(2901 if final else 3401)
                details=prefix=control=None
                if stratum in ('stable_patterns','changing_patterns'):
                    s=Stream(random.Random(seed))
                    details=pattern_schedule(s,stratum,i,n,final)
                    family=details['primary_mechanism']+'/'+details['schedule']
                    if stratum=='stable_patterns':stable.append((s,len(rows)))
                elif stratum=='neutral' and i<count//2:
                    source,source_row=stable[i]
                    s=shuffled_control(source,seed);control=rows[source_row]['id']
                    family='matched_marginal_shuffle/'+rows[source_row]['family']
                    details={'preserved':['positive_size_histogram','command_sign_schedule','insert_and_delete_counts'],
                             'randomized':['positive_size_order','legal_deletion_PID_assignment']}
                elif stratum=='neutral':
                    s=Stream(random.Random(seed));details=neutral(s,i,n,final)
                    family=f"neutral/profile{details['profile']}/variant{i//6}"
                else:
                    s,prefix=public_prefix(seed,i,final);family='public_prefix/'+prefix['suffix']
                rows.append(save(split,len(rows),s,family,stratum,seed,details,prefix,control))
        manifests[split]={'schema_version':1,'split':split,'weight':1,
            'selection_status':'predeclared_without_candidate_outcomes','cases':rows}
    rows=[]
    for i,family in enumerate(['stable_pattern_longrun','changing_pattern_longrun','neutral_heavy_churn','max_alive']):
        seed=515020261020000+i;s=Stream(random.Random(seed))
        if i in (0,1):details=pattern_schedule(s,'stable_patterns' if i==0 else 'changing_patterns',17+i*9,200000,True)
        elif i==2:details=neutral(s,0,200000,True)
        else:
            for _ in range(200000):s.emit(s.rng.randint(1,40))
            details={'terminal_fill':False,'kind':'maximum_alive_count'}
        rows.append(save('stress',i,s,family,'stress',seed,details))
    manifests['stress']={'schema_version':1,'split':'stress','weight':1,'cases':rows}
    allrows=[r for m in manifests.values() for r in m['cases']]
    hashes={r['sha256'] for r in allrows};assert len(hashes)==len(allrows)
    assert len({r['commands_sha256'] for r in allrows})==len(allrows)
    prior_dirs=['pipes_closed_ready_20261020','pipes_online_core_20261020']
    known_paths=[]
    for dirname in prior_dirs:
        d=ROOT/'prototypes'/dirname/'evaluation'
        known_paths.extend(str((d/s/'manifest.json').relative_to(ROOT)) for s in ('calibration','final','stress'))
        known_paths.extend(x['path'] for x in json.loads((d/'generation-summary.json').read_text())['known_manifests_checked'])
    known=set();checked=[]
    for rel in sorted(set(known_paths)):
        p=ROOT/rel
        if p.exists():
            tokens={x.decode().lower() for x in re.findall(rb'(?<![0-9a-fA-F])[0-9a-fA-F]{64}(?![0-9a-fA-F])',p.read_bytes())}
            known.update(tokens);checked.append({'path':rel,'sha256_tokens':len(tokens)})
    open_hashes={sha((ROOT/'data/pipes/open'/f'{i}.in').read_bytes()) for i in range(1,16)}
    known.update(open_hashes);assert not hashes&known
    for split,m in manifests.items():(HERE/split/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
    summary={'schema_version':1,'generator_sha256':sha(Path(__file__).read_bytes()),
        'bookkeeping_sha256':sha((HERE/'stream.py').read_bytes()),'design_sha256':sha((HERE/'design.json').read_bytes()),
        'counts':{k:len(m['cases']) for k,m in manifests.items()},'known_hash_overlap':[],
        'known_manifests_checked':checked,'known_sha256_tokens':len(known),'open15_source_hashes_checked':sorted(open_hashes),
        'all_input_and_commands_hashes_unique':True,'score_based_rejection':False,
        'volume_diagnostics':{k:{'count_ge_0_9':sum(r['final_to_peak_volume']>=.9 for r in m['cases']),
            'count_lt_0_7':sum(r['final_to_peak_volume']<.7 for r in m['cases']),
            'min':min(r['final_to_peak_volume'] for r in m['cases'])} for k,m in manifests.items()},
        'independence':['No candidate source or new results read; no solver or platform runs.',
            'Open15 structure computed only from official input commands, not placements or scores.',
            'No rejection or tuning using score, KPI, F/peak or observed candidate failures.',
            'Matched controls preserve stated marginals only; retained sign schedule is disclosed.',
            'Synthetic final cannot guarantee the unknown hidden-test distribution; public prefixes are known events.',
            'Final candidate outcomes must remain sealed until candidate freeze.'],
        'manifests':{k:{'path':f'{k}/manifest.json','sha256':sha((HERE/k/'manifest.json').read_bytes())} for k in manifests}}
    (HERE/'generation-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({k:summary[k] for k in ('counts','manifests','volume_diagnostics')},indent=2))

if __name__=='__main__':main()
