#!/usr/bin/env python3
"""I/O-only derivatives. Never writes to the frozen candidates directory."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'candidates-fast'

IO=r'''
// Platform I/O only. Each answer is written immediately, without output buffering.
#include <cstdint>
#include <limits>
#include <stdexcept>
#include <type_traits>
#if defined(_WIN32)
#ifndef NOMINMAX
#define NOMINMAX
#endif
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <windows.h>
#else
#include <cerrno>
#include <unistd.h>
#endif
namespace fastio {
unsigned char input[65536];
std::size_t position=0,available=0;
int nextByte(){
 if(position==available){
#if defined(_WIN32)
  DWORD received=0;
  if(!ReadFile(GetStdHandle(STD_INPUT_HANDLE),input,DWORD(sizeof(input)),&received,nullptr)){
   if(GetLastError()==ERROR_BROKEN_PIPE)return -1;
   throw std::runtime_error("input read failed");
  }
  available=std::size_t(received);
#else
  ssize_t received;
  do{received=::read(STDIN_FILENO,input,sizeof(input));}while(received<0&&errno==EINTR);
  if(received<0)throw std::runtime_error("input read failed");
  available=std::size_t(received);
#endif
  position=0;
  if(!available)return -1;
 }
 return input[position++];
}
template<class Int>bool readInteger(Int& out){
 static_assert(std::is_integral<Int>::value&&std::is_signed<Int>::value,"signed integer required");
 int c;do{c=nextByte();}while(c>=0&&c<=32);
 if(c<0)return false;
 bool negative=false;
 if(c=='-'||c=='+'){negative=c=='-';c=nextByte();}
 if(c<'0'||c>'9')return false;
 const std::uint64_t maximum=std::uint64_t(std::numeric_limits<Int>::max());
 const std::uint64_t limit=maximum+(negative?1u:0u);
 std::uint64_t value=0;
 do{
  const unsigned digit=unsigned(c-'0');
  if(value>limit/10||(value==limit/10&&digit>limit%10))return false;
  value=value*10+digit;c=nextByte();
 }while(c>='0'&&c<='9');
 if(c>=0)--position; // preserve delimiter, matching formatted integer extraction
 if(negative){out=value==maximum+1u?std::numeric_limits<Int>::min():Int(-std::int64_t(value));}
 else out=Int(value);
 return true;
}
void writeAll(const char* data,std::size_t size){
 while(size){
#if defined(_WIN32)
  DWORD written=0;
  if(!WriteFile(GetStdHandle(STD_OUTPUT_HANDLE),data,DWORD(size),&written,nullptr)||!written)
   throw std::runtime_error("output write failed");
  const std::size_t count=std::size_t(written);
#else
  ssize_t written;
  do{written=::write(STDOUT_FILENO,data,size);}while(written<0&&errno==EINTR);
  if(written<=0)throw std::runtime_error("output write failed");
  const std::size_t count=std::size_t(written);
#endif
  data+=count;size-=count;
 }
}
char* integer(char* output,std::int64_t value){
 std::uint64_t magnitude=std::uint64_t(value);
 if(value<0){*output++='-';magnitude=0u-magnitude;}
 char digits[20];unsigned count=0;
 do{digits[count++]=char('0'+magnitude%10);magnitude/=10;}while(magnitude);
 while(count)*output++=digits[--count];
 return output;
}
void answer(std::int64_t x){
 char data[24];char* end=integer(data,x);*end++='\n';writeAll(data,std::size_t(end-data));
}
void answer(std::int64_t digs,std::int64_t x){
 char data[48];char* end=integer(data,digs);*end++=' ';end=integer(end,x);*end++='\n';
 writeAll(data,std::size_t(end-data));
}
} // namespace fastio
'''

COMMON=[
 ("if (emit) std::cout << pipe.start << '\\n' << std::flush;",'if (emit) fastio::answer(pipe.start);'),
 ("if (emit) std::cout << digs << ' ' << start << '\\n' << std::flush;",'if (emit) fastio::answer(digs, start);'),
 ("if (emit) std::cout << 0 << '\\n' << std::flush;",'if (emit) fastio::answer(0);'),
]
ONLINE=[
 ('    std::ios::sync_with_stdio(false);\n    std::cin.tie(nullptr);\n','    // Native descriptor input/output.\n'),
 ('while (std::cin >> command)', 'while (fastio::readInteger(command))'),
]
REPLAY=[
 ('  ios::sync_with_stdio(false);cin.tie(nullptr);\n','  // Native descriptor input/output.\n'),
 ('while(cin>>c&&c!=0)', 'while(fastio::readInteger(c)&&c!=0)'),
 ('if(emit)printf("%d %d\\n",digs,x);','if(emit)fastio::answer(digs,x);'),
 ('if(emit)printf("%d\\n",p.first);','if(emit)fastio::answer(p.first);'),
 ("cout<<(physical->T-oldT)/20<<' '<<address<<'\\n'<<flush;",'fastio::answer((physical->T-oldT)/20,address);'),
 ("cout<<x<<'\\n'<<flush;",'fastio::answer(x);'),
]

def digest(data):return hashlib.sha256(data).hexdigest()

def main():
 compiler=shutil.which('clang++')
 if not compiler:raise SystemExit('clang++ required')
 OUT.mkdir(exist_ok=True)
 records={}
 for name in ['online','full','hybrid']:
  base=ROOT/'candidates'/name
  raw=(base/'solution.cpp').read_bytes();source=raw.decode()
  manifest=json.loads((base/'build.json').read_text())
  assert digest(raw)==manifest['source_sha256'],name
  replacements=COMMON+(ONLINE if name=='online' else REPLAY)
  changed=source
  for before,after in replacements:
   assert changed.count(before)==1,(name,before)
   changed=changed.replace(before,after,1)
  # Exact reverse proof: allocation, tables, guards, imports, state and numeric
  # expressions must recover the complete frozen source byte for byte.
  restored=changed
  for before,after in reversed(replacements):
   if after:
    assert restored.count(after)==1,(name,after)
    restored=restored.replace(after,before,1)
   else:
    marker='    Allocator allocator;' if name=='online' else '  vector<Test>tests;'
    assert restored.count(marker)==1
    restored=restored.replace(marker,before+marker,1)
  assert restored==source,name
  target=OUT/name;target.mkdir(exist_ok=True)
  path=target/'solution.cpp';path.write_text(IO+'\n'+changed)
  binary=target/'solver'
  subprocess.run([compiler,'-std=c++17','-O2',str(path),'-o',str(binary)],check=True)
  row={**manifest,'source':str(path.relative_to(OUT)),'binary':str(binary.relative_to(OUT)),
       'source_sha256':digest(path.read_bytes()),'binary_sha256':digest(binary.read_bytes()),
       'frozen_source_sha256':digest(raw),'fastio_sha256':digest(IO.encode()),
       'io_only_reverse_proof':True,'compiler':compiler,'flags':['-std=c++17','-O2'],
       'replacements':[{'before':before,'after':after}for before,after in replacements]}
  (target/'build.json').write_text(json.dumps(row,indent=2)+'\n');records[name]=row
  assert (base/'solution.cpp').read_bytes()==raw,'frozen input modified'
 (OUT/'build.json').write_text(json.dumps(records,indent=2)+'\n')
 print(OUT/'build.json')

if __name__=='__main__':main()
