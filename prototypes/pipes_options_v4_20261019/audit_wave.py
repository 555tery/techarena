"""Root's independent physical/macro simulator, separate from C++ allocator."""
from collections import Counter
import json
from pathlib import Path
import subprocess
from audit import ROOT, REPO, read_input, source_module

def replay(commands,path,root=None,forced=None,reference=False):
    steps={p['command_index']:p for p in path};assert len(steps)==len(path)
    assert set(steps)=={i for i,c in enumerate(commands) if c>0}
    cells=[];live={};pid=0;remaining=0;option=-1;replies=[];keys={};new_blocks=[]
    for i,c in enumerate(commands):
        keys[i]=str(len(cells))+'|'+''.join(f'{p}:{s}:{l}:{born};' for p,(s,l,born) in sorted(live.items()))
        if c<0:
            start,length,born=live.pop(-c);assert cells[start:start+length]==[-c]*length
            cells[start:start+length]=[0]*length;replies.append(str(start))
            if len(live)>12 or len(cells)>160:remaining=0;option=-1
            continue
        p=steps[i];eligible=len(live)<=12 and len(cells)<=160
        if not eligible:
            remaining=0;option=-1;active=0;offset=0
            assert p['option']==-1 and not p['boundary'] and not p['continuation']
        else:
            if remaining==0:
                assert p['boundary'] and not p['continuation']
                option=p['option'];assert option in range(4);remaining=4;new_blocks.append((i,option))
                if root is not None and i==root:assert option==forced
                if reference and root is not None and i>root:assert option==0
            else:assert not p['boundary'] and p['continuation'] and p['option']==option
            active=option;offset=4-remaining
        gaps=[];j=0
        while j<len(cells):
            if cells[j]:j+=1;continue
            end=j
            while end<len(cells) and cells[end]==0:end+=1
            gaps.append((j,end-j));j=end
        fits=[g for g in gaps if g[1]>=c]
        right=active==1 or (active==3 and offset>0)
        if fits:
            s,h=min(fits,key=lambda x:x[0] if active==2 else (x[1],x[0]));dig=0
            start=s+h-c if right else s
        else:
            tail=gaps[-1][1] if gaps and sum(gaps[-1])==len(cells) else 0
            dig=(c-tail+19)//20;start=len(cells)+20*dig-c if right else len(cells)-tail
        assert (p['digs'],p['start'])==(dig,start),(i,p,(dig,start),active,offset)
        cells.extend([0]*(20*dig));pid+=1
        assert start>=0 and start+c<=len(cells) and not any(cells[start:start+c])
        cells[start:start+c]=[pid]*c;live[pid]=(start,c,i+1)
        replies.append(f'{dig} {start}')
        if eligible:remaining-=1
    return {'T':len(cells),'F':sum(x[1] for x in live.values()),'replies':replies,'keys':keys,'blocks':new_blocks}

def audit_wave(directory,solver):
    directory=Path(directory);counts=Counter();stats_files=sorted(directory.glob('*.stats.json'))
    baseline=source_module('prior_bitmap',REPO/'prototypes/pipes_generalization_20261018/audit_baselines.py')
    for p in stats_files:
        st=json.loads(p.read_text());commands=read_input(Path(st['input']))
        actual=replay(commands,st['rollin_witness']);assert actual['T']==st['rollin_final_trench']
        run=subprocess.run([str(solver)],input='\n'.join(map(str,commands+[0]))+'\n',text=True,capture_output=True,timeout=5)
        assert run.returncode==0 and run.stdout.splitlines()==actual['replies']
        bf=baseline.oracle(commands,'bf');counts['rollin_streams']+=1
        counts['rollin_streams_changed_vs_BF']+=bf!=actual['replies']
        counts['rollin_commands_changed_vs_BF']+=sum(a!=b for a,b in zip(bf,actual['replies']))
        for k,v in st['rollin_counters'].items():counts['rollin_'+k]+=v
        labels=p.with_name(p.name.replace('.stats.json','.jsonl'))
        for line in labels.read_text().splitlines():
            row=json.loads(line);i=row['command_index'];counts['states']+=1
            assert row['state_key']==actual['keys'][i]
            assert row['prefix_witness']==[x for x in st['rollin_witness'] if x['command_index']<i]
            assert row['rollin_option']==next(x['option'] for x in st['rollin_witness'] if x['command_index']==i)
            for o in row['options']:
                counts['root_options']+=1
                best=replay(commands,row['prefix_witness']+o['witness'],i,o['index'])
                ref=replay(commands,row['prefix_witness']+o['reference_witness'],i,o['index'],True)
                assert best['T']==o['cost']<=ref['T']==o['reference_cost']
                counts['joint_improvements']+=best['T']<ref['T']
                counts['future_option_expansions']+=o['search_counters']['generated']
            assert row['gains']==[(row['options'][0]['cost']-o['cost'])/20 for o in row['options']]
    out={'passed':True,'counts':dict(counts),'scope':'Every ownrollin, every chosen/reference suffix, macro persistence and C++ runtime rollin parity verified by independent bitmap.'}
    (directory/'audit.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out),flush=True);return out

if __name__=='__main__':
    import sys
    audit_wave(sys.argv[1],Path(sys.argv[2]))
