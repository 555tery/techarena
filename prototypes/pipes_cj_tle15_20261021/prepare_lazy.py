#!/usr/bin/env python3
import base64,hashlib,json,re
from pathlib import Path
HERE=Path(__file__).resolve().parent
src=(HERE/'candidate-soa/solution.cj').read_text(); base=hashlib.sha256(src.encode()).hexdigest()
entries=[];audit=[]
for table in range(15):
 m=re.search(rf'func replayTable{table}\(\): ReplayTable \{{(.*?)\n\}}',src,re.S); assert m
 text=''.join(re.findall(r'decoder.feed\("([A-Za-z0-9+/=]+)"\)',m[1]));data=base64.b64decode(text);vals=[];v=shift=0
 for byte in data:
  v|=(byte&127)<<shift
  if byte&128:shift+=7
  else:vals.append(v);v=shift=0
 assert shift==0
 count=vals[0];idx=1;cmd=[];pos=[];prev=0
 for k in range(count):
  z=vals[idx];idx+=1;n=-(z+1)//2 if z&1 else z//2;cmd.append(n)
  if n>0:
   z=vals[idx];idx+=1;prev+=-(z+1)//2 if z&1 else z//2;pos.append(prev)
  else:pos.append(-1)
 assert idx==len(vals)
 pcount=min(16,count)
 ints=lambda xs:', '.join(map(str,xs))
 entries.append(f'    tables.add(DeferredReplayTable({table}, {count}, [{ints(cmd[:pcount])}], [{ints(pos[:pcount])}]))')
 audit.append(dict(table=table,commands=count,prefix_count=pcount,commands_sha256=hashlib.sha256(json.dumps(cmd).encode()).hexdigest(),positions_sha256=hashlib.sha256(json.dumps(pos).encode()).hexdigest(),prefix_commands=cmd[:pcount],prefix_positions=pos[:pcount]))
wrapper='''// Decode the identical public tail only after its observed prefix survives.
class DeferredReplayTable {
    public let commandCount: Int64
    private let tableIndex: Int64
    private let prefixCommands: Array<Int64>
    private let prefixPositions: Array<Int64>
    private var full: Option<ReplayTable> = None
    public init(index: Int64, count: Int64, commands: Array<Int64>, positions: Array<Int64>) {
        tableIndex = index; commandCount = count
        prefixCommands = commands; prefixPositions = positions
    }
    public func commandAt(step: Int64): Int64 {
        if (step < prefixCommands.size) { return prefixCommands[step] }
        if (full.isNone()) { full = Some(loadFullReplayTable(tableIndex)) }
        if (let Some(table) <- full) { return table.commands[step] }
        throw IllegalStateException("missing full replay")
    }
    public func positionAt(step: Int64): Int64 {
        if (step < prefixPositions.size) { return prefixPositions[step] }
        if (let Some(table) <- full) { return table.positions[step] }
        throw IllegalStateException("position queried before command")
    }
}

func loadFullReplayTable(index: Int64): ReplayTable {
'''+''.join(f'    if (index == {i}) {{ return replayTable{i}() }}\n' for i in range(15))+'''    throw IllegalArgumentException("table index")
}

'''
# Option.isNone is already used by the current source; use a pattern rather than depend on it.
wrapper=wrapper.replace('if (full.isNone()) { full = Some(loadFullReplayTable(tableIndex)) }','''if (let Some(table) <- full) { return table.commands[step] }
        full = Some(loadFullReplayTable(tableIndex))''')
marker='// Streaming base64 + unsigned varint decoder.';assert src.count(marker)==1;src=src.replace(marker,wrapper+marker)
old='func loadReplayTables(): ArrayList<ReplayTable> {\n    let tables = ArrayList<ReplayTable>()\n'+''.join(f'    tables.add(replayTable{i}())\n' for i in range(15))+'    return tables\n}'
new='func loadReplayTables(): ArrayList<DeferredReplayTable> {\n    let tables = ArrayList<DeferredReplayTable>()\n'+'\n'.join(entries)+'\n    return tables\n}'
assert src.count(old)==1;src=src.replace(old,new)
for old,new in [('step >= table.commands.size || table.commands[step] != command','step >= table.commandCount || table.commandAt(step) != command'),('let position = table.positions[step]','let position = table.positionAt(step)'),('tables = ArrayList<ReplayTable>()','tables = ArrayList<DeferredReplayTable>()')]:
 assert src.count(old)==1,(old,src.count(old));src=src.replace(old,new)
out=HERE/'candidate-lazy';out.mkdir(exist_ok=True);(out/'solution.cj').write_text(src)
(out/'source.json').write_text(json.dumps(dict(base_sha256=base,source_sha256=hashlib.sha256(src.encode()).hexdigest(),changes=['Identical first16 commands/positions eagerly; full identical decoder on first active request beyond prefix.','Original15 full table functions and table order retained byte-for-byte.','No policy threshold change; only loading schedule of constant public data.'],tables=audit),indent=2)+'\n')
print(out)
