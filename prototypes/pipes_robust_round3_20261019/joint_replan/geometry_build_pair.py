#!/usr/bin/env python3
import json, sys, hashlib
from pathlib import Path
REPO=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(REPO/'prototypes/pipes_open15_adversary_20261019'))
from construct import decode
src=REPO/'prototypes/pipes_robust_round2_20261019/final/solution.cpp'
tables=decode(src)
j=json.loads((REPO/'prototypes/pipes_open15_overfit_20261019/joint.json').read_text())
case_idxs=[7,12]
sel=set()
positions={}
for idx in case_idxs:
    case=j['cases'][idx]
    cmds,pos=tables[idx]
    assert list(cmds)==case['commands'], (idx,len(cmds),len(case['commands']))
    assert len(case['block_ids'])==len(cmds)
    assert len(pos)==len(cmds)
    p=0
    for command, block, x in zip(cmds,case['block_ids'],pos):
        if command>0:
            assert block>=0 and x is not None
            sel.add(block)
            if block in positions:
                assert positions[block]==x,(block,positions[block],x)
            positions[block]=x
        else:
            assert block<0 and x is None
# Remap selected timeline endpoints to a compressed exact interval coordinate system.
old_to_new={7:0,12:1}
blocks=[]
endpoints=set()
for old in sorted(sel):
    b=j['blocks'][str(old)] if isinstance(j['blocks'],dict) else j['blocks'][old]
    spans=[]
    for l,r,c in b['intervals']:
        if c in old_to_new:
            spans.append([l,r,old_to_new[c]])
            endpoints.add(l); endpoints.add(r)
    assert spans,(old,b)
    blocks.append((old,b['length'],positions[old],b['first'],spans))
coords=sorted(endpoints); rank={x:i for i,x in enumerate(coords)}
for case_idx in case_idxs:
    c=j['cases'][case_idx]
    print(f"Open{case_idx+1}: lower_T={c['lower_T']} F={c['F']} commands={len(c['commands'])}")
print(f"selected blocks={len(blocks)} common prefix=388 commands; prefix allocs=210; unique endpoints={len(coords)}")
# Input of pack.cpp: n nt k, weights/F, then len seed first m, spans.
inputp=OUT/'geometry_open8_13_pair.in'
with inputp.open('w') as f:
    f.write(f"{len(blocks)} {len(coords)-1} 2\n")
    for idx in case_idxs:
        c=j['cases'][idx]; f.write(f"{c['weight']} {c['F']}\n")
    for old,length,seed,first,spans in blocks:
        remapped=[[rank[l],rank[r],c] for l,r,c in spans]
        f.write(f"{length} {seed} {first} {len(remapped)}\n")
        for x in remapped: f.write(f"{x[0]} {x[1]} {x[2]}\n")
# Reverse map metadata. Current candidate positions by global block ID are the seeds.
meta={"target_source":str(src.relative_to(REPO)),"target_source_sha256":hashlib.sha256(src.read_bytes()).hexdigest(),"pair":[8,13],"case_indices_zero_based":case_idxs,"common_prefix_commands":388,"common_prefix_allocations":210,"selected_block_count":len(blocks),"pair_input":str(inputp.relative_to(REPO)),"coordinate_endpoints_count":len(coords),"coordinate_compression":"ranked all half-open lifetime endpoints; preserves interval overlap","targets_T":{"8":j['cases'][7]['lower_T'],"13":j['cases'][12]['lower_T']},"block_ids":[x[0] for x in blocks],"seeds":[x[2] for x in blocks],"lengths":[x[1] for x in blocks],"current_tables_sha256":hashlib.sha256(src.read_bytes()).hexdigest()}
(OUT/'geometry_pair_provenance.json').write_text(json.dumps(meta,indent=2)+'\n')
