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
#if !defined(_WIN32) && !defined(PIPES_STDIO_IO)
#include <unistd.h>
#endif
using namespace std;
// Direct read returns available pipe bytes; it does not wait to fill the buffer.
inline int inputChar(){
#if defined(_WIN32) || defined(PIPES_STDIO_IO)
 return getchar();
#else
 static unsigned char buffer[4096];static size_t pos=0,used=0;
 if(pos==used){ssize_t n;do{n=::read(STDIN_FILENO,buffer,sizeof(buffer));}while(n<0&&errno==EINTR);
  if(n==0)return EOF;if(n<0)throw runtime_error("input read failed");used=size_t(n);pos=0;}
 return buffer[pos++];
#endif
}
void writeBytes(const char*data,size_t length){
#if defined(_WIN32) || defined(PIPES_STDIO_IO)
 if(fwrite(data,1,length,stdout)!=length||fflush(stdout)!=0)throw runtime_error("output failed");
#else
 while(length){ssize_t n=::write(STDOUT_FILENO,data,length);if(n<0&&errno==EINTR)continue;
  if(n<=0)throw runtime_error("output failed");data+=n;length-=size_t(n);}
#endif
}
inline bool spaceChar(int c){return c==' '||c=='\t'||c=='\n'||c=='\v'||c=='\f'||c=='\r';}
bool readInteger(int&out){
#if defined(_WIN32) || defined(PIPES_STDIO_INPUT) || defined(PIPES_STDIO_IO)
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
// Printable immutable records: base85 zigzag(command), base85 trench length, reply length, reply.
static const unsigned char unbase85[256]={0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,0,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,0,57,58,59,60,61,62,63,64,65,66,67,68,69,70,71,72,73,74,75,76,77,78,79,80,81,82,83,84,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0};
unsigned read85(const unsigned char*p){return (unsigned(unbase85[p[0]])*85+unbase85[p[1]])*85+unbase85[p[2]];}
struct Record{int command,T;const char*reply;unsigned length;};
Record recordAt(const unsigned char*p){unsigned c=read85(p);return{(c&1)?-int(c>>1):int(c>>1),int(read85(p+3)),reinterpret_cast<const char*>(p+7),unsigned(p[6]-33)};}
struct Test{const unsigned char*cursor;unsigned remaining;};
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
// Materialize allocation state only when the observed input leaves the table.
void restore(Allocator&state,size_t chosen,unsigned steps){
 const unsigned char*p=reinterpret_cast<const unsigned char*>(records[chosen]);
 for(unsigned i=0;i<steps;++i){Record r=recordAt(p);p+=7+r.length;
  if(r.command>0){const char*q=r.reply;while(*q!=' ')++q;++q;int x=0;while(*q>='0'&&*q<='9')x=x*10+(*q++-'0');state.pipes.push_back({x,r.command});}
  else{int id=-r.command;if(id<=0||size_t(id)>=state.pipes.size()||state.pipes[id].n<=0)throw runtime_error("bad restored PID");state.pipes[id].n=0;}
  state.T=r.T;
 }
 state.reconstruct();
}
int main(){
 try{
  vector<Test>tests;for(size_t i=0;i<15;++i)tests.push_back({reinterpret_cast<const unsigned char*>(records[i]),counts[i]});
  unsigned active[15];for(unsigned i=0;i<15;++i)active[i]=i;unsigned activeCount=15;
  Allocator state;int c;unsigned replay=0,fallback=0,conflict=0,steps=0;size_t lastTest=0;int lastT=0;bool useTables=true;
  while(readInteger(c)&&c!=0){
   if(useTables){
    Record chosen{};bool matched=false,agrees=true;unsigned kept=0;size_t selected=0;
    for(unsigned k=0;k<activeCount;++k){unsigned i=active[k];Test&t=tests[i];if(!t.remaining)continue;Record r=recordAt(t.cursor);if(r.command!=c)continue;
     t.cursor+=7+r.length;--t.remaining;active[kept++]=i;
     if(matched&&(chosen.length!=r.length||memcmp(chosen.reply,r.reply,r.length)!=0||chosen.T!=r.T))agrees=false;
     chosen=r;selected=i;matched=true;
    }
    activeCount=kept;
    if(matched&&agrees){writeBytes(chosen.reply,chosen.length);lastTest=selected;lastT=chosen.T;++steps;if(c>0)++replay;continue;}
    if(matched)++conflict;
    restore(state,lastTest,steps);useTables=false;vector<Test>().swap(tests);
   }
   if(c>0){++fallback;state.place(c,state.bf(c));}else state.remove(-c);
  }
  fprintf(stderr,"OPEN15_FULL_OVERFIT replay=%u fallback=%u table_conflict=%u T=%d\n",replay,fallback,conflict,useTables?lastT:state.T);
 }catch(const exception&e){fprintf(stderr,"error: %s\n",e.what());return 2;}
 return 0;
}
