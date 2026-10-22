"""An exact, small diagnostic of multi-action versus one-intervention labels."""
import json
from audit import ROOT, REPO, source_module, verify
from audit_labels import replay
from tiny_oracle import optimal

def main():
    commands=[7,7,6,-2,5,-1,-3,15]
    cells=source_module('cells',REPO/'prototypes/pipes_generalization_20261018/audit_baselines.py')
    bf_replies=cells.oracle(commands,'bf');bf=verify(commands,bf_replies)['T']
    # First placement is already committed at zero. Enumerate EVERY integer
    # legal alternative at each later BF-trajectory arrival, then ordinary BF.
    # T is monotone: a forced action beyond BF's height cannot improve final T.
    single=[]
    for root,c in enumerate(commands):
        if c<=0 or root==0:continue
        oldT=verify(commands[:root],bf_replies[:root])['T']
        for start in range(bf-c+1):
            a={'start':start,'digs':(max(0,start+c-oldT)+19)//20}
            try:t=replay(commands,root,a)
            except AssertionError:continue
            single.append({'root':root,**a,'T':t})
    exact=optimal(commands,fixed={0:0},lower=20,upper=bf)
    assert exact['complete'] and exact['optimum']==20
    starts={int(k):v for k,v in exact['starts'].items()}
    witness={};pid=0;T=0
    for i,c in enumerate(commands):
        if c>0:
            start=starts[pid];pid+=1;dig=(max(0,start+c-T)+19)//20;T+=20*dig
            witness[i]={'start':start,'digs':dig}
    assert replay(commands,0,witness[0],witness)==exact['optimum']
    out={'commands':commands,'committed_first_start':0,'BF_T':bf,
         'best_single_intervention_then_BF_T':min(x['T'] for x in single),
         'single_interventions_checked':len(single),'exact_joint_T':exact['optimum'],
         'exact_search_nodes':exact['nodes'],'witness':witness,
         'scope':'Full integer actions at later BF states; fixed first pipe. Offline teacher diagnostic, not a causal performance claim.'}
    (ROOT/'coordination-fixture.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
if __name__=='__main__':main()
