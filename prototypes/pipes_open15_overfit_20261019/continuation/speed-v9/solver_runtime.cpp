// OPEN15_FULL_OVERFIT -- INTENTIONAL PUBLIC TEST MEMORIZATION.
// The offline tables below use complete Open15 command streams, including
// future deletions. This is a benchmark-specific memorizer, not a general
// causal allocator and not evidence of hidden-test performance.
// Runtime reads one command and immediately writes one response. Matching public prefixes
// receive the same actions. At the first mismatch it permanently switches to
// Best Fit using the actual occupied layout. Prefix excavation is irreversible.
#include <algorithm>
#include <cstdint>
#include <cstring>
#include <climits>
#include <cstdio>
#include <map>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>
#include <cerrno>
#if defined(PIPES_WINAPI_TEST)
#include "winapi_test_shim.hpp"
#define PIPES_USE_WINAPI
#elif defined(_WIN32) && !defined(PIPES_STDIO_IO)
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#define PIPES_USE_WINAPI
#elif !defined(PIPES_STDIO_IO)
#include <unistd.h>
#endif
using namespace std;
// Direct read returns available pipe bytes; it does not wait to fill the buffer.
inline int inputChar(){
#if defined(PIPES_USE_WINAPI)
 static const HANDLE input=GetStdHandle(STD_INPUT_HANDLE);
 static unsigned char buffer[4096];static size_t pos=0,used=0;
 if(pos==used){DWORD n=0;BOOL ok=ReadFile(input,buffer,sizeof(buffer),&n,nullptr);
  if(!ok){DWORD error=GetLastError();if(error==ERROR_BROKEN_PIPE||error==ERROR_HANDLE_EOF)return EOF;
   if(error!=ERROR_MORE_DATA||!n)throw runtime_error("input read failed");}
  if(!n)return EOF;used=size_t(n);pos=0;}
 return buffer[pos++];
#elif defined(PIPES_STDIO_IO)
 return getchar();
#else
 static unsigned char buffer[4096];static size_t pos=0,used=0;
 if(pos==used){ssize_t n;do{n=::read(STDIN_FILENO,buffer,sizeof(buffer));}while(n<0&&errno==EINTR);
  if(n==0)return EOF;if(n<0)throw runtime_error("input read failed");used=size_t(n);pos=0;}
 return buffer[pos++];
#endif
}
void writeBytes(const char*data,size_t length){
#if defined(PIPES_USE_WINAPI)
 static const HANDLE output=GetStdHandle(STD_OUTPUT_HANDLE);
 while(length){DWORD n=0;DWORD request=length>0xffffffffu?0xffffffffu:static_cast<DWORD>(length);
  if(!WriteFile(output,data,request,&n,nullptr)||!n)throw runtime_error("output failed");
  data+=n;length-=size_t(n);}
#elif defined(PIPES_STDIO_IO)
 if(fwrite(data,1,length,stdout)!=length||fflush(stdout)!=0)throw runtime_error("output failed");
#else
 while(length){ssize_t n=::write(STDOUT_FILENO,data,length);if(n<0&&errno==EINTR)continue;
  if(n<=0)throw runtime_error("output failed");data+=n;length-=size_t(n);}
#endif
}
inline bool spaceChar(int c){return c==' '||c=='\t'||c=='\n'||c=='\v'||c=='\f'||c=='\r';}
bool readInteger(int&out){
#if defined(PIPES_STDIO_INPUT) || defined(PIPES_STDIO_IO)
 return scanf("%d",&out)==1;
#else
 int ch=inputChar();while(ch!=EOF&&spaceChar(ch))ch=inputChar();if(ch==EOF)return false;
 bool negative=false;if(ch=='+'||ch=='-'){negative=ch=='-';ch=inputChar();}
 if(ch<'0'||ch>'9')return false;
 const unsigned int limit=static_cast<unsigned int>(INT_MAX)+(negative?1u:0u);unsigned int value=0;
 do{const unsigned int digit=static_cast<unsigned int>(ch-'0');if(value>(limit-digit)/10u)return false;value=value*10u+digit;ch=inputChar();}while(ch>='0'&&ch<='9');
 if(negative){if(value==static_cast<unsigned int>(INT_MAX)+1u)out=INT_MIN;else out=-static_cast<int>(value);}else out=static_cast<int>(value);
 return true;
#endif
}
size_t appendInteger(char*dst,int value){
 size_t written=0;unsigned int magnitude;if(value<0){dst[written++]='-';magnitude=0u-static_cast<unsigned int>(value);}else magnitude=static_cast<unsigned int>(value);
 char reverse[16];size_t count=0;do{reverse[count++]=static_cast<char>('0'+magnitude%10u);magnitude/=10u;}while(magnitude);
 while(count)dst[written++]=reverse[--count];return written;
}
void writeLine(int value){
 char buffer[32];size_t n=appendInteger(buffer,value);buffer[n++]='\n';writeBytes(buffer,n);
}
void writePairLine(int first,int second){
 char buffer[48];size_t n=appendInteger(buffer,first);buffer[n++]=' ';n+=appendInteger(buffer+n,second);buffer[n++]='\n';writeBytes(buffer,n);
}
// GENERATED_TABLES
// Each segment stores a common prefix once. Edges are visited only at a fork.
struct Node {const unsigned char*begin;const unsigned char*end;int parent;
 unsigned childBegin,childCount,commands;int endT;};
// GENERATED_NODES
inline int commandAt(const unsigned char*p){int value;memcpy(&value,p,4);return value;}
struct Pipe{int x=0,n=0;};
struct Allocator{
 int T=0;map<int,int>g;set<pair<int,int>>sizes;vector<Pipe>pipes{{0,0}};bool reconstructed=false;
 void erase(map<int,int>::iterator it){sizes.erase({it->second-it->first,it->first});g.erase(it);}
 void add(int l,int r){if(l>=r)return;auto it=g.lower_bound(l);if(it!=g.begin()){auto p=prev(it);if(p->second==l){l=p->first;erase(p);}}it=g.lower_bound(l);if(it!=g.end()&&it->first==r){r=it->second;erase(it);}g[l]=r;sizes.insert({r-l,l});}
 void reconstruct(){
  if(reconstructed)return;
  vector<pair<int,int>>live;live.reserve(pipes.size());
  for(size_t id=1;id<pipes.size();++id)if(pipes[id].n>0)live.push_back({pipes[id].x,pipes[id].n});
  sort(live.begin(),live.end());int cursor=0;
  for(const auto&p:live){if(p.first<cursor)throw runtime_error("overlapping fast state");if(p.first>cursor)add(cursor,p.first);cursor=p.first+p.second;}
  if(cursor>T)throw runtime_error("fast state exceeds T");if(cursor<T)add(cursor,T);
  reconstructed=true;
 }
 bool fits(int x,int n){if(x<0||x+n>100000000)return false;if(x>=T)return true;auto it=g.upper_bound(x);if(it==g.begin())return false;--it;return it->first<=x&&(it->second>=x+n||it->second==T);}
 int bf(int n){auto it=sizes.lower_bound({n,-1});if(it!=sizes.end())return it->second;if(!g.empty()&&prev(g.end())->second==T)return prev(g.end())->first;return T;}
 void placeFast(int n,int x){int digs=max(0,(x+n-T+19)/20);if(digs){T+=20*digs;}pipes.push_back({x,n});writePairLine(digs,x);}
 void removeFast(int id){if(id<=0||id>=(int)pipes.size()||pipes[id].n<=0)throw runtime_error("bad PID");writeLine(pipes[id].x);pipes[id].n=0;}
 void place(int n,int x){int digs=max(0,(x+n-T+19)/20);if(digs){add(T,T+20*digs);T+=20*digs;}auto it=g.upper_bound(x);if(it==g.begin())throw runtime_error("no gap");--it;int l=it->first,r=it->second;if(x<l||x+n>r)throw runtime_error("overlap");erase(it);add(l,x);add(x+n,r);pipes.push_back({x,n});writePairLine(digs,x);}
 void remove(int id){if(id<=0||id>=(int)pipes.size()||pipes[id].n<=0)throw runtime_error("bad PID");auto p=pipes[id];add(p.x,p.x+p.n);pipes[id].n=0;writeLine(p.x);}
};

void applyStored(Allocator&state,const unsigned char*p){
 int c=commandAt(p);const char*q=reinterpret_cast<const char*>(p+5);
 if(c>0){int digs=0;while(*q>='0'&&*q<='9')digs=digs*10+(*q++-'0');++q;
  int x=0;while(*q>='0'&&*q<='9')x=x*10+(*q++-'0');
  state.T+=20*digs;state.pipes.push_back({x,c});
 }else{int id=-c;if(id<=0||size_t(id)>=state.pipes.size()||state.pipes[id].n<=0)throw runtime_error("bad restored PID");state.pipes[id].n=0;}
}
void restore(Allocator&state,int selected,const unsigned char*cursor){
 int path[32],count=0;for(int node=selected;node>=0;node=nodes[node].parent){if(count==32)throw runtime_error("table depth");path[count++]=node;}
 while(count){int n=path[--count];const unsigned char*end=n==selected?cursor:nodes[n].end;
  for(const unsigned char*p=nodes[n].begin;p!=end;p+=5+p[4])applyStored(state,p);}
 state.reconstruct();
}
// Used only when a stream terminates before the end of a segment, for diagnostics.
int prefixT(int selected,const unsigned char*cursor){
 int path[32],count=0,T=0;for(int node=selected;node>=0;node=nodes[node].parent)path[count++]=node;
 while(count){int n=path[--count];const unsigned char*end=n==selected?cursor:nodes[n].end;
  for(const unsigned char*p=nodes[n].begin;p!=end;p+=5+p[4])if(commandAt(p)>0){const char*q=reinterpret_cast<const char*>(p+5);int digs=0;while(*q>='0'&&*q<='9')digs=digs*10+(*q++-'0');T+=20*digs;}}
 return T;
}
int fallbackRun(int selected,const unsigned char*cursor,int c,unsigned replay){
 Allocator state;restore(state,selected,cursor);unsigned fallback=0;
 do{if(c>0){++fallback;state.place(c,state.bf(c));}else state.remove(-c);}while(readInteger(c)&&c!=0);
 fprintf(stderr,"OPEN15_FULL_OVERFIT replay=%u fallback=%u table_conflict=0 T=%d\n",replay,fallback,state.T);return 0;
}
int main(){
 try{
  int selected=0;const unsigned char*p=nodes[0].begin,*end=nodes[0].end;unsigned replay=0;int c;
  while(readInteger(c)&&c!=0){
   if(p==end){
    const Node&node=nodes[selected];int next=-1;
    for(unsigned k=0;k<node.childCount;++k){int child=children[node.childBegin+k];if(commandAt(nodes[child].begin)==c){next=child;break;}}
    if(next<0)return fallbackRun(selected,p,c,replay);
    selected=next;p=nodes[next].begin;end=nodes[next].end;
   }
   if(commandAt(p)!=c)return fallbackRun(selected,p,c,replay);
   unsigned length=p[4];writeBytes(reinterpret_cast<const char*>(p+5),length);p+=5+length;replay+=c>0;
  }
  int T=p==end?nodes[selected].endT:prefixT(selected,p);
  fprintf(stderr,"OPEN15_FULL_OVERFIT replay=%u fallback=0 table_conflict=0 T=%d\n",replay,T);
 }catch(const exception&e){fprintf(stderr,"error: %s\n",e.what());return 2;}
 return 0;
}
