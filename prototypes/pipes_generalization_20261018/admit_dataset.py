"""Coordinator's independent input admission. No solver scores are loaded."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1] / 'tools'))
from pipes_harness import parse_test


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    source = ROOT / 'data/generated'
    assert (source / 'STATUS').read_text().strip() == 'COMPLETE'
    manifest = json.loads((source / 'manifest.json').read_text())
    assert manifest['freeze_sha256'] == sha(ROOT / 'freeze.json')
    assert len(manifest['bases']) == 48 and len(manifest['cases']) == 240
    families = manifest['design']['families']
    bases = {b['base_id']:b for b in manifest['bases']}
    assert len(bases) == 48
    assert len(set(b['seed'] for b in bases.values())) == 48
    final, repeat = ROOT/'data/final', ROOT/'data/repeat'
    final.mkdir(exist_ok=False); repeat.mkdir(exist_ok=False)
    index, volume, audits = {}, [], []
    for base in bases.values():
        path = source / base['path']
        assert sha(path) == base['sha256']
        base_commands = list(map(int, path.read_text().split()[2:]))
        assert len(base_commands) == base['n']
        cases = [c for c in manifest['cases'] if c['base_id'] == base['base_id']]
        assert sorted(c['stop_fraction'] for c in cases) == [.2,.4,.6,.8,1.0]
        for case in cases:
            path = source / case['file']
            assert sha(path) == case['sha256']
            data = path.read_text().split()
            assert float(data[0]) == 1 and int(data[1]) == case['cutpoint']
            commands = list(map(int,data[2:]))
            assert commands == base_commands[:case['cutpoint']]
            checked = parse_test(path)
            assert checked['operation_count'] == case['cutpoint']
            assert checked['final_occupied_length_m'] == case['stats']['live_volume']
            assert checked['peak_live_pipe_length_m'] == case['stats']['max_live_volume']
            assert checked['placement_count'] == case['stats']['arrivals']
            scale = base['parameters']['scale']
            if scale == 'micro':
                assert checked['peak_live_pipe_length_m'] <= 60
            name = case['test_id']
            index[name] = {'family':case['family'],'base_id':case['base_id'],
                           'replicate':case['replicate'],'stop_fraction':case['stop_fraction'],
                           'stop_role':case['stop_role'],'scale':scale,'full_length':base['n'],
                           'n':checked['operation_count'],'F':checked['final_occupied_length_m'],
                           'peak':checked['peak_live_pipe_length_m'],
                           'H0':checked['minimum_trench_lower_bound_m'],'sha256':case['sha256']}
            target = final / (name+'.in')
            shutil.copyfile(path,target)
            # Exact predeclared repeat identities: endpoints of each scale's
            # family list, replicate3, full trajectory. No metric is available.
            if case['replicate'] == 3 and case['stop_fraction'] == 1:
                if case['family'] in [families[i]['id'] for i in (0,9,10,11)]:
                    shutil.copyfile(target, repeat/target.name)
            volume.append(checked['final_occupied_length_m']/checked['peak_live_pipe_length_m'])
        audits.append({'base_id':base['base_id'],'prefixes':5,'independent_parser_passed':True})
    assert len(index) == 240
    assert set(Counter(r['family'] for r in index.values()).values()) == {20}
    assert len(list(repeat.glob('*.in'))) == 4
    (ROOT/'data/case-index.json').write_text(json.dumps(index,indent=2)+'\n')
    report = {'independent_parser_passed':True,'cases':240,'bases':48,'families':12,
              'literal_prefix_groups_verified':audits,'manifest_sha256':sha(source/'manifest.json'),
              'repeat_cases':[p.stem for p in sorted(repeat.glob('*.in'))],
              'minimum_final_over_peak':min(volume),'maximum_final_over_peak':max(volume),
              'zero_final_volume_count':sum(r['F']==0 for r in index.values()),
              'input_bytes_unchanged':all(sha(final/(name+'.in'))==r['sha256'] for name,r in index.items())}
    (ROOT/'data/admission.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k != 'literal_prefix_groups_verified'}))


if __name__ == '__main__':
    main()
