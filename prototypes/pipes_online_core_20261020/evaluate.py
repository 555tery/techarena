"""Paired whole-stream evaluator with separate DEV and fresh data namespaces."""
import argparse, hashlib, importlib.util, json, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OLD = ROOT/'prototypes/pipes_closed_ready_20261020'
spec = importlib.util.spec_from_file_location('previous_evaluator', OLD/'evaluate.py')
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)
h, screen, sha = prior.h, prior.screen, prior.sha

def cases(group):
    if group == 'open15':
        return prior.cases(group)
    if group == 'dev':
        return [dict(c, id=g+'-'+c['id']) for g in ['calibration','final'] for c in prior.cases(g)]
    folder = HERE/'evaluation'/group
    m = json.loads((folder/'manifest.json').read_text())
    return [dict(c, path=folder/c['file']) for c in m['cases']]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('group', choices=['dev','open15','calibration','final','stress'])
    ap.add_argument('--names', default='baseline,primal_moderate')
    ap.add_argument('--mode', choices=['screen','official'], default='screen')
    args = ap.parse_args()
    if args.group in ['calibration','final','stress']:
        p = json.loads((HERE/'experiment.json').read_text())
        assert sha(HERE/'evaluation'/args.group/'manifest.json') == p['fresh_data'][args.group]
    if args.group == 'final':
        frozen = json.loads((HERE/'selection-freeze.json').read_text())
        for name in args.names.split(','):
            assert sha(HERE/'candidates'/name/'solution.cpp') == frozen['sources'][name]
    records = []
    for c in cases(args.group):
        if 'sha256' in c:
            assert sha(c['path']) == c['sha256']
        for name in args.names.split(','):
            directory = HERE/'candidates'/name
            binary, source = directory/'solver', directory/'solution.cpp'
            dest = HERE/'measurements'/args.mode/args.group/name/c['id']
            dest.mkdir(parents=True, exist_ok=True)
            path = dest/'record.json'
            if path.exists():
                r = json.loads(path.read_text())
                assert r['binary_sha256'] == sha(binary) and r['test_sha256'] == sha(c['path'])
            else:
                started = time.time()
                try:
                    r = screen(binary, c['path']) if args.mode == 'screen' else h.run_case([str(binary)], ROOT/'tools/interactor', c['path'], dest, 5, 240)
                except Exception as exc:
                    r = dict(status='error', detail=repr(exc), kpi=None, solver_cpu_total_s=None, solver_peak_rss_mb=None)
                r.update(id=c['id'], strategy=name, family=c['family'], stratum=c['stratum'],
                    test_sha256=sha(c['path']), source_sha256=sha(source), binary_sha256=sha(binary),
                    input_path=str(c['path']), mode=args.mode, started_at_unix=started)
                r['resources_ok'] = r['solver_cpu_total_s'] is not None and r['solver_cpu_total_s'] < 5 and r['solver_peak_rss_mb'] is not None and r['solver_peak_rss_mb'] < 256
                path.write_text(json.dumps(r, indent=2)+'\n')
            records.append(r)
            if r['status'] != 'ok':
                print('FAIL', c['id'], name, r.get('detail'), flush=True)
            if args.mode == 'official':
                old = HERE/'measurements/screen'/args.group/name/c['id']/'record.json'
                if old.exists():
                    q = json.loads(old.read_text())
                    assert q['trench_length_m'] == r['trench_length_m'] and q['test_sha256'] == r['test_sha256']
    out = dict(records=records, workers=1, platform_actions=0, host='macOS arm64, not Windows/G5420')
    (HERE/f'{args.mode}-{args.group}-{args.names.replace(",","-")}.json').write_text(json.dumps(out, indent=2)+'\n')
    print(json.dumps(dict(group=args.group,n=len(records),invalid=sum(r['status']!='ok' for r in records),resource_failures=sum(not r['resources_ok'] for r in records))))

if __name__ == '__main__':
    main()
