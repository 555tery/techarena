import importlib.util,json,time
from pathlib import Path
here=Path(__file__).resolve().parent
root=here.parents[2]
spec=importlib.util.spec_from_file_location('ev',root/'prototypes/pipes_closed_ready_20261020/evaluate.py')
ev=importlib.util.module_from_spec(spec);spec.loader.exec_module(ev)
names=['baseline','parity_decay64','primal_window256']
binaries={n:(root/'prototypes/pipes_closed_ready_20261020/candidates-fast/online/solver' if n=='baseline' else here/n/'solver') for n in names}
records=[]
start=time.time()
for group in ['calibration','final','open15']:
    for i,case in enumerate(ev.cases(group)):
        for name in names:
            dest=here/'measurements'/group/name/(case['id']+'.json');dest.parent.mkdir(exist_ok=True,parents=True)
            if dest.exists():
                row=json.loads(dest.read_text())
            else:
                try:
                    row=ev.screen(binaries[name],case['path']);row.pop('candidate_stderr',None)
                except Exception as e:
                    row={'status':'error','detail':repr(e)}
                row.update(id=case['id'],family=case['family'],stratum=case['stratum'],group=group,name=name,test_sha256=ev.sha(case['path']),binary_sha256=ev.sha(binaries[name]))
                dest.write_text(json.dumps(row,indent=2)+'\n')
            records.append(row)
        if i%16==0: print(group,i,'elapsed',round(time.time()-start),flush=True)
    (here/'records.json').write_text(json.dumps(records,indent=2)+'\n')
print('DONE',len(records),round(time.time()-start),flush=True)
