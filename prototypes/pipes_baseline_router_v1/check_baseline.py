#!/usr/bin/env python3
"""Exact original/instrumented baseline equivalence on synthetic inputs only."""
import csv
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parent


def main():
    manifest=json.loads((ROOT/'data/manifest.json').read_text())
    records=[]
    for split in ['train','calibration']:
        for entry in manifest['artifacts'][split]['files']:
            path=ROOT/'data'/split/entry['file']
            assert hashlib.sha256(path.read_bytes()).hexdigest()==entry['sha256']
            tokens=path.read_text().split();commands=tokens[2:2+int(tokens[1])]
            raw='\n'.join([*commands,'0'])+'\n';runs=[]
            for name in ['old_baseline','instrumented']:
                result=subprocess.run([str(ROOT/'bin'/name)],input=raw,capture_output=True,text=True,check=True)
                assert len(result.stdout.splitlines())==len(commands)
                runs.append(result)
            assert runs[0].stdout==runs[1].stdout,(split,entry['file'])
            records.append({'split':split,'file':entry['file'],'input_sha256':entry['sha256'],
                'transcript_sha256':hashlib.sha256(runs[0].stdout.encode()).hexdigest(),
                'commands':len(commands),'diagnostic':runs[1].stderr.strip()})
    report={'exact_equivalence':True,'inputs':len(records),'commands':sum(x['commands'] for x in records),
        'binary_sha256':{n:hashlib.sha256((ROOT/'bin'/n).read_bytes()).hexdigest() for n in ['old_baseline','instrumented']},
        'records':records}
    (ROOT/'reports/baseline_equivalence.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Exact baseline equivalence:',len(records),'inputs,',report['commands'],'commands')


if __name__=='__main__':main()
