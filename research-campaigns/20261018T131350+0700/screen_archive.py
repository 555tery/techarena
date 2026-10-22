"""Bounded reuse of existing hypotheses, assessed on official local Open15."""
import importlib.util
import json
from pathlib import Path
import shutil
import hashlib

CAMPAIGN = Path(__file__).resolve().parent
REPO = CAMPAIGN.parents[1]
RUN = REPO / 'shinka-pipes/search-v3-1/runs/20261018T062832+0700-mixed'
spec = importlib.util.spec_from_file_location('campaign_evaluate', CAMPAIGN / 'evaluate.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def main():
    selected = [2, 3, 4, 5, 6, 7, 24, 52]
    directory = CAMPAIGN / 'branches/archive_transfer'
    directory.mkdir(exist_ok=True)
    sources = []
    for generation in selected:
        origin = RUN / f'gen_{generation}/main.cpp'
        target = directory / f'gen_{generation}.cpp'
        if target.exists():
            raise ValueError('refusing to replace a frozen screening source')
        shutil.copyfile(origin, target)
        sources.append({'generation':generation, 'origin':str(origin), 'source':str(target),
            'sha256':hashlib.sha256(target.read_bytes()).hexdigest()})
    (directory/'design.json').write_text(json.dumps({'selected':sources,'purpose':'reuse existing independent and specialist hypotheses; no new code proposals',
        'score_is_development_only':True,'validation_accessed':False},indent=2)+'\n')
    results = []
    for source in sources:
        module.quota()
        generation = source['generation']
        result = module.evaluate(source['source'], REPO/'data/pipes/open',
            directory/f'open15_gen_{generation}',f'archive-gen-{generation}')
        rows=[]
        if result.get('correct'):
            summary=json.loads(Path(result['summary_path']).read_text())
            rows=[{'case':r['case'],'trench':r['trench_length_m'],'score':r['weighted_score']} for r in summary['records']]
        results.append({'generation':generation,'correct':result.get('correct'),
            'score':result.get('weighted_score'),'cases':rows})
        (directory/'results.json').write_text(json.dumps(results,indent=2)+'\n')
        print(json.dumps({'generation':generation,'score':result.get('weighted_score'),
            'target_cases':[r for r in rows if r['case'] in ['11','13','15']]}),flush=True)


if __name__ == '__main__':
    main()
