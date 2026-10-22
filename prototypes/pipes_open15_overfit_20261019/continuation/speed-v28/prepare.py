"""Move noncanonical token parsing out of the canonical input hot path."""
from pathlib import Path
import hashlib
import json
import subprocess

HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'speed-v25'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(BASE/'solution.cpp')=='2abd02de6968851e40b442d0af595f9e297cc2185fda118c8cab38afbd4369b8'
s=(BASE/'solution.cpp').read_text()
needle='static PIPES_ALWAYS_INLINE bool consumeNonzeroToken(unsigned expectedWidth,size_t&pos,size_t&used){'
assert s.count(needle)==1
s=s.replace(needle,'''#if defined(__GNUC__) || defined(__clang__)
static __attribute__((cold,noinline))
#elif defined(_MSC_VER)
static __declspec(noinline)
#else
static
#endif
bool consumeNonzeroTokenSlow(unsigned expectedWidth,size_t&pos,size_t&used){''')
needle='bool replay(const unsigned char*meta,const unsigned char*p,unsigned count,bool alreadyRead){'
fast=r'''
static PIPES_ALWAYS_INLINE bool consumeNonzeroToken(unsigned expectedWidth,size_t&pos,size_t&used){
#if !defined(PIPES_STDIO_IO)
 if(pos==used){
  inputPos=pos;
  if(!refillInputBuffer()){pos=used=0;return false;}
  pos=inputPos;used=inputUsed;
 }
 if(used-pos>expectedWidth){
  const unsigned char*p=inputBuffer+pos;
  // Exact Open15 tokens have no leading whitespace. Preserve the complete
  // partial/whitespace/zero parser on the cold path instead of entering its
  // whitespace loop before every canonical token.
  if(p[0]>' '&&p[0]!='0'&&spaceChar(p[expectedWidth])){
   pos+=expectedWidth+1;
#if defined(PIPES_USE_WINAPI)
   if(p[expectedWidth]=='\r'&&pos<used&&inputBuffer[pos]=='\n')++pos;
#endif
   return true;
  }
 }
#endif
 return consumeNonzeroTokenSlow(expectedWidth,pos,used);
}
'''
assert s.count(needle)==1
s=s.replace(needle,fast+needle)
(HERE/'solution.cpp').write_text(s)
for f in ('verify.py','verify_support.py','winapi_test_shim.hpp'):(HERE/f).write_bytes((BASE/f).read_bytes())
flags=['-O2','-std=c++17','-Wall','-Wextra']
subprocess.run(['/usr/bin/clang++',*flags,str(HERE/'solution.cpp'),'-o',str(HERE/'solver')],check=True)
(HERE/'build.json').write_text(json.dumps({'source_sha256':sha(HERE/'solution.cpp'),'binary_sha256':sha(HERE/'solver'),'parent_sha256':sha(BASE/'solution.cpp'),'flags':flags,'scope':'Same exact Open15 tables and NT backend. Canonical token fast path precedes cold whitespace/partial framing parser.'},indent=2)+'\n')
print(sha(HERE/'solution.cpp'))
