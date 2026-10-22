from pathlib import Path
import json, subprocess, sys, time
ROOT = Path('/Users/555tery/techarena')
OUT = ROOT / 'results/pipes/improvement/shrinkage'
BUILDS = json.loads((OUT / 'builds.json').read_text())['builds']
JUDGE = ROOT / 'tools/interactor'
SETS = [('open', ROOT / 'data/pipes/open'), ('development', ROOT / 'data/pipes/synthetic/development')]
progress = OUT / 'progress.log'
for build in BUILDS:
    name = build['name']
    for set_name, tests in SETS:
        report = OUT / 'reports' / set_name / name
        cmd = [sys.executable, str(ROOT / 'tools/pipes_harness.py'), '--solver', build['binary'], '--name', name,
               '--interactor', str(JUDGE), '--tests', str(tests), '--out', str(report)]
        marker = f'{time.strftime("%Y-%m-%dT%H:%M:%S")} START {set_name} {name}\n'
        progress.open('a').write(marker)
        log_path = report.parent / f'{name}.log'
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open('w') as log:
            result = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, text=True)
        summary_path = report / 'summary.json'
        if summary_path.exists():
            summary = json.loads(summary_path.read_text())
            row = (f'{set_name} {name}: score={summary["weighted_score_sum"]:.12f}/'
                   f'{summary["weight_sum"]:.12f}, valid={summary["ok_count"]}/{summary["case_count"]}, '
                   f'harness_rc={result.returncode}')
        else:
            row = f'{set_name} {name}: MISSING_SUMMARY harness_rc={result.returncode}'
        print(row, flush=True)
        with progress.open('a') as f:
            f.write(row + '\n')
        if not summary_path.exists():
            print(log_path.read_text()[-5000:], file=sys.stderr)
print('MATRIX_DONE', flush=True)
