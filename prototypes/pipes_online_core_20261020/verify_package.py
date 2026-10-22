"""Static artifact QA; does not claim a browser-rendered review."""
import hashlib, json, shutil, subprocess, zipfile
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit
from evaluate import HERE, sha

class ReportParser(HTMLParser):
    def __init__(self):
        super().__init__();self.links=[];self.results=[];self.ids=[];self.scripts=[];self.in_script=False
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if 'href' in a:self.links.append(a['href'])
        if 'id' in a:self.ids.append(a['id'])
        if 'data-result' in a:self.results.append(a['data-result'])
        if tag=='script':self.in_script=True
    def handle_endtag(self,tag):
        if tag=='script':self.in_script=False
    def handle_data(self,data):
        if self.in_script:self.scripts.append(data)

p=ReportParser();p.feed((HERE/'report.html').read_text())
assert len(p.ids)==len(set(p.ids))
assert len(p.results)==128
assert {v:p.results.count(v) for v in set(p.results)}==dict(win=68,tie=37,loss=23)
for link in p.links:
    q=urlsplit(link)
    if not q.scheme and not q.netloc and q.path:
        assert (HERE/unquote(q.path)).is_file(),link
syntax=False
if shutil.which('node'):
    subprocess.run(['node','--check'],input='\n'.join(p.scripts),text=True,check=True,capture_output=True);syntax=True
manifest=json.loads((HERE/'release/manifest.json').read_text())
assert sha(HERE/'release/solution.cpp')==manifest['source_sha256']
assert len(list((HERE/'release/tests').rglob('*.in')))==212
with zipfile.ZipFile(HERE/'online-core-ready.zip') as z:
    assert z.testzip() is None
    assert hashlib.sha256(z.read('online-core-ready/solution.cpp')).hexdigest()==manifest['source_sha256']
    for name in z.namelist():
        rel=name.removeprefix('online-core-ready/')
        assert z.read(name)==(HERE/'release'/rel).read_bytes()
    assert len([n for n in z.namelist() if n.endswith('.in')])==212
out=dict(static_links_passed=True,case_rows=128,filter_counts=dict(win=68,tie=37,loss=23),javascript_syntax_passed=syntax,
    archive_crc_and_all_files_match=True,source_matches_tested_frozen_hash=True,packaged_tests=212,
    visual_browser_review=False,reason='Browser automation is disabled in this Work environment; static QA only.')
(HERE/'report-qa.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
