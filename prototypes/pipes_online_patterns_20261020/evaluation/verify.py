#!/usr/bin/env python3
"""Independent disk replay and controls audit; does not import generator."""
import collections
import hashlib
import json
import re
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]

def sha(raw):return hashlib.sha256(raw).hexdigest()

def main():
    seen=set();command_hashes=set();summary={}
    for split,count,per_stratum in [('calibration',96,24),('final',192,48),('stress',4,4)]:
        path=HERE/split/'manifest.json';rows=json.loads(path.read_text())['cases']
        assert len(rows)==count
        commands_by_id={}
        for row in rows:
            raw=(HERE/split/row['file']).read_bytes();tokens=raw.split()
            assert tokens[0]==b'1' and tokens[-1]==b'0'
            commands=list(map(int,tokens[2:-1]))
            assert 1<=len(commands)==int(tokens[1])==row['n']<=200000
            h=sha(raw);assert h==row['sha256'] and h not in seen;seen.add(h)
            h=sha(('\n'.join(map(str,commands))+'\n').encode())
            assert h==row['commands_sha256'] and h not in command_hashes;command_hashes.add(h)
            live={};pid=1;volume=peak=peak_count=0
            for c in commands:
                if c>0:
                    assert 1<=c<=40
                    live[pid]=c;pid+=1;volume+=c
                else:
                    assert c<0 and -c in live
                    volume-=live.pop(-c)
                peak=max(peak,volume);peak_count=max(peak_count,len(live))
            assert volume==row['final_live_volume']>0
            assert peak==row['peak_live_volume']
            assert len(live)==row['final_live_count']>=1
            assert peak_count==row['peak_live_count']
            assert volume/peak==row['final_to_peak_volume']
            prefix=row['public_prefix']
            if prefix:
                source=(ROOT/prefix['source']).read_bytes()
                assert sha(source)==prefix['source_sha256']
                public=list(map(int,source.split()[2:-1]));n=prefix['prefix_n']
                assert commands[:n]==public[:n]
                assert sha(('\n'.join(map(str,commands[:n]))+'\n').encode())==prefix['prefix_commands_sha256']
                assert n+prefix['suffix_n']==len(commands)
            if row['matched_control_for']:
                original=commands_by_id[row['matched_control_for']]
                assert len(original)==len(commands)
                assert [c>0 for c in original]==[c>0 for c in commands]
                assert collections.Counter(c for c in original if c>0)==collections.Counter(c for c in commands if c>0)
                assert original!=commands
            commands_by_id[row['id']]=commands
        strata=dict(collections.Counter(r['stratum'] for r in rows))
        expected=({'stress':4} if split=='stress' else {s:per_stratum for s in ['stable_patterns','changing_patterns','neutral','public_prefix']})
        assert strata==expected
        prefixes=[r['public_prefix'] for r in rows if r['public_prefix']]
        if split!='stress':
            assert {p['case'] for p in prefixes}==set(range(1,16))
            assert {p['suffix'] for p in prefixes}=={'stable_motif','changing_grammar','neutral_renewal','noisy_inverse_motif','cohort_return','affine_periodic','terminal_fill','stop_after_prefix'}
            assert sum(bool(r['matched_control_for']) for r in rows)==per_stratum//2
        summary[split]={'cases':count,'strata':strata,'n_min':min(r['n'] for r in rows),
            'n_max':max(r['n'] for r in rows),'manifest_sha256':sha(path.read_bytes()),
            'F_peak_ge_0_9':sum(r['final_to_peak_volume']>=.9 for r in rows),
            'F_peak_lt_0_7':sum(r['final_to_peak_volume']<.7 for r in rows),
            'matched_controls':sum(bool(r['matched_control_for']) for r in rows),
            'prefix_cases':sorted({p['case'] for p in prefixes})}
    generation=json.loads((HERE/'generation-summary.json').read_text())
    known=set()
    for entry in generation['known_manifests_checked']:
        raw=(ROOT/entry['path']).read_bytes()
        known.update(x.decode().lower() for x in re.findall(rb'(?<![0-9a-fA-F])[0-9a-fA-F]{64}(?![0-9a-fA-F])',raw))
    known.update(sha((ROOT/'data/pipes/open'/f'{i}.in').read_bytes()) for i in range(1,16))
    assert not known&seen
    for split,entry in generation['manifests'].items():assert entry['sha256']==summary[split]['manifest_sha256']
    result={'all_checks_passed':True,'unique_file_hashes':len(seen),'unique_command_hashes':len(command_hashes),
            'known_hash_overlap':[],'known_sha256_tokens':len(known),'summary':summary}
    (HERE/'disk-validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
