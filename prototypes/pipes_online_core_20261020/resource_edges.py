"""Post-freeze resource checks; never used for selection or tuning."""
import argparse, collections, datetime, json, random
from evaluate import HERE, ROOT, h, screen, sha

def generate():
    dest=HERE/'resource_edges';dest.mkdir(exist_ok=True)
    rows=[]
    for label,pop,seed,batch in [('moderate_churn',512,87002011,1),('scale_boundary',4099,87002012,3)]:
        rng=random.Random(seed);commands=[];active=collections.deque();pid=0
        def place(i):
            nonlocal pid
            # Abrupt changes of request support, fixed before resource results.
            phase=(i//97)%4
            choices=([1,2,3,4,5],[24,27,31,35,40],[6,11,16,21,26],[7,13,19,29,37])[phase]
            commands.append(rng.choice(choices));pid+=1;active.append(pid)
        for i in range(pop):place(i)
        epoch=0
        while len(commands)+2*batch<=200000:
            for _ in range(batch):
                if epoch%3==0:
                    active.rotate(rng.randrange(len(active)))
                commands.append(-active.popleft())
            for _ in range(batch):place(len(commands))
            epoch+=1
        while len(commands)<200000:place(len(commands))
        path=dest/(label+'.in')
        assert not path.exists()
        path.write_text('1\n'+str(len(commands))+'\n'+'\n'.join(map(str,commands))+'\n0\n')
        meta=h.parse_test(path)
        rows.append(dict(id=label,file=path.name,sha256=sha(path),n=len(commands),population=pop,seed=seed,metadata=meta))
    (dest/'manifest.json').write_text(json.dumps(dict(created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        purpose='Resource and correctness only, generated after final score results and candidate freeze; not independent quality evidence.',
        selection_freeze_sha256=sha(HERE/'selection-freeze.json'),cases=rows),indent=2)+'\n')

def run():
    manifest=json.loads((HERE/'resource_edges/manifest.json').read_text())
    frozen=json.loads((HERE/'selection-freeze.json').read_text())
    records=[]
    for c in manifest['cases']:
        path=HERE/'resource_edges'/c['file'];assert sha(path)==c['sha256']
        for name in ['baseline',frozen['selected']]:
            directory=HERE/'candidates'/name;assert sha(directory/'solution.cpp')==frozen['sources'][name]
            assert sha(directory/'solver')==frozen['binaries'][name]
            bulk=screen(directory/'solver',path)
            dest=HERE/'measurements/official/resource_edges'/name/c['id'];dest.mkdir(parents=True,exist_ok=True)
            r=h.run_case([str(directory/'solver')],ROOT/'tools/interactor',path,dest,5,240)
            assert r['status']=='ok' and r['trench_length_m']==bulk['trench_length_m']
            r.update(id=c['id'],strategy=name,test_sha256=c['sha256'],source_sha256=frozen['sources'][name],mode='official',stratum='resource',family=c['id'],
                     resources_ok=r['solver_cpu_total_s']<5 and r['solver_peak_rss_mb']<256)
            (dest/'record.json').write_text(json.dumps(r,indent=2)+'\n')
            records.append(r)
            print(c['id'],name,r['solver_cpu_total_s'],r['solver_peak_rss_mb'],r['resources_ok'],flush=True)
    (HERE/'resource-edges-results.json').write_text(json.dumps(dict(records=records,selection_use=False),indent=2)+'\n')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('action',choices=['generate','run']);args=ap.parse_args()
    generate() if args.action=='generate' else run()
