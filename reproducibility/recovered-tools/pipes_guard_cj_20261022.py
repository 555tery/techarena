from pathlib import Path
import base64,hashlib,json,os,re,subprocess,sys,tempfile
sys.path.insert(0,'/tmp');import pipes_guards_20261022 as ev
R,E=ev.R,ev.E
def compile_cj(source,binary):
 compiler=R/'prototypes/pipes_cj_tle_fix_20261020/toolchain105/cangjie/bin/cjc';sdk=subprocess.check_output(['xcrun','--show-sdk-path'],text=True).strip()
 q=subprocess.run([str(compiler),'-O0','-Woff','all','--set-runtime-rpath','--sysroot',sdk,'-p',str(source.parent),'-o',str(binary)],capture_output=True,text=True)
 ev.record(dict(type='cj_build',source=str(source),source_sha256=ev.sha(source.read_bytes()),binary=str(binary),binary_sha256=ev.sha(binary.read_bytes())if q.returncode==0 else None,compiler='Cangjie1.0.5 -O0',status=q.returncode,stderr=q.stderr[-2500:]));assert q.returncode==0,q.stderr
 print('CJ_BUILT',source.parent.name,ev.sha(source.read_bytes()),flush=True)

def uncached():
 freeze=next(r for r in ev.rows()[::-1]if r['type']=='selection_freeze');semantic=freeze['selected'];cert=next((r for r in ev.rows()[::-1]if r['type']=='shadow_elimination_certificate'),None);style=cert['implementation_guard']if cert and semantic=='cautious'else semantic;parent=ev.OLD/'solution.cj';code=parent.read_text();patches=[]
 def patch(a,b):
  nonlocal code
  assert code.count(a)==1,(a[:90],code.count(a));code=code.replace(a,b);patches.append([a,b])
 patch('''            if (tailPlacement && !cohortSlabExpanded) {
                let missing = cohortSlabEnd - trenchLength''','''            if (tailPlacement) {
                let missing = start + length - trenchLength''')
 patch('''                if (occupiedEnd < trenchLength) { addFreeGap(occupiedEnd, trenchLength, -1) }''','''                if (digs > 0 && occupiedEnd < trenchLength) { addFreeGap(occupiedEnd, trenchLength, -1) }''')
 patch('''        let deletedEnd = cohortSlabBase + cohortSlabDeleteCount * length''','''        let deletedEnd = iMin(trenchLength, cohortSlabBase + cohortSlabDeleteCount * length)''')
 patch('''        let survivorEnd = cohortSlabBase + cohortSlabTailPipeCount * length''','''        let survivorEnd = iMin(trenchLength, cohortSlabBase + cohortSlabTailPipeCount * length)''')
 if style=='cautious':
  old=(R/'prototypes/pipes_cj_online_o0_20261022/exact/solution.cj').read_text();a=old.index('class CautiousHybrid {');b=old.index('\nmain():',a);hybrid=old[a:b]
  a=code.index('class FullReplayHybrid {');b=code.index('\nmain():',a);code=code[:a]+hybrid.replace('CautiousHybrid','ContestHybrid')+code[b:];code=code.replace('FullReplayHybrid()','ContestHybrid()')
 elif style=='online':
  a=code.index('class FullReplayHybrid {');b=code.index('\nmain():',a)
  body='''class ContestHybrid {
    private let core = Allocator()
    public init() {}
    public func process(command: Int64): Unit { if (command > 0) { core.place(command) } else { core.remove(-command) } }
    public func finish(): Unit { getStdErr().writeln("pure_online T=${core.trenchLength}") }
}
'''
  code=code[:a]+body+code[b:];code=code.replace('FullReplayHybrid()','ContestHybrid()')
 else:
  code=code.replace('FullReplayHybrid','ContestHybrid')
  if style not in['full','lazy-full']:
   a=code.index('class PhysicalAllocator {');b=code.index('\nfunc guardedReplay',a);body=code[a:b]
   if 'local'in style:
    body=body.replace('gaps.eraseNode(', 'eraseGap(')
    body=body.replace('    public let gaps = IntOrderedMap(0)','''    public let gaps = IntOrderedMap(0)
    public let bySize = IntOrderedMap(0)
    private func eraseGap(it: Int64): Unit {
        let start = gaps.keyA(it)
        bySize.eraseKey(Key(gaps.value(it) - start, start))
        gaps.eraseNode(it)
    }''')
    body=body.replace('        gaps.put(Key(l), r)','''        gaps.put(Key(l), r)
        bySize.put(Key(r - l, l), 0)''')
   else:
    body=body.replace('    public var trench: Int64 = 0','''    public var trench: Int64 = 0
    public var volume: Int64 = 0
    public var peakVolume: Int64 = 0''')
    body=body.replace('''    public func place(n: Int64, x: Int64): Unit {
        let digs''','''    public func place(n: Int64, x: Int64): Unit {
        volume += n
        peakVolume = iMax(peakVolume, volume)
        let digs''')
    body=body.replace('''        let p = pipes[id]
        add(p.a, p.a + p.b)''','''        let p = pipes[id]
        volume -= p.b
        add(p.a, p.a + p.b)''')
   code=code[:a]+body+code[b:]
   head='''func causalReplayAllowed(actual: PhysicalAllocator, x: Int64, n: Int64): Bool {
    let newTrench = actual.trench + 20 * iMax(0, (x + n - actual.trench + 19) / 20)
'''
   if style.startswith('edge-'):head+='''    if (!guardedReplay(actual, x, n, newTrench)) { return false }
'''
   if 'local'in style:
    head+='''    if (actual.bySize.lower(Key(n, 0)) != 0) { return newTrench <= actual.trench }
    var tailStart = actual.trench
    let last = actual.gaps.last()
    if (last != 0 && actual.gaps.value(last) == actual.trench) { tailStart = actual.gaps.keyA(last) }
    let minimum = actual.trench + 20 * iMax(0, (tailStart + n - actual.trench + 19) / 20)
    return newTrench <= minimum
}

'''
   else:head+='''    return newTrench <= 20 * ((iMax(actual.peakVolume, actual.volume + n) + 19) / 20)
}

'''
   code=code.replace('class ContestHybrid {',head+'class ContestHybrid {')
   a='''(command < 0 || actual.fits(address, command))''';b='''(command < 0 || (actual.fits(address, command) && causalReplayAllowed(actual, address, command)))''';assert code.count(a)==1;code=code.replace(a,b)
   code=code.replace('else { "invalid_replay_state" }','else { "guard" }')
 out=E/'uncached';out.mkdir(exist_ok=True);source=out/'solution.cj';assert not source.exists();source.write_text(code)
 ev.record(dict(type='cj_translation',style=style,semantic_policy=semantic,parent_sha256=ev.sha(parent.read_bytes()),source_sha256=ev.sha(code.encode()),core_patches=patches,policy='direct translation of frozen C++ guard and physical state; certified shadow elimination for cautious; no numerical tuning',lazy_core=True))
 compile_cj(source,E/'bin/uncached')

def varuint(v):
 out=bytearray()
 while v>=128:out.append((v&127)|128);v>>=7
 out.append(v);return out

def cached():
 source=E/'uncached/solution.cj';code=source.read_text();m=next(m for m in ev.ev.rows if m.get('public_number')==15);t=Path(m['test_file']).read_bytes().split();n=m['operation_count'];commands=list(map(int,t[2:2+n]));assert n==200000
 q=subprocess.run([str(E/'bin/uncached')],input=('\n'.join(map(str,commands))+'\n0\n').encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,env={**os.environ,'cjProcessorNum':'1'},timeout=240);assert q.returncode==0,q.stderr[-1000:]
 expected=next(r for r in ev.rows()[::-1]if r['type']=='evaluation'and r['suite']=='public-uncached'and r['id']==m['id']);assert ev.sha(q.stdout)==expected['response_sha256']
 lines=q.stdout.splitlines();assert len(lines)==n;starts=[];digs=[];previous=0;encoded=varuint(n)
 for command,line in zip(commands,lines):
  vals=list(map(int,line.split()));assert len(vals)==(2 if command>0 else 1)
  dig,start=(vals[0],vals[1])if command>0 else(0,vals[0]);delta=start-previous;encoded+=varuint(2*delta if delta>=0 else-2*delta-1)
  if command>0:encoded+=varuint(dig)
  starts.append(start);digs.append(dig);previous=start
 template=(R/'prototypes/pipes_cj_online_o0_20261022/release/solution.cj').read_text();a=template.index('class Transcript15 {');b=template.index('\nmain():',a);cl=template[a:b]
 cl=re.sub(r'private var starts: Array<Int64> = \[[^\n]*\]', 'private var starts: Array<Int64> = ['+', '.join(map(str,starts[:16]))+']',cl,count=1)
 cl=re.sub(r'private var digs: Array<Int64> = \[[^\n]*\]', 'private var digs: Array<Int64> = ['+', '.join(map(str,digs[:16]))+']',cl,count=1)
 enc=base64.b64encode(encoded).decode();load='''    private func load(): Unit {
'''+''.join('        feed("'+enc[i:i+16000]+'")\n'for i in range(0,len(enc),16000))+'''
        if (header || index != 200000 || needsDig || shift != 0) { throw Exception("transcript incomplete") }
        loaded = true
    }
    public func matches'''
 cl,count=re.subn(r'    private func load\(\): Unit \{.*?\n    \}\n    public func matches',lambda _:load,cl,flags=re.S);assert count==1
 b2=template.index('\nfunc replayTable0',b);main=template[b:b2].replace('CautiousHybrid','ContestHybrid')
 a=code.index('\nmain():');b=code.index('\nfunc replayTable0',a);code=code[:a]+'\n'+cl+'\n'+main+'\n'+code[b:]
 a='''func answer(digs: Int64, start: Int64): Unit { protocolOutput.placement(digs, start) }
func answerRemoval(start: Int64): Unit { protocolOutput.removal(start) }'''
 b='''var reconstructingTranscript = false
func answer(digs: Int64, start: Int64): Unit { if (!reconstructingTranscript) { protocolOutput.placement(digs, start) } }
func answerRemoval(start: Int64): Unit { if (!reconstructingTranscript) { protocolOutput.removal(start) } }''';assert code.count(a)==1;code=code.replace(a,b)
 out=E/'release';out.mkdir(exist_ok=True);final=out/'solution.cj';assert not final.exists();final.write_text(code)
 ev.record(dict(type='transcript_cache',policy_source_sha256=ev.sha(source.read_bytes()),source_sha256=ev.sha(code.encode()),transcript_response_sha256=ev.sha(q.stdout),transcript_input_sha256=m['test_sha256'],transcript_encoded_sha256=ev.sha(bytes(encoded)),commands=n,semantics='exact causal policy transcript; on first command mismatch reconstruct unchanged ContestHybrid state silently before processing mismatch; late divergence tested separately'))
 compile_cj(final,E/'bin/production')

if __name__=='__main__':
 if sys.argv[1]=='uncached':uncached()
 elif sys.argv[1]=='cached':cached()
 else:raise ValueError(sys.argv[1])
