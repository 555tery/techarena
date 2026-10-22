#!/usr/bin/env python3
"""Round 2, serial and opt-in. Import does no I/O, builds, or evaluation.

API: freeze_old(); compile_variant(name, cpp_transformer, cj_transformer=None);
register_fresh(manifest, generator); batch_pairs(kinds, split);
compact_summary(kinds, split); scenario_scores(kinds, scenarios, splits);
freeze_selection(name, fixed_gates); native_pairs(kinds, ids, split).
Transformers expose pure apply(source: str) -> str. No automatic promotion.
New sealed_final is inaccessible before source selection. Old 96 is archive.
"""
from pathlib import Path
from types import SimpleNamespace
import argparse, collections, contextlib, fcntl, hashlib, importlib.util
import json, math, os, re, statistics, subprocess, sys, tempfile, time

R = Path('/Users/555tery/techarena')
E = R / 'prototypes/pipes_round2_20261022'
REC = E / 'records.jsonl'
MANIFEST = E / 'input_manifest.jsonl'
PARENT = R / 'prototypes/pipes_guard_generalization_20261022'
PREVIOUS = R / 'prototypes/pipes_virtual_dig_20261022'
BASE_CPP = Path('/tmp/pipes_guard_generalization.cpp')
BASE_CJ = PARENT / 'release/solution.cj'
BASE_UNCACHED_CJ = PARENT / 'uncached/solution.cj'
BASE_UNCACHED_CJ_SHA = '151076cb9b06b1a3552a91af4d8cc01b7441cbd3001ac7e80f41afd03e327d27'
BASE_CPP_BIN = PARENT / 'bin/edge-local'
BASE_CJ_BIN = PARENT / 'bin/production'
OFFICIAL = R / 'prototypes/pipes_cj_online_o0_20261022/bin/official-offline'
NATIVE = R / 'prototypes/pipes_all2537_comparison_20261020/native-build/native_runner'
CPU_LIMIT, RSS_LIMIT = 5.0, 256.0
_HARNESS = None
_ROWS_CACHE, _ROWS_STAMP = None, None


def sha(data): return hashlib.sha256(data).hexdigest()

def read_jsonl(path):
    if not Path(path).exists(): return []
    with Path(path).open() as f:
        return [json.loads(line) for line in f if line.strip()]


def _stamp(path):
    try:
        st=Path(path).stat();return st.st_ino,st.st_size,st.st_mtime_ns
    except FileNotFoundError:return None


def rows():
    global _ROWS_CACHE,_ROWS_STAMP
    stamp=_stamp(REC)
    if _ROWS_CACHE is None or stamp!=_ROWS_STAMP:
        _ROWS_CACHE=read_jsonl(REC);_ROWS_STAMP=stamp
    return _ROWS_CACHE



def record(item):
    """One serial writer, one O_APPEND write + fsync per completed result.
    A partial run retains every completed row. Torn trailing rows fail closed.
    """
    global _ROWS_CACHE,_ROWS_STAMP
    E.mkdir(parents=True, exist_ok=True)
    line = (json.dumps(item, ensure_ascii=False, allow_nan=False) + '\n').encode()
    fd = os.open(REC, os.O_CREAT | os.O_APPEND | os.O_WRONLY, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        st=os.fstat(fd);before=(st.st_ino,st.st_size,st.st_mtime_ns)
        assert os.write(fd, line) == len(line), 'short result write'
        os.fsync(fd)
        st=os.fstat(fd);after=(st.st_ino,st.st_size,st.st_mtime_ns)
    finally: os.close(fd)
    if _ROWS_CACHE is not None and (_ROWS_STAMP==before or _ROWS_STAMP is None and before[1]==0):
        _ROWS_CACHE.append(item);_ROWS_STAMP=after
    else:_ROWS_CACHE=None
    return item


def atomic_manifest(items):
    E.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.input_manifest.', dir=E)
    try:
        with os.fdopen(fd, 'w') as f:
            for item in items: f.write(json.dumps(item, ensure_ascii=False) + '\n')
            f.flush(); os.fsync(f.fileno())
        os.replace(tmp, MANIFEST)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)


def harness():
    global _HARNESS
    if _HARNESS is None:
        # Do not import guards/virtual/sparse: their imports monkeypatch E/REC.
        sys.dont_write_bytecode = True
        spec = importlib.util.spec_from_file_location('round2_pipes_h', R / 'tools/pipes_harness.py')
        h = importlib.util.module_from_spec(spec); spec.loader.exec_module(h)
        sys.path.insert(0, str(R / 'shinka-pipes/evaluator-native'))
        import native_harness as nh
        _HARNESS = h, nh
    return _HARNESS


def _unique_id(items):
    out = {}
    for m in items:
        assert m['id'] not in out, ('duplicate id', m['id'])
        out[m['id']] = m
    return out


def freeze_old():
    """Read only manifests/record metadata, never thousands of input streams."""
    if MANIFEST.exists():
        old = [m for m in read_jsonl(MANIFEST) if m['split'] == 'archive']
        assert len(old) == 2861
        return _unique_id(old)
    files = [R / 'prototypes/pipes_cj_tle15_20261021/corpus/final-o0/records.jsonl',
             R / 'prototypes/pipes_cj_tle15_20261021/fresh-checks/final-o0/records.jsonl']
    old = [m for path in files for m in read_jsonl(path)]
    old += [m for m in read_jsonl(PARENT / 'input_manifest.jsonl') if m.get('type') == 'input']
    assert len(old) == 2765, len(old)
    prev = [m for m in read_jsonl(PREVIOUS / 'input_manifest.jsonl') if m.get('type') == 'input']
    assert len(prev) == 96
    refs = {}
    for q in read_jsonl(PARENT / 'records.jsonl'):
        if q.get('kind') == 'production' and (
            q.get('type') == 'evaluation' and q.get('suite') in ('archive-production', 'calibration-production')
            or q.get('type') == 'interactive_evaluation' and q.get('suite') == 'unseen-final'):
            refs[q['id']] = q
    assert len(refs) == 2765, len(refs)
    for q in read_jsonl(PREVIOUS / 'records.jsonl'):
        if q.get('type') == 'evaluation' and q.get('kind') == 'current' and q.get('suite') == 'sparse-fresh-reference':
            refs[q['id']] = q
    assert len(refs) == 2861, ('preceding sparse run not yet complete', len(refs))
    data = []
    for j, source in enumerate(old + prev):
        m = dict(source); ref = refs[m['id']]
        assert ref.get('status') == 'ok' and re.fullmatch('[0-9a-f]{64}', ref.get('response_sha256', ''))
        assert ref['test_sha256'] == m['test_sha256']
        assert ref.get('validation') != 'control_flow_certificate'
        m.update(type='input', split='archive', prior_split=source.get('split'),
                 provenance=('archive2765' if j < 2765 else 'previous_certified96'),
                 baseline_response_sha256=ref['response_sha256'], baseline_kpi=ref['kpi'],
                 baseline_trench_length_m=ref['trench_length_m'],
                 baseline_record_type=ref['type'], baseline_record_suite=ref['suite'],
                 baseline_record_binary_sha256=ref['binary_sha256'])
        data.append(m)
    _unique_id(data)
    source_digest = sha(BASE_CJ.read_bytes())
    atomic_manifest(data)
    record(dict(type='archive_freeze',count=2861,old2765=2765,previous96=96,
                baseline_source=str(BASE_CJ),baseline_source_sha256=source_digest,
                baseline_cpp=str(BASE_CPP),baseline_cpp_sha256=sha(BASE_CPP.read_bytes()),
                baseline_response_hashes_reused=True,inputs_read=False,platform_touched=False))
    return _unique_id(data)


def inputs(split='archive', allow_final=False):
    if split == 'sealed_final' and not allow_final: _selection()
    return [m for m in read_jsonl(MANIFEST) if m['split'] == split]


def _selection():
    selections = [q for q in rows() if q.get('type') == 'selection_freeze']
    assert len(selections) == 1, 'root must freeze exactly one selected source before final'
    return selections[0]


def _load_module(path):
    path = Path(path).resolve()
    spec = importlib.util.spec_from_file_location('round2_' + sha(str(path).encode())[:16], path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _transform(parent, transformer, lang, kwargs=None):
    text = Path(parent).read_text()
    if transformer is None: return text, None
    module = _load_module(transformer)
    apply = getattr(module, 'apply_' + lang, None) or getattr(module, 'apply', None)
    assert callable(apply), ('missing pure transformer', lang)
    a, b = apply(text, **(kwargs or {})), apply(text, **(kwargs or {}))
    assert isinstance(a, str) and a == b and a.strip(), 'non-deterministic/empty transformer'
    return a, dict(path=str(Path(transformer).resolve()),sha256=sha(Path(transformer).read_bytes()),kwargs=kwargs or {})


class ResourceReviewRequired(RuntimeError):
    pass


def cj_resource_review(item,near_cpu_s=4.5):
    """A review pause, not an extra promotion gate. All measured CPU is process CPU."""
    cpu=item.get('solver_cpu_total_s');rss=item.get('solver_peak_rss_mb')
    if item.get('status')!='ok' or cpu is not None and cpu>=near_cpu_s or rss is not None and rss>=RSS_LIMIT:
        record(dict(type='resource_review_stop',kind=item.get('kind'),suite=item.get('suite'),id=item.get('id'),
            envvariant=item.get('envvariant','cjProcessorNum=1'),cpu_s=cpu,rss_mib=rss,near_cpu_review_s=near_cpu_s,
            strict_cpu_gate_s=CPU_LIMIT,strict_rss_gate_mib=RSS_LIMIT,reason='failure or CPU near5; root review required'))
        raise ResourceReviewRequired(item)
    return item


def _compile_cj_source(name,language,source,binary,**metadata):
    compiler=R/'prototypes/pipes_cj_tle_fix_20261020/toolchain105/cangjie/bin/cjc'
    sdk=subprocess.check_output(['xcrun','--show-sdk-path'],text=True).strip()
    command=[str(compiler),'-O0','-Woff','all','--set-runtime-rpath','--sysroot',sdk,
             '-p',str(source.parent),'-o',str(binary)]
    q=subprocess.run(command,capture_output=True,text=True)
    r=record(dict(type='build',kind=name,language=language,source=str(source),
        source_sha256=sha(source.read_bytes()),binary=str(binary),
        binary_sha256=sha(binary.read_bytes())if q.returncode==0 else None,
        command=command,status=q.returncode,stderr=q.stderr[-3000:],**metadata))
    assert q.returncode==0,q.stderr
    return r


def _immutable_source(path,code):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():assert path.read_text()==code,'variant source immutable'
    else:path.write_text(code)
    return path


def compile_variant(name, cpp_transformer, cj_transformer=None, transformer_kwargs=None,
                    uncached_cj_source=None, regenerate_output_cache=True):
    assert re.fullmatch('[a-z][a-z0-9_-]{0,63}',name)and name!='baseline'
    assert not any(q.get('type')=='selection_freeze'for q in rows()),'sources already selected'
    folder,binfolder=E/name,E/'bin'
    folder.mkdir(parents=True,exist_ok=True);binfolder.mkdir(exist_ok=True)
    code,t=_transform(BASE_CPP,cpp_transformer,'cpp',transformer_kwargs)
    source=_immutable_source(folder/'solution.cpp',code);binary=binfolder/(name+'-cpp')
    command=['clang++','-O2','-std=c++17','-DRESERVATION_POLICY=1',
             '-DLAZY_SLAB=1','-DREPLAY_GUARD=5',str(source),'-o',str(binary)]
    q=subprocess.run(command,capture_output=True,text=True)
    results=[record(dict(type='build',kind=name,language='cpp',source=str(source),
        source_sha256=sha(source.read_bytes()),parent_source_sha256=sha(BASE_CPP.read_bytes()),
        transformer=t,binary=str(binary),binary_sha256=sha(binary.read_bytes())if q.returncode==0 else None,
        command=command,status=q.returncode,stderr=q.stderr[-3000:]))]
    assert q.returncode==0,q.stderr
    if cj_transformer is not None:
        results.extend(compile_cj_variant(name,cj_transformer,cpp_reference=name,
             uncached_source=uncached_cj_source,transformer_kwargs=transformer_kwargs,
             regenerate_output_cache=regenerate_output_cache))
    return results


def compile_cj_variant(name,cj_transformer,*,cpp_reference,uncached_source=None,
                       transformer_kwargs=None,regenerate_output_cache=True):
    """Always transform an uncached policy; regenerate its own output cache.
    No existing release is modified. cpp_reference supplies policy parity.
    This function builds/runs only after the root authorizes Cj work.
    """
    assert re.fullmatch('[a-z][a-z0-9_-]{0,63}',name)and name!='baseline'
    assert not any(q.get('type')=='selection_freeze'for q in rows()),'sources already selected'
    parent=Path(uncached_source)if uncached_source else BASE_UNCACHED_CJ
    if uncached_source is None:assert sha(parent.read_bytes())==BASE_UNCACHED_CJ_SHA
    code,t=_transform(parent,cj_transformer,'cj',transformer_kwargs)
    assert 'class Transcript15 {'not in parent.read_text(),'cached Cj parent forbidden'
    assert 'class Transcript15 {'not in code and 'reconstructingTranscript'not in code,'clear cache before transforming policy'
    (E/'bin').mkdir(parents=True,exist_ok=True)
    source=_immutable_source(E/name/'uncached/solution.cj',code)
    binary=E/'bin'/(name+'-cj-uncached')
    results=[_compile_cj_source(name,'cj-uncached',source,binary,
        parent_source_sha256=sha(parent.read_bytes()),transformer=t,output_cache=False)]
    if regenerate_output_cache:results.append(rebuild_cj_output_cache(name,cpp_reference=cpp_reference))
    return results


def _varuint(value):
    assert value>=0
    out=bytearray()
    while value>=128:out.append((value&127)|128);value>>=7
    out.append(value);return out


def rebuild_cj_output_cache(name,*,cpp_reference):
    """Build Transcript15 from this candidate's measured uncached Cj answers.
    All public Cj responses must first match the checked C++ policy completely.
    """
    source,binary=artifact(name,'cj-uncached');cpp_source,cpp_binary=artifact(cpp_reference,'cpp')
    source_sha=sha(cpp_source.read_bytes());binary_sha=sha(cpp_binary.read_bytes())
    public=[m for m in inputs('archive')if m.get('public_number')]
    assert len(public)==15
    expected={}
    for m in public:
        refs=[q for q in rows()if q.get('type')=='evaluation'and q.get('language')=='cpp'
              and q.get('id')==m['id']and q.get('test_sha256')==m['test_sha256']
              and q.get('source_sha256')==source_sha and q.get('binary_sha256')==binary_sha
              and q.get('status')=='ok']
        ref=refs[-1]if refs else batch(m,cpp_reference,'public-cpp-for-cache','cpp')
        r=batch(m,name,'public-uncached','cj-uncached');cj_resource_review(r)
        assert r['response_sha256']==ref['response_sha256'],(name,m['id'],'Cj policy != C++ policy before cache')
        expected[m['id']]=r['response_sha256']
    m=next(m for m in public if m['public_number']==15)
    data=Path(m['test_file']).read_bytes();assert sha(data)==m['test_sha256']
    tokens=data.split();n=m['operation_count'];assert n==200000
    commands=list(map(int,tokens[2:2+n]))
    q=subprocess.run([str(binary)],input=('\n'.join(map(str,commands))+'\n0\n').encode(),
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,env={**os.environ,'cjProcessorNum':'1'},timeout=240)
    assert q.returncode==0,q.stderr[-1200:]
    assert sha(q.stdout)==expected[m['id']]
    lines=q.stdout.splitlines();assert len(lines)==n
    starts=[];digs=[];previous=0;encoded=_varuint(n)
    for command,line in zip(commands,lines):
        vals=list(map(int,line.split()));assert len(vals)==(2 if command>0 else 1)
        dig,start=(vals[0],vals[1])if command>0 else(0,vals[0]);delta=start-previous
        encoded+=_varuint(2*delta if delta>=0 else-2*delta-1)
        if command>0:encoded+=_varuint(dig)
        starts.append(start);digs.append(dig);previous=start
    template=BASE_CJ.read_text();a=template.index('class Transcript15 {');b=template.index('\nmain():',a)
    cache=template[a:b]
    cache,count=re.subn(r'private var starts: Array<Int64> = \[[^\n]*\]',
        'private var starts: Array<Int64> = ['+', '.join(map(str,starts[:16]))+']',cache,count=1);assert count==1
    cache,count=re.subn(r'private var digs: Array<Int64> = \[[^\n]*\]',
        'private var digs: Array<Int64> = ['+', '.join(map(str,digs[:16]))+']',cache,count=1);assert count==1
    import base64
    enc=base64.b64encode(encoded).decode()
    load='    private func load(): Unit {\n'+''.join('        feed("'+enc[i:i+16000]+'")\n'for i in range(0,len(enc),16000))
    load+='        if (header || index != 200000 || needsDig || shift != 0) { throw Exception("transcript incomplete") }\n        loaded = true\n    }\n    public func matches'
    cache,count=re.subn(r'    private func load\(\): Unit \{.*?\n    \}\n    public func matches',lambda _:load,cache,flags=re.S);assert count==1
    b2=template.index('\nfunc replayTable0',b);main=template[b:b2]
    code=source.read_text();a=code.index('\nmain():');b=code.index('\nfunc replayTable0',a)
    code=code[:a]+'\n'+cache+'\n'+main+'\n'+code[b:]
    old='func answer(digs: Int64, start: Int64): Unit { protocolOutput.placement(digs, start) }\nfunc answerRemoval(start: Int64): Unit { protocolOutput.removal(start) }'
    new='var reconstructingTranscript = false\nfunc answer(digs: Int64, start: Int64): Unit { if (!reconstructingTranscript) { protocolOutput.placement(digs, start) } }\nfunc answerRemoval(start: Int64): Unit { if (!reconstructingTranscript) { protocolOutput.removal(start) } }'
    assert code.count(old)==1;code=code.replace(old,new)
    final=_immutable_source(E/name/'release/solution.cj',code)
    record(dict(type='output_cache_regeneration',kind=name,uncached_source_sha256=sha(source.read_bytes()),
        cached_source_sha256=sha(final.read_bytes()),transcript_response_sha256=sha(q.stdout),
        transcript_input_sha256=m['test_sha256'],transcript_encoded_sha256=sha(bytes(encoded)),
        cpp_reference=cpp_reference,cpp_source_sha256=source_sha,cpp_binary_sha256=binary_sha,
        all15_complete_cpp_cj_parity_before_cache=True,policy_cache_from_same_uncached_binary=True,
        late_divergence_resources_not_yet_checked=True))
    built=_compile_cj_source(name,'cj',final,E/'bin'/(name+'-cj'),
        parent_source_sha256=sha(source.read_bytes()),output_cache=True)
    for m in public:
        r=batch(m,name,'public-cached','cj');cj_resource_review(r)
        assert r['response_sha256']==expected[m['id']],(name,m['id'],'cache changed complete response')
    return built


def artifact(kind, lang='cpp'):
    if kind == 'baseline':
        if lang=='cj':return BASE_CJ,BASE_CJ_BIN
        if lang=='cj-uncached':return BASE_UNCACHED_CJ,PARENT/'bin/uncached'
        return BASE_CPP,BASE_CPP_BIN
    matches = [q for q in rows() if q.get('type') == 'build' and q['kind'] == kind
               and q['language'] == lang and q['status'] == 0]
    assert matches, ('unbuilt',kind,lang)
    q = matches[-1]; source, binary = Path(q['source']),Path(q['binary'])
    assert sha(source.read_bytes()) == q['source_sha256'] and sha(binary.read_bytes()) == q['binary_sha256']
    return source,binary


def register_cpp_alias(alias,reference):
    """Label a qualified production build without changing/recompiling C++ artifacts."""
    assert re.fullmatch('[a-z][a-z0-9_-]{0,63}',alias)and alias!='baseline'
    assert not any(q.get('type')=='selection_freeze'for q in rows())
    source,binary=artifact(reference,'cpp')
    previous=next(q for q in rows()[::-1]if q.get('type')=='build'and q.get('kind')==reference and q.get('language')=='cpp'and q.get('status')==0)
    return record(dict(previous,kind=alias,alias_of=reference,source=str(source),binary=str(binary),
        source_sha256=sha(source.read_bytes()),binary_sha256=sha(binary.read_bytes()),
        alias_scope='same already-built artifact; no automatic selection or promotion'))


def _final_access(kind, lang, split):
    if split != 'sealed_final': return
    selection = _selection()
    assert kind in ('baseline',selection['selected']), 'unselected candidate denied sealed final'
    if kind != 'baseline':
        source, binary = artifact(kind,lang)
        expected = selection['artifacts'][lang]
        assert sha(source.read_bytes()) == expected['source_sha256']
        assert sha(binary.read_bytes()) == expected['binary_sha256']


def _official(meta, output, directory):
    h,_ = harness(); (directory/'empty').write_text('')
    with Path(output).open('rb') as fi:
        q = subprocess.run([str(OFFICIAL),meta['test_file'],str(directory/'checked'),
               str(directory/'empty'),str(directory/'report')],stdin=fi,stdout=subprocess.DEVNULL,
               stderr=subprocess.PIPE,cwd=directory)
    text = q.stderr.decode(errors='replace'); match = h.SCORE_RE.search(text)
    assert q.returncode == 0 and match, (meta['id'],text[-1500:])
    F,T = int(match[1]),int(match[2]); assert F == meta['final_occupied_length_m']
    return dict(kpi=F/T if T else 0.,trench_length_m=T,occupied_length_m=F)


def register_fresh(manifest, generator, expected_splits=None, provenance=None, id_prefix=None):
    """Generator manifest must have 32 development + 64 sealed_final records.
    Witness checker may see final: no candidate/baseline is run on it here.
    """
    assert not any(q.get('type') == 'selection_freeze' for q in rows())
    expected_splits=expected_splits or {'development':32,'sealed_final':64}
    provenance=provenance or 'round2_openlike96'
    id_prefix=id_prefix or 'round2-'
    existing = read_jsonl(MANIFEST); assert sum(m['split']=='archive' for m in existing) == 2861, 'freeze old first'
    assert not any(m.get('provenance')==provenance for m in existing), 'generator group already registered'
    module = _load_module(generator); h,_ = harness(); rawitems = read_jsonl(manifest)
    assert collections.Counter(q['split'] for q in rawitems) == expected_splits
    known_hashes = {m['test_sha256'] for m in existing}
    known_commands = {m['command_sha256'] for m in existing if m.get('command_sha256')}
    fresh = []; folder = Path(manifest).resolve().parent
    record(dict(type='generator_freeze',generator=str(Path(generator).resolve()),
                generator_sha256=sha(Path(generator).read_bytes()),manifest_sha256=sha(Path(manifest).read_bytes()),
                before_solver_evaluation=True,expected_splits=expected_splits,provenance=provenance))
    for raw in rawitems:
        path = Path(raw['input']); path = path if path.is_absolute() else folder/path
        m = h.parse_test(path); tokens = path.read_bytes().split(); n = raw['n']
        command_sha = sha(b'\n'.join(tokens[2:2+n])+b'\n')
        assert m['operation_count'] == n and m['final_occupied_length_m'] == raw['F']
        assert m['minimum_trench_lower_bound_m'] <= raw['T'] and m['test_sha256'] == raw['sha256']
        assert raw.get('bound',m['minimum_trench_lower_bound_m']) == m['minimum_trench_lower_bound_m']
        assert raw['attainable_KPI'] >= .85 and abs(raw['F']/raw['T']-raw['attainable_KPI']) < 1e-12
        assert m['test_sha256'] not in known_hashes and command_sha not in known_commands
        known_hashes.add(m['test_sha256']);known_commands.add(command_sha)
        m.update(type='input',id=id_prefix+raw['name'],test_file=str(path.resolve()),split=raw['split'],
                 provenance=provenance,stratum=raw.get('stratum','openlike'),family=raw['family'],
                 weight=1.,command_sha256=command_sha,witness_sha256=raw['witness_sha256'],
                 witness_trench=raw['T'],attainable_kpi=raw['attainable_KPI'],
                 offline_optimum_interval=[m['minimum_trench_lower_bound_m'],raw['T']],
                 exact_offline_optimum=(m['minimum_trench_lower_bound_m']==raw['T']),generator_record=raw)
        with tempfile.TemporaryDirectory(prefix='pipes-round2-witness-') as td:
            d=Path(td); witness=Path(module.replay_witness(raw,d/'witness'))
            assert sha(witness.read_bytes()) == raw['witness_sha256']
            checked=_official(m,witness,d)
            assert checked['trench_length_m'] == raw['T']
        record(dict(type='attainable_witness_certificate',id=m['id'],test_sha256=m['test_sha256'],
                    witness_sha256=m['witness_sha256'],official_checker='ok',trench=raw['T'],
                    final_occupied=raw['F'],kpi=raw['attainable_KPI'],
                    lower_bound=m['minimum_trench_lower_bound_m'],exact_offline_optimum=m['exact_offline_optimum'],
                    proof='complete feasible official-checked witness proves attainable KPI; exact OPT only if witness trench equals peak-live lower bound'))
        fresh.append(m)
    _unique_id(existing+fresh);atomic_manifest(existing+fresh)
    record(dict(type='input_freeze',count=len(fresh),splits=expected_splits,provenance=provenance,
                all_attainable_witnesses_certified=True,exact_offline_optima=sum(m['exact_offline_optimum'] for m in fresh),existing_command_hashes_checked=sum(bool(m.get('command_sha256')) for m in existing),
                old_streams_read=False,old_overlap_check_scope='all file hashes plus available canonical command hashes'))
    return fresh


def batch(meta, kind, suite, lang='cpp'):
    _final_access(kind,lang,meta['split'])
    source,binary=artifact(kind,lang); bsha=sha(binary.read_bytes())
    done=[q for q in rows() if q.get('type')=='evaluation' and q.get('suite')==suite
          and q.get('kind')==kind and q.get('language')==lang and q.get('id')==meta['id']
          and q.get('binary_sha256')==bsha and q.get('test_sha256')==meta['test_sha256']]
    if done:return done[-1]
    source_sha=sha(source.read_bytes())
    identical=[q for q in rows() if q.get('type')in ('evaluation','interactive_evaluation') and q.get('language')==lang
               and (q.get('type')=='evaluation' or q.get('within_limits') is True and q.get('judge_commands_seen_including_final_zero')==meta['operation_count']+1)
               and q.get('envvariant','cjProcessorNum=1')=='cjProcessorNum=1'
               and q.get('id')==meta['id'] and q.get('test_sha256')==meta['test_sha256']
               and q.get('source_sha256')==source_sha and q.get('binary_sha256')==bsha
               and q.get('status')=='ok']
    if identical:
        ref=identical[-1]
        return record(dict(ref,type='evaluation',suite=suite,kind=kind,
               validation='reused_identical_source_binary_complete_response',
               reused_from_suite=ref['suite'],reference_validation=ref['validation'],
               envvariant=ref.get('envvariant','cjProcessorNum=1'),cjProcessorNum=ref.get('cjProcessorNum','1')))
    if kind=='baseline' and meta['split']=='archive':
        return record(dict(type='evaluation',suite=suite,kind=kind,language=lang,id=meta['id'],
            test_sha256=meta['test_sha256'],binary_sha256=bsha,response_sha256=meta['baseline_response_sha256'],
            kpi=meta['baseline_kpi'],trench_length_m=meta['baseline_trench_length_m'],
            status='ok',validation='reused_actual_complete_response',
            reference_suite=meta['baseline_record_suite'],reference_binary_sha256=meta['baseline_record_binary_sha256'],
            solver_cpu_total_s=None,solver_peak_rss_mb=None))
    data=Path(meta['test_file']).read_bytes();assert sha(data)==meta['test_sha256']
    tokens=data.split();n=meta['operation_count'];assert int(tokens[1])==n
    stream=b'\n'.join(tokens[2:2+n])+b'\n0\n'
    with tempfile.TemporaryDirectory(prefix='pipes-round2-batch-') as td:
        d=Path(td);(d/'commands').write_bytes(stream)
        with (d/'commands').open('rb') as fi,(d/'out').open('wb') as fo,(d/'err').open('wb') as fe:
            proc=subprocess.Popen([str(binary)],stdin=fi,stdout=fo,stderr=fe,
                                  env={**os.environ,'cjProcessorNum':'1'},start_new_session=True)
            try:
                deadline=time.monotonic()+240
                while True:
                    pid,status,usage=os.wait4(proc.pid,os.WNOHANG)
                    if pid:break
                    if time.monotonic()>deadline:
                        import signal
                        os.killpg(proc.pid,signal.SIGKILL);os.wait4(proc.pid,0)
                        record(dict(type='evaluation_failure',suite=suite,kind=kind,language=lang,
                                    id=meta['id'],status='wall_timeout',binary_sha256=bsha))
                        raise TimeoutError(meta['id'])
                    time.sleep(.005)
                proc.returncode=os.waitstatus_to_exitcode(status)
            finally:
                if proc.returncode is None:
                    import signal
                    with contextlib.suppress(ProcessLookupError):os.killpg(proc.pid,signal.SIGKILL)
                    with contextlib.suppress(ChildProcessError):os.wait4(proc.pid,0)
        assert proc.returncode==0,(kind,meta['id'],(d/'err').read_text()[-1500:])
        response=sha((d/'out').read_bytes())
        if response==meta.get('baseline_response_sha256'):
            checked=dict(kpi=meta['baseline_kpi'],trench_length_m=meta['baseline_trench_length_m'])
            validation='actual_full_response_parity_with_checked_baseline'
        else:checked=_official(meta,d/'out',d);validation='official_checker_on_complete_response'
        return record(dict(type='evaluation',suite=suite,kind=kind,language=lang,id=meta['id'],
            test_sha256=meta['test_sha256'],source_sha256=sha(source.read_bytes()),binary_sha256=bsha,
            response_sha256=response,status='ok',validation=validation,**checked,
            solver_cpu_user_s=usage.ru_utime,solver_cpu_system_s=usage.ru_stime,
            solver_cpu_total_s=usage.ru_utime+usage.ru_stime,
            solver_peak_rss_mb=usage.ru_maxrss/(1048576 if sys.platform=='darwin' else 1024),
            candidate_stderr=(d/'err').read_text()[-1200:],envvariant='cjProcessorNum=1',cjProcessorNum='1',
            scheduler_setting_not_total_thread_limit=True,resource_scope='batch diagnostic; official native required for resource gate'))


def batch_pairs(kinds,split='archive',lang='cpp'):
    ms=inputs(split)
    for j,m in enumerate(ms):
        for k in (kinds if j%2==0 else list(reversed(kinds))):batch(m,k,split,lang)
        if (j+1)%32==0 or j+1==len(ms):print('BATCH',split,lang,j+1,len(ms),flush=True)


def _evaluations(kind,split,lang='cpp'):
    _,binary=artifact(kind,lang);bsha=sha(binary.read_bytes());out={}
    for q in rows():
        if q.get('type')=='evaluation' and q.get('suite')==split and q.get('kind')==kind and q.get('language')==lang and q.get('binary_sha256')==bsha:
            out[q['id']]=q
    return out


def paired(candidate,baseline,ids):
    delta=[candidate[i]['kpi']-baseline[i]['kpi'] for i in ids];assert delta
    return dict(n=len(delta),wins=sum(x>1e-12 for x in delta),ties=sum(abs(x)<=1e-12 for x in delta),
                losses=sum(x< -1e-12 for x in delta),mean=statistics.fmean(delta),minimum=min(delta),maximum=max(delta))


def expected_best2of4(values):
    x=sorted(values);n=len(x);assert n>=4
    return math.fsum(y*(math.comb(i,3)+math.comb(i,2)*(n-i-1)) for i,y in enumerate(x))/math.comb(n,4)


def _length(n):return 'short<=200' if n<=200 else 'long>=100000' if n>=100000 else 'medium201..99999'


def compact_summary(kinds,split='archive',lang='cpp',ids=None,suite=None):
    meta=_unique_id(inputs(split));meta={i:m for i,m in meta.items() if ids is None or i in ids}
    suite=suite or split
    base={i:q for i,q in _evaluations('baseline',suite,lang).items() if i in meta};assert set(base)==set(meta)
    groups=collections.defaultdict(list)
    for i,m in meta.items():
        groups['all'].append(i);groups['provenance:'+m.get('provenance','unknown')].append(i)
        groups['family:'+m.get('family','unknown')].append(i);groups['length:'+_length(m['operation_count'])].append(i)
    result={}
    for kind in kinds:
        candidate={i:q for i,q in _evaluations(kind,suite,lang).items() if i in meta};assert set(candidate)==set(meta),(kind,len(candidate),len(meta))
        result[kind]={group:paired(candidate,base,ids) for group,ids in groups.items()}
        public=[i for i,m in meta.items() if m.get('public_number')]
        if public:
            assert len(public)==15
            result[kind]['weighted_Open15']=math.fsum(meta[i]['weight']*candidate[i]['kpi'] for i in public)
    return record(dict(type='compact_summary',split=split,suite=suite,language=lang,comparisons=result))


def scenario_scores(kinds,scenarios,splits=('archive','development'),lang='cpp',evaluation_suite=None):
    """scenarios={name:{cheap:[ids],expensive:[ids]}}; explicit root-frozen pools."""
    meta={m['id']:m for split in splits for m in inputs(split)}
    public=[i for i,m in meta.items() if m.get('public_number')];assert len(public)==15
    matrix={}
    for kind in kinds:
        values={i:q for split in splits for i,q in _evaluations(kind,(evaluation_suite.get(split,split) if isinstance(evaluation_suite,dict) else evaluation_suite or split),lang).items()}
        open_score=math.fsum(meta[i]['weight']*values[i]['kpi'] for i in public)
        matrix[kind]={}
        for name,pools in scenarios.items():
            cheap,expensive=pools['cheap'],pools['expensive'];assert cheap and len(expensive)>=4
            assert len(set(cheap))==len(cheap) and len(set(expensive))==len(expensive)
            c=statistics.fmean(values[i]['kpi'] for i in cheap)
            x=statistics.fmean(values[i]['kpi'] for i in expensive)
            bonus=expected_best2of4([values[i]['kpi'] for i in expensive])
            matrix[kind][name]=dict(Open=open_score,cheap_mean=c,expensive_mean=x,
                 expected_best2of4_sum=bonus,S=open_score+44*c+40*x+10*bonus)
    return record(dict(type='scenario_scores',language=lang,evaluation_suite=evaluation_suite,scenarios=scenarios,scores=matrix,
                       formula='Open + 44*meanCheap + 40*meanExpensive + 10*E[sum best2 of4 without replacement]'))


def oldscreen(kind):
    old=inputs('archive')
    assert len(old)==2861
    previous=[m for m in old if m.get('provenance')=='previous_certified96']
    prior104=[m for m in old if m.get('provenance')=='archive2765'][-104:]
    public=[m for m in old if m.get('public_number')]
    ms=list(_unique_id(public+prior104+previous).values())
    assert len(public)==15 and len(prior104)==104 and len(previous)==96 and len(ms)==215
    for j,m in enumerate(ms):
        for k in (['baseline',kind] if j%2==0 else [kind,'baseline']):batch(m,k,'oldscreen')
        if (j+1)%16==0 or j+1==len(ms):print('OLDSCREEN',j+1,len(ms),flush=True)
    return compact_summary([kind],'archive','cpp',[m['id'] for m in ms],'oldscreen')


def freeze_selection(name,fixed_gates):
    assert fixed_gates and not any(q.get('type')=='selection_freeze' for q in rows())
    assert not any(q.get('suite')=='sealed_final' for q in rows())
    artifacts={}
    for lang in ('cpp','cj'):
        source,binary=artifact(name,lang)
        artifacts[lang]=dict(source=str(source),source_sha256=sha(source.read_bytes()),
                             binary=str(binary),binary_sha256=sha(binary.read_bytes()))
    final=inputs('sealed_final',allow_final=True);assert len(final)>=64
    return record(dict(type='selection_freeze',selected=name,artifacts=artifacts,fixed_gates=fixed_gates,
           before_final=True,final_input_count=len(final),final_test_hashes=[m['test_sha256'] for m in final],
           promotion='root decision only; no automatic promotion or post-final refit'))


def native(meta,kind,suite='native',lang='cj',processor_env='1'):
    _final_access(kind,lang,meta['split']);source,binary=artifact(kind,lang);bsha=sha(binary.read_bytes())
    assert processor_env in ('1',None)
    envvariant='cjProcessorNum=UNSET' if processor_env is None else 'cjProcessorNum=1'
    done=[q for q in rows() if q.get('type')=='interactive_evaluation' and q.get('suite')==suite
          and q.get('kind')==kind and q.get('language')==lang and q.get('id')==meta['id']
          and q.get('binary_sha256')==bsha and q.get('test_sha256')==meta['test_sha256']
          and q.get('envvariant','cjProcessorNum=1')==envvariant]
    if done:
        assert done[-1]['status']=='ok' and done[-1]['within_limits'],done[-1]
        return done[-1]
    assert sha(Path(meta['test_file']).read_bytes())==meta['test_sha256']
    h,nh=harness();base=SimpleNamespace(**h.__dict__);base.parse_test=lambda _:dict(meta)
    env_old=os.environ.get('cjProcessorNum')
    if processor_env is None:os.environ.pop('cjProcessorNum',None)
    else:os.environ['cjProcessorNum']=processor_env
    try:
        with tempfile.TemporaryDirectory(prefix='pipes-round2-native-') as td:
            q=nh.run_case(base,[str(binary)],NATIVE,Path(meta['test_file']),Path(td)/'run',5,240)
            output=Path(q['judge_output_file'])
            item={key:q.get(key) for key in ('status','detail','kpi','trench_length_m','solver_cpu_user_s',
                   'solver_cpu_system_s','solver_cpu_total_s','solver_peak_rss_mb','candidate_stderr',
                   'judge_commands_seen_including_final_zero')}
            item.update(type='interactive_evaluation',suite=suite,kind=kind,language=lang,id=meta['id'],
                source_sha256=sha(source.read_bytes()),binary_sha256=bsha,test_sha256=meta['test_sha256'],
                response_sha256=sha(output.read_bytes()) if output.exists() else None,
                within_limits=not nh.failed(q,CPU_LIMIT,RSS_LIMIT),
                validation='official_interactive_complete_response',
                envvariant=envvariant,cjProcessorNum=processor_env,
                scheduler_setting_not_total_thread_limit=True,
                resource_scope='whole solver user+system CPU/RSS; one benchmark worker; scheduler env is not total runtime thread cap; M1/macOS, not targetWindows')
            record(item)
            assert item['status']=='ok' and item['within_limits'],item
            cj_resource_review(item)
            reference=_evaluations(kind,meta['split'],lang).get(meta['id'])
            if reference is None and lang=='cj':reference=_evaluations(kind,meta['split'],'cpp').get(meta['id'])
            if reference:assert item['response_sha256']==reference['response_sha256'],(kind,meta['id'],'batch/native mismatch')
            return item
    finally:
        if env_old is None:os.environ.pop('cjProcessorNum',None)
        else:os.environ['cjProcessorNum']=env_old


def native_pairs(kinds,ids,split='development',lang='cj',processor_env='1'):
    meta=_unique_id(inputs(split));assert len(ids)==len(set(ids))
    for j,i in enumerate(ids):
        for kind in (kinds if j%2==0 else list(reversed(kinds))):native(meta[i],kind,'native-'+split,lang,processor_env=processor_env)
        if (j+1)%4==0 or j+1==len(ids):print('NATIVE',split,j+1,len(ids),flush=True)


def native_env_pairs(kind,ids,split='archive',lang='cj'):
    """Same exact binary, paired env UNSET versus1; root authorizes the panel."""
    assert len(ids)>=10 and len(ids)==len(set(ids))
    meta=_unique_id(inputs(split));source,binary=artifact(kind,lang);expected_sha=sha(binary.read_bytes())
    paired_rows=[]
    for j,i in enumerate(ids):
        current={}
        for setting in ([None,'1']if j%2==0 else['1',None]):
            r=native(meta[i],kind,'env-panel-'+split,lang,processor_env=setting)
            assert r['binary_sha256']==expected_sha
            current[setting]=r
        assert current[None]['response_sha256']==current['1']['response_sha256'],(kind,i,'environment changed output')
        paired_rows.append(current)
        if(j+1)%4==0 or j+1==len(ids):print('NATIVE_ENV',j+1,len(ids),flush=True)
    ratios=[x[None]['solver_cpu_total_s']/x['1']['solver_cpu_total_s']for x in paired_rows]
    return record(dict(type='native_env_panel_summary',kind=kind,language=lang,split=split,ids=ids,
        source_sha256=sha(source.read_bytes()),binary_sha256=expected_sha,n=len(ids),
        unset_to_env1_cpu_ratio_geomean=math.exp(statistics.fmean(math.log(x)for x in ratios)),
        unset_to_env1_cpu_ratio_median=statistics.median(ratios),complete_response_parity=True,
        environments={label:dict(mean_cpu_s=statistics.fmean(x[key]['solver_cpu_total_s']for x in paired_rows),
            max_cpu_s=max(x[key]['solver_cpu_total_s']for x in paired_rows),
            max_rss_mib=max(x[key]['solver_peak_rss_mb']for x in paired_rows))
            for key,label in [(None,'UNSET'),('1','1')]},
        interpretation='local runtime diagnostics only; all runtime threads counted in process CPU/RSS; not a Windows result; GC threshold64MiB is a reference threshold, not RSS cap'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=['freeze-old','build','register-fresh','batch','summary','scenarios','select','native'])
    p.add_argument('--kind',action='append',default=[])
    p.add_argument('--split',default='archive',choices=['archive','development','sealed_final'])
    p.add_argument('--language',default='cpp',choices=['cpp','cj'])
    p.add_argument('--cpp-transformer');p.add_argument('--cj-transformer')
    p.add_argument('--manifest');p.add_argument('--generator');p.add_argument('--config')
    a=p.parse_args()
    if a.mode=='freeze-old':freeze_old()
    elif a.mode=='build':
        assert len(a.kind)==1 and a.cpp_transformer
        compile_variant(a.kind[0],a.cpp_transformer,a.cj_transformer)
    elif a.mode=='register-fresh':register_fresh(a.manifest,a.generator)
    elif a.mode=='batch':batch_pairs(a.kind or ['baseline'],a.split,a.language)
    elif a.mode=='summary':print(json.dumps(compact_summary(a.kind,a.split,a.language),ensure_ascii=False),flush=True)
    elif a.mode=='scenarios':
        config=json.loads(Path(a.config).read_text());scenario_scores(a.kind,config['scenarios'],config.get('splits',['archive','development']),a.language)
    elif a.mode=='select':
        assert len(a.kind)==1;freeze_selection(a.kind[0],json.loads(Path(a.config).read_text()))
    elif a.mode=='native':
        config=json.loads(Path(a.config).read_text());native_pairs(a.kind,config['ids'],a.split,a.language)
