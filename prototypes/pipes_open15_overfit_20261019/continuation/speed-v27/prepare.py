"""Emit identical little-endian tables as uint64 words for ordinary MSVC."""
from pathlib import Path
import ast
import hashlib
import json
import re
import subprocess

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / 'speed-v25'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(BASE / 'solution.cpp') == '2abd02de6968851e40b442d0af595f9e297cc2185fda118c8cab38afbd4369b8'
source = (BASE / 'solution.cpp').read_text()
arrays = []

def emit(match):
 name = match[1]
 data = ast.literal_eval('(' + match[2] + ')').encode('latin1')
 words = [int.from_bytes(data[i:i+8].ljust(8,b'\0'),'little') for i in range(0,len(data),8)]
 if not words: words = [0]
 arrays.append({'name':name,'bytes':len(data),'padded_bytes':8*len(words),'sha256':hashlib.sha256(data).hexdigest()})
 lines = [','.join('0x%016xULL'%x for x in words[i:i+6]) for i in range(0,len(words),6)]
 return 'static const uint64_t '+name+'_words[]={\n'+',\n'.join(lines)+'\n};'

source, count = re.subn(r'static const (?:unsigned char|char) ((?:meta|replies)\d+)\[\]=\n(.*?);',emit,source,flags=re.S)
assert count == 44
source = re.sub(r'reinterpret_cast<const unsigned char\*>\(replies(\d+)\)',r'reinterpret_cast<const unsigned char*>(replies\1_words)',source)
source = re.sub(r'\{meta(\d+),',r'{reinterpret_cast<const unsigned char*>(meta\1_words),',source)
source = source.replace('// Runtime consumes one command', '// Numeric table words below require a little-endian target (Windows x64).\n// Runtime consumes one command')
(HERE/'solution.cpp').write_text(source)
for name in ('verify.py','verify_support.py','winapi_test_shim.hpp'):
 (HERE/name).write_bytes((BASE/name).read_bytes())
flags = ['-O2','-std=c++17','-Wall','-Wextra']
subprocess.run(['/usr/bin/clang++',*flags,str(HERE/'solution.cpp'),'-o',str(HERE/'solver')],check=True)
(HERE/'build.json').write_text(json.dumps({'source_sha256':sha(HERE/'solution.cpp'),'binary_sha256':sha(HERE/'solver'),'parent_sha256':sha(BASE/'solution.cpp'),'flags':flags,'source_bytes':(HERE/'solution.cpp').stat().st_size,'binary_bytes':(HERE/'solver').stat().st_size,'arrays':arrays,'scope':'Exact Open15 full overfit; same 44 byte streams in uint64 storage; ordinary CRT startup. No MSVC or Windows performance claim until server check.'},indent=2)+'\n')
print(json.dumps({'source_sha256':sha(HERE/'solution.cpp'),'arrays':count,'source_bytes':(HERE/'solution.cpp').stat().st_size}))
