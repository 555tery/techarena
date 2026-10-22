"""Independent replay of every full-suffix witness; paired observable audits."""
import json
from pathlib import Path
from collections import defaultdict
from audit import ROOT, read_input

def replay(commands, root, forced, witness=None):
    cells=[];live={};pid=0
    for i,c in enumerate(commands):
        if c<0:
            s,l=live.pop(-c);assert cells[s:s+l]==[-c]*l;cells[s:s+l]=[0]*l;continue
        gaps=[];j=0
        while j<len(cells):
            if cells[j]:j+=1;continue
            end=j
            while end<len(cells) and not cells[end]:end+=1
            gaps.append((j,end-j));j=end
        if i==root:a=forced
        elif i>root and witness is not None:a=witness[i]
        else:
            fits=[g for g in gaps if g[1]>=c]
            if fits:s,l=min(fits,key=lambda g:(g[1],g[0]));dig=0
            else:
                tail=gaps[-1][1] if gaps and sum(gaps[-1])==len(cells) else 0
                s=len(cells)-tail;dig=(c-tail+19)//20
            a={'start':s,'digs':dig}
        s,d=a['start'],a['digs'];assert d==(max(0,s+c-len(cells))+19)//20
        cells.extend([0]*(20*d));pid+=1
        assert s>=0 and s+c<=len(cells) and not any(cells[s:s+c])
        cells[s:s+c]=[pid]*c;live[pid]=(s,c)
    return len(cells)

def main():
    groups=defaultdict(list);states=actions=joint=bf_reference=0;expanded=0
    for file in sorted((ROOT/'labels/train').glob('*.jsonl')):
        for line in file.read_text().splitlines():
            row=json.loads(line);commands=read_input(Path(row['input']));root=row['command_index'];states+=1
            keys=[(a['start'],a['digs']) for a in row['actions']]
            assert len(keys)==len(set(keys))<=8
            opt={k for k,a in zip(keys,row['actions']) if a['cost']==row['best_cost']}
            groups[(row['observable_key'],row['length'])].append((opt,keys,row))
            for a in row['actions']:
                actions+=1;w={x['command_index']:x for x in a['witness']}
                assert len(w)==len(a['witness'])
                assert set(w)=={i for i in range(root,len(commands)) if commands[i]>0}
                assert (w[root]['start'],w[root]['digs'])==(a['start'],a['digs'])
                assert replay(commands,root,a,w)==a['cost']
                assert replay(commands,root,a)==a['bf_suffix_cost']>=a['cost']
                joint+=a['cost']<a['bf_suffix_cost'];bf_reference+=a['used_reference']
                expanded+=a['counters']['expanded']
    compared=conflict=identical_features=0;examples=[]
    for key,rows in groups.items():
        if len(rows)<2:continue
        compared+=1
        ref=rows[0]
        assert all(r[1]==ref[1] for r in rows)
        assert all([a['features'] for a in r[2]['actions']]==[a['features'] for a in ref[2]['actions']] for r in rows)
        identical_features+=1
        intersection=set.intersection(*(r[0] for r in rows))
        if not intersection:
            conflict+=1
            examples.append({'command_index':ref[2]['command_index'],'length':ref[2]['length'],
                             'forks':[{'input':r[2]['input'],'costs':[a['cost'] for a in r[2]['actions']]} for r in rows], 'actions':ref[1]})
    out={'states':states,'actions':actions,'all_witnesses_legal_and_costs_verified':True,
         'joint_actions_better_than_same_root_bf_suffix':joint,'used_bf_reference':bf_reference,
         'expanded':expanded,'paired_observable_groups':compared,'identical_causal_features':identical_features,
         'no_common_beam_best_action_groups':conflict,'examples':examples[:5],
         'scope':'Beam best-action conflicts are descriptive, not impossibility proof; all future-dependent costs stay offline.'}
    (ROOT/'teacher-independent-audit.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k!='examples'}))
if __name__=='__main__':main()
