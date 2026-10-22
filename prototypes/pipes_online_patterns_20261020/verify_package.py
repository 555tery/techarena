"""Static links, frozen provenance, archive bytes, and mock-DOM handler QA."""
import hashlib,json,shutil,subprocess,zipfile
from html.parser import HTMLParser
from urllib.parse import unquote,urlsplit
from evaluate import HERE,ROOT,sha

class Parser(HTMLParser):
    def __init__(self):
        super().__init__();self.links=[];self.results=[];self.ids=[];self.scripts=[];self.inscript=False
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if 'href' in a:self.links.append(a['href'])
        if 'id' in a:self.ids.append(a['id'])
        if 'data-result' in a:self.results.append(a['data-result'])
        if tag=='script':self.inscript=True
    def handle_endtag(self,tag):
        if tag=='script':self.inscript=False
    def handle_data(self,data):
        if self.inscript:self.scripts.append(data)

o=json.loads((HERE/'outcome.json').read_text());p=Parser();p.feed((HERE/'report.html').read_text())
assert o['confirmation_passed'] and len(p.ids)==len(set(p.ids))
assert len(p.results)==192
assert {x:p.results.count(x) for x in set(p.results)}==dict(win=37,tie=122,loss=33)
for link in p.links:
    q=urlsplit(link)
    if not q.scheme and not q.netloc and q.path:assert (HERE/unquote(q.path)).is_file(),link
assert sha(HERE/'release/solution.cpp')==o['source_sha256']
assert sha(ROOT/'prototypes/pipes_online_core_20261020/release/solution.cpp')==o['baseline_sha256']
assert len(list((HERE/'release/tests').rglob('*.in')))==307
with zipfile.ZipFile(HERE/'online-patterns-ready.zip') as z:
    assert z.testzip() is None
    assert hashlib.sha256(z.read('online-patterns-ready/solution.cpp')).hexdigest()==o['source_sha256']
    for name in z.namelist():
        rel=name.removeprefix('online-patterns-ready/')
        assert z.read(name)==(HERE/'release'/rel).read_bytes()
    assert len([n for n in z.namelist() if n.endswith('.in')])==307
syntax=handlers=False
if shutil.which('node'):
    js='\n'.join(p.scripts)
    subprocess.run(['node','--check'],input=js,text=True,check=True,capture_output=True);syntax=True
    pre='''const assert=require('node:assert/strict');
const elements={'filter':{value:'all',addEventListener(){}},'count':{},'mix-output':{}};
const controls=['stable_patterns','changing_patterns','neutral','public_prefix'].map(t=>({value:'25',dataset:{stratum:t},parentElement:{share:{},querySelector(){return this.share;}},addEventListener(){}}));
const resultRows=RESULTS.map(result=>({dataset:{result},hidden:false}));
const document={getElementById:id=>elements[id],querySelectorAll:q=>q==='.mix'?controls:resultRows};
'''.replace('RESULTS',json.dumps(p.results))
    post='''
assert.equal(elements.count.textContent,'Строк: 192');
for(const [type,n] of Object.entries({win:37,tie:122,loss:33})){elements.filter.value=type;apply();assert.equal(resultRows.filter(r=>!r.hidden).length,n);}
const readDelta=()=>Number(elements['mix-output'].textContent.split(': ')[1]);
assert.ok(Math.abs(readDelta()-(EXPECTED))<0.0000051);
for(const e of controls)e.value=e.dataset.stratum==='stable_patterns'?'100':'0';mix();assert.ok(Math.abs(readDelta()-(STABLE))<0.0000051);
for(const e of controls)e.value='0';mix();assert.ok(Math.abs(readDelta()-(EXPECTED))<0.0000051);
'''.replace('EXPECTED',repr(o['total_score_equal_mix_delta'])).replace('STABLE',repr(o['total_score_endpoints_delta']['stable_patterns']))
    subprocess.run(['node'],input=pre+js+post,text=True,check=True,capture_output=True);handlers=True
out=dict(static_links_passed=True,final_case_rows=192,filter_counts=dict(win=37,tie=122,loss=33),
    javascript_syntax_passed=syntax,mocked_DOM_filter_and_sensitivity_passed=handlers,
    archive_crc_and_all_bytes_match=True,packaged_tests=307,source_matches_frozen_tested_hash=True,
    previous_release_unchanged=True,visual_browser_review=False,
    reason='Browser automation unavailable in this Work environment; no browser rendering or screenshot inspection claimed.')
(HERE/'report-qa.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
