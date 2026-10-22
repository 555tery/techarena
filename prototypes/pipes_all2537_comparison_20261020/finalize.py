#!/usr/bin/env python3
"""Independent final arithmetic audit and attainable-KPI witness catalog."""
import hashlib
import json
import math
from fractions import Fraction
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    frozen=json.loads((HERE/'freeze.json').read_text())
    analysis=json.loads((HERE/'analysis.json').read_text())
    recheck=json.loads((HERE/'resource-recheck/summary.json').read_text())
    regimes=json.loads((HERE/'regime_analysis.json').read_text())
    assert analysis['complete'] and analysis['selected_complete'] and recheck['complete']
    assert regimes['complete'] and regimes['selected_pair_complete']
    assert regimes['records_snapshot_sha256']==analysis['hash_verification']['records_snapshot_sha256']
    assert analysis['hash_verification']['transcripts_read_and_rehashed']
    rows=[json.loads(x) for x in (HERE/'records.jsonl').read_text().splitlines()]
    index={(r['id'],r['method']):r for r in rows}
    methods=frozen['methods'];selected=[c for c in frozen['cases'] if c['selected']]
    assert len(rows)==len(index)==2541*6 and len(selected)==2537
    freeze_sha=sha(HERE/'freeze.json')
    assert all(r['freeze_sha256']==freeze_sha for r in rows)
    assert analysis['hash_verification']['records_snapshot_sha256']==sha(HERE/'records.jsonl')
    means={};public={};originals={}
    for method in methods:
        m=method['id'];valid=[];adjusted=[]
        for case in selected:
            r=index[case['id'],m]
            k=case['meta']['final_occupied_length_m']/r['trench_length_m'] if r['status']=='ok' else None
            if k is not None:valid.append(k)
            passed=(r['status']=='ok' and r['solver_cpu_total_s'] is not None and r['solver_cpu_total_s']<5
                    and r['solver_peak_rss_mb'] is not None and r['solver_peak_rss_mb']<256)
            assert passed==r['within_limits']
            adjusted.append(k if passed else 0.)
        means[m]={'raw_mean':math.fsum(valid)/len(valid) if valid else None,'adjusted_mean':math.fsum(adjusted)/2537}
        s=analysis['all_selected_summaries'][m]
        assert means[m]['raw_mean'] is None or abs(means[m]['raw_mean']-s['raw_kpi_valid_scored_runs_only']['mean'])<1e-13
        assert abs(means[m]['adjusted_mean']-s['contest_adjusted_kpi']['mean'])<1e-13
        public_cases=[c for c in frozen['cases'] if c['public_number'] is not None]
        assert {c['public_number'] for c in public_cases}==set(range(1,16))
        raw_public=[];adjusted_public=[]
        for c in public_cases:
            r=index[c['id'],m]
            value=c['meta']['weight']*c['meta']['final_occupied_length_m']/r['trench_length_m'] if r['status']=='ok' else 0.
            raw_public.append(value);adjusted_public.append(value if r['within_limits'] else 0.)
        all_open_valid=all(index[c['id'],m]['status']=='ok' for c in public_cases)
        public[m]={'raw_score':math.fsum(raw_public) if all_open_valid else None,'adjusted_score':math.fsum(adjusted_public)}
        if public[m]['raw_score'] is None:assert analysis['full_open15'][m]['raw_weighted_score'] is None
        else:assert abs(public[m]['raw_score']-analysis['full_open15'][m]['raw_weighted_score'])<1e-12
        assert abs(public[m]['adjusted_score']-analysis['full_open15'][m]['contest_adjusted_weighted_score'])<1e-12
        originals[m]=sha(ROOT/method['original_source'])==method['source_sha256']
    witnesses=[];unresolved=[]
    for c in selected:
        F=c['meta']['final_occupied_length_m']
        valid=[index[c['id'],m['id']] for m in methods if index[c['id'],m['id']]['status']=='ok']
        if not valid:
            unresolved.append(c['id']);continue
        best=min(valid,key=lambda r:(r['trench_length_m'],not r['within_limits'],r['method']!='online_cpp',r['method']))
        T=best['trench_length_m']
        if 20*F>=17*T:
            witnesses.append(dict(id=c['id'],input=c['input'],input_sha256=c['input_sha256'],origin=c['origin'],
                method=best['method'],source_sha256=best['source_sha256'],F=F,T=T,KPI=F/T,
                KPI_exact=str(Fraction(F,T)),volume_upper_bound=c['meta']['kpi_upper_bound_from_live_volume'],
                within_local_resource_limits=best['within_limits'],transcript=best['judge_output_file'],response_sha256=best['response_sha256']))
        else:unresolved.append(c['id'])
    assert len(witnesses)==analysis['best_observed_portfolio']['KPI_at_least_085_with_observed_legal_placement']
    catalog=dict(freeze_sha256=freeze_sha,total_selected=2537,certified_count=len(witnesses),unresolved_count=len(unresolved),
                 proof='An observed complete transcript accepted by the official checker realizes F/T >= 17/20. Therefore the maximum over legal placements is at least 0.85 for this stream.',
                 caveat='No witness among these methods does not prove the true optimum below 0.85. This is not a guarantee for any single online algorithm.',
                 witnesses=witnesses,no_witness_ids=unresolved)
    (HERE/'witnesses_085.json').write_text(json.dumps(catalog,indent=2)+'\n')
    class Links(HTMLParser):
        def __init__(self):super().__init__();self.links=[];self.scripts=[];self.capture=False
        def handle_starttag(self,tag,attrs):
            a=dict(attrs)
            if tag=='a' and 'href' in a:self.links.append(a['href'])
            if tag=='script':self.capture=a.get('type')!='application/json'
        def handle_endtag(self,tag):
            if tag=='script':self.capture=False
        def handle_data(self,text):
            if self.capture:self.scripts.append(text)
    text=(HERE/'report.html').read_text();parser=Links();parser.feed(text)
    missing=[]
    for url in parser.links:
        parsed=urlsplit(url)
        if not parsed.scheme and parsed.path and not (HERE/unquote(parsed.path)).exists():missing.append(url)
    assert not missing,missing
    assert '__TABLE__' not in text and '__DATA__' not in text and 'Промежуточные результаты — прогон продолжается' not in text
    (HERE/'report-script.js').write_text('\n'.join(parser.scripts))
    audit=dict(complete=True,primary_runs=len(rows),selected_streams=2537,extra_open15_streams=4,
               resource_rechecks=recheck['jobs'],resource_recheck_failures=recheck['failures'],
               independent_arithmetic_check=means,full_open15_check=public,
               original_source_hashes_still_match=originals,certified_085_count=len(witnesses),unresolved_085_count=len(unresolved),
               html_parser_ok=True,all_static_local_links_exist=True,visual_browser_inspection=False,
               artifact_sha256={name:sha(HERE/name) for name in ['freeze.json','records.jsonl','analysis.json','coverage.json','witnesses_085.json','report.html','REPORT.txt','resource-recheck/summary.json','regime_analysis.json','prepare.py','run.py','run_serial_v1.py','analyze.py','make_report.py','recheck_resources.py','regime_analysis.py','finalize.py']})
    (HERE/'final_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    print(json.dumps(dict(complete=True,primary_runs=len(rows),witnesses_085=len(witnesses),unresolved_085=len(unresolved),resource_rechecks=recheck['jobs']),indent=2))

if __name__=='__main__':main()
