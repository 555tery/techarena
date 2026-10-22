#!/usr/bin/env python3
import argparse,hashlib,json,os,select,subprocess,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
def run(binary):
 p=subprocess.Popen([str(binary.resolve())],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env={**os.environ,'cjProcessorNum':'1'},bufsize=0)
 commands=[3,2,-2,2,3,7,1,-1,40,8,-4,4,-3,16,-8,1,-5,2,-9,33,5,-6]
 replies=[]
 try:
  for index,command in enumerate(commands):
   n=abs(command);sign=b'-' if command<0 else b'+'
   payload=(b' '*5007 if index==8 else b' \t')+sign+b'00'+str(n).encode()+b' \r\n'
   if index==8:chunks=[payload[:2047],payload[2047:4097],payload[4097:5010],payload[5010:]]
   else:chunks=[payload[:3],payload[3:4],payload[4:6],payload[6:]]
   for chunk in chunks:
    if chunk:p.stdin.write(chunk);p.stdin.flush();time.sleep(0.001)
   line=bytearray()
   while not line.endswith(b'\n'):
    assert select.select([p.stdout],[],[],5)[0],('no immediate reply',index)
    piece=os.read(p.stdout.fileno(),64);assert piece,('early EOF',index);line.extend(piece)
   assert len(line.split())==(2 if command>0 else 1),(index,line)
   replies.append(bytes(line))
  p.stdin.write(b'\t+0000\r\n');p.stdin.close();p.stdin=None
  assert p.wait(timeout=10)==0,p.stderr.read().decode()
  assert p.stdout.read()==b''
  return b''.join(replies),p.stderr.read().decode()
 finally:
  if p.poll() is None:p.kill();p.wait()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--candidate',type=Path,required=True);args=ap.parse_args()
 baseline=HERE.parent/'pipes_cj_tle_fix_20261020/bin/candidate-final-o0'
 a,ae=run(baseline);b,be=run(args.candidate);assert a==b
 d=dict(status='pass',commands=22,byte_identical=True,input_fragmentation='sign, digits, CRLF split across writes; one5007-byte whitespace prefix crosses4096-byte buffer.',response_protocol='One immediate LF-terminated reply per command before sending the next command; zero ends successfully.',baseline_binary_sha256=hashlib.sha256(baseline.read_bytes()).hexdigest(),candidate_binary_sha256=hashlib.sha256(args.candidate.read_bytes()).hexdigest(),response_sha256=hashlib.sha256(a).hexdigest(),baseline_finish=ae,candidate_finish=be)
 out=HERE/'audit/fragmented-io.json';out.parent.mkdir(exist_ok=True);out.write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d))
if __name__=='__main__':main()
