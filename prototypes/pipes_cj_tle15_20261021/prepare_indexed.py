#!/usr/bin/env python3
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
src=(HERE/'candidate-metadata/solution.cj').read_text()
base_sha=hashlib.sha256(src.encode()).hexdigest()
def replace(old,new,n=1):
 global src
 assert src.count(old)==n,(old[:100],src.count(old),n)
 src=src.replace(old,new)
# Read only the requested scalar key component, retaining the native owner.
marker='    public func key(node: Int64): Key { keys[node] }'
extra=''
for field,offset in [('A',0),('B',1),('C',2)]:
 extra+=f'''
    public func key{field}(node: Int64): Int64 {{
        if (node < 0 || node >= keys.size) {{ throw IndexOutOfBoundsException("AVL key index") }}
        let data = keys.borrowData()
        let result = unsafe {{ data.read(node * 3 + {offset}) }}
        blackBox(this)
        return result
    }}'''
replace(marker,marker+extra,2)
# Balanced argument scan, including nested Key(), map index expressions and calls.
pieces=[]; pos=0; count=0
while True:
 i=src.find('.key(',pos)
 if i<0: pieces.append(src[pos:]); break
 j=i+5; depth=1
 while depth:
  if src[j]=='(': depth+=1
  elif src[j]==')': depth-=1
  j+=1
 if src[j:j+2] in ('.a','.b','.c'):
  pieces.append(src[pos:i]+'.key'+src[j+1].upper()+'('+src[i+5:j]);pos=j+2;count+=1
 else:
  pieces.append(src[pos:j]);pos=j
src=''.join(pieces)
replace('    private let gapRelease = FastIntVector()','''    private let gapRelease = FastIntVector()
    private let gapSizeId = FastIntVector()
    private let gapAgeId = FastIntVector()
    private let gapPolicyId = FastIntVector()''')
replace('public init() { pipes.add(Pipe()); gapOwner.add(0); gapRelease.add(0) }','''public init() {
        pipes.add(Pipe()); gapOwner.add(0); gapRelease.add(0)
        gapSizeId.add(0); gapAgeId.add(0); gapPolicyId.add(0)
    }''')
replace('        while (gapOwner.size <= added) { gapOwner.add(0); gapRelease.add(0) }','''        while (gapOwner.size <= added) {
            gapOwner.add(0); gapRelease.add(0)
            gapSizeId.add(0); gapAgeId.add(0); gapPolicyId.add(0)
        }''')
replace('freeBySizeAge.eraseKey(Key(gapLength, gapRelease[it], start))','freeBySizeAge.eraseNode(gapAgeId[it])')
replace('freeBySize.eraseKey(Key(gapLength, start))','freeBySize.eraseNode(gapSizeId[it])')
replace('freeBySizeCohort[cohort].eraseKey(Key(gapLength, start))','freeBySizeCohort[cohort].eraseNode(gapPolicyId[it])')
replace('freeBySizeShared.eraseKey(Key(gapLength, start))','freeBySizeShared.eraseNode(gapPolicyId[it])')
replace('        freeBySize.put(Key(gapLength, mergedStart), 0)','        gapSizeId[added] = freeBySize.put(Key(gapLength, mergedStart), 0)')
replace('        freeBySizeAge.put(Key(gapLength, mergedFreedAt, mergedStart), 0)','        gapAgeId[added] = freeBySizeAge.put(Key(gapLength, mergedFreedAt, mergedStart), 0)')
replace('freeBySizeCohort[mergedCohort].put(Key(gapLength, mergedStart), 0)','gapPolicyId[added] = freeBySizeCohort[mergedCohort].put(Key(gapLength, mergedStart), 0)')
replace('freeBySizeShared.put(Key(gapLength, mergedStart), 0)','gapPolicyId[added] = freeBySizeShared.put(Key(gapLength, mergedStart), 0)')
# Cache exact integer suffix counts only when queried; recordLength invalidates.
replace('    public var recentDistinctCount: Int64 = 0\n    public var recentShortCount: Int64 = 0\n    public var lengthOccurrenceCount', '    public var recentDistinctCount: Int64 = 0\n    public var recentShortCount: Int64 = 0\n    public var lengthOccurrenceCount',2) # identity assertion
p=src.index('public class Allocator {');a,b=src[:p],src[p:]
b=b.replace('    public var recentDistinctCount: Int64 = 0','    private let missSuffix = FastIntBuffer(42)\n    private var missSuffixDirty = true\n    public var recentDistinctCount: Int64 = 0',1)
old='''                var misses: Int64 = 0
                for (request in slack + 1..=40) { misses += recentFrequency[request] }
                score += kUnfitPenaltyScale * misses'''
assert b.count(old)==1
b=b.replace(old,'''                if (missSuffixDirty) {
                    var suffix: Int64 = 0
                    var request: Int64 = 40
                    while (request >= 1) {
                        suffix += recentFrequency[request]
                        missSuffix[request] = suffix
                        request--
                    }
                    missSuffixDirty = false
                }
                score += kUnfitPenaltyScale * missSuffix[slack + 1]''')
old='''    public func recordLength(length: Int64): Unit {
        recentLengths.pushBack(length)'''
assert b.count(old)==1
b=b.replace(old,'''    public func recordLength(length: Int64): Unit {
        missSuffixDirty = true
        recentLengths.pushBack(length)''')
src=a+b
# Fixed native Fenwick with transient borrows and post-access owner fences.
replace('    public var activeFenwick = Array<Int64>(200001, repeat: 0)','    private let activeFenwick = FastIntBuffer(200001)')
marker='''    public operator func [](index: Int64): Int64 {
        if (index < 0 || index >= size) { throw IndexOutOfBoundsException("Native integer buffer index") }'''
# Insert pointer API only in this fixed-buffer class, not growable owners.
a=src.index('public class FastIntBuffer {'); b=src.index('public class FastFloatBuffer {',a)
part=src[a:b]
idx=part.index('    public operator func []')
part=part[:idx]+'    func borrowData(): CPointer<Int64> { data }\n\n'+part[idx:]
src=src[:a]+part+src[b:]
replace('''        var position = index
        while (position < activeFenwick.size) { activeFenwick[position] += delta; position += position & -position }''','''        var position = index
        if (position <= 0 || position >= activeFenwick.size) { throw IndexOutOfBoundsException("Fenwick update") }
        let data = activeFenwick.borrowData()
        unsafe {
            while (position < activeFenwick.size) {
                data.write(position, data.read(position) + delta)
                position += position & -position
            }
        }
        blackBox(this)''')
replace('''        var sum: Int64 = 0
        var position = index
        while (position > 0) { sum += activeFenwick[position]; position -= position & -position }
        return sum''','''        var sum: Int64 = 0
        var position = index
        if (position >= activeFenwick.size) { throw IndexOutOfBoundsException("Fenwick prefix") }
        let data = activeFenwick.borrowData()
        unsafe {
            while (position > 0) { sum += data.read(position); position -= position & -position }
        }
        blackBox(this)
        return sum''')
# Remove the scalar key read made redundant by metadata side arrays.
replace('            let itStart = freeByStart.keyA(it)\n','')
out=HERE/'candidate-indexed';out.mkdir(exist_ok=True);(out/'solution.cj').write_text(src)
(out/'source.json').write_text(json.dumps(dict(base_sha256=base_sha,source_sha256=hashlib.sha256(src.encode()).hexdigest(),scalar_key_reads=count,changes=['Keep same keys/order/AVL operations; store remaining three index node IDs per stable geometry node.','Scalar-only key reads remove unneeded struct materialization.','Lazy exact integer suffix counts for misses, invalidated on every recordLength.','Fixed native Fenwick with owner lifetime fence and validated indices.']),indent=2)+'\n')
print(out,'scalar_key_reads',count)
