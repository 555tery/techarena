"""I/O-only production validation against a frozen policy, with exact output parity."""
import datetime
import json
import subprocess
from pathlib import Path

from evaluate import HERE, ROOT, cases, h, sha, verify_freeze


def main():
    verify_freeze('final')
    result = json.loads((HERE/'analysis-final.json').read_text())
    name = result['recommended']
    original = HERE/'candidates'/name/'solver'
    source = HERE/'candidates-fast'/name/'solution.cpp'
    binary = source.with_name('solver')
    build = json.loads(source.with_name('build.json').read_text())
    freeze_path = HERE/'production-freeze.json'
    frozen = dict(policy=name, source_sha256=sha(source), binary_sha256=sha(binary),
                  original_source_sha256=sha(original.with_name('solution.cpp')),
                  original_binary_sha256=sha(original),
                  original_selection_freeze_sha256=sha(HERE/'selection-freeze.json'),
                  analysis_final_sha256=sha(HERE/'analysis-final.json'),
                  production_plan_sha256=sha(HERE/'production-plan.json'),
                  builder_sha256=sha(HERE/'build_fast_io.py'),
                  validator_sha256=sha(Path(__file__)))
    if freeze_path.exists():
        old = json.loads(freeze_path.read_text())
        assert all(old[k] == v for k, v in frozen.items())
    else:
        freeze_path.write_text(json.dumps(dict(frozen, created_at=datetime.datetime.now(datetime.timezone.utc).isoformat()), indent=2)+'\n')
    inputs = [(group, row) for group in ['calibration', 'final', 'open15', 'stress'] for row in cases(group)]
    assert len(inputs) == 210
    parity_path = HERE/'production-parity.json'
    if parity_path.exists():
        parity = json.loads(parity_path.read_text())
        assert parity['production_freeze_sha256'] == sha(freeze_path)
    else:
        rows = []
        for group, case in inputs:
            tokens = case['path'].read_bytes().split()
            data = b'\n'.join(tokens[2:2+int(tokens[1])]+[b'0'])+b'\n'
            a = subprocess.run([str(original)], input=data, capture_output=True, timeout=90, check=True)
            b = subprocess.run([str(binary)], input=data, capture_output=True, timeout=90, check=True)
            assert a.stdout == b.stdout, (group, case['id'], 'I/O change affected output')
            import hashlib
            rows.append(dict(group=group, id=case['id'], test_sha256=sha(case['path']),
                             commands=int(tokens[1]), output_sha256=hashlib.sha256(a.stdout).hexdigest()))
        parity = dict(production_freeze_sha256=sha(freeze_path), records=rows,
                      n=len(rows), commands=sum(r['commands'] for r in rows),
                      exact_stdout_parity=True)
        parity_path.write_text(json.dumps(parity, indent=2)+'\n')
    print('EXACT_OUTPUT_PARITY', parity['n'], parity['commands'], flush=True)
    records = []
    for group, case in inputs:
        dest = HERE/'measurements/production'/group/name/case['id']
        dest.mkdir(parents=True, exist_ok=True)
        path = dest/'record.json'
        if path.exists():
            r = json.loads(path.read_text())
            assert r['binary_sha256'] == sha(binary) and r['test_sha256'] == sha(case['path'])
        else:
            r = h.run_case([str(binary)], ROOT/'tools/interactor', case['path'], dest, 5, 240)
            r.update(id=case['id'], group=group, strategy=name, family=case['family'],
                     stratum=case['stratum'], source_sha256=sha(source), binary_sha256=sha(binary),
                     mode='production_official')
            r['resources_ok'] = (r['solver_cpu_total_s'] is not None and r['solver_peak_rss_mb'] is not None
                                 and r['solver_cpu_total_s'] < 5 and r['solver_peak_rss_mb'] < 256)
            path.write_text(json.dumps(r, indent=2)+'\n')
        old = json.loads((HERE/'measurements/official'/group/name/case['id']/'record.json').read_text())
        assert r['status'] == 'ok' and r['trench_length_m'] == old['trench_length_m'], (group, case['id'], r)
        records.append(r)
        print(group, case['id'], name, r['status'], r['kpi'], r['solver_cpu_total_s'], r['solver_peak_rss_mb'], flush=True)
    assert sha(source) == frozen['source_sha256'] and sha(binary) == frozen['binary_sha256']
    output = dict(policy=name, production_freeze_sha256=sha(freeze_path), records=records,
                  all_valid=all(r['status']=='ok' for r in records),
                  all_resources_ok=all(r['resources_ok'] for r in records),
                  maximum_cpu_s=max(r['solver_cpu_total_s'] for r in records),
                  maximum_rss_mib=max(r['solver_peak_rss_mb'] for r in records),
                  n=len(records), native_windows_tested=False, platform_actions=0)
    (HERE/'production-validation.json').write_text(json.dumps(output, indent=2)+'\n')
    print(json.dumps({k:v for k,v in output.items() if k!='records'}, indent=2))
    assert output['all_resources_ok'], 'Production failed local resource gate; do not package as ready.'


if __name__ == '__main__':
    main()
