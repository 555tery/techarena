#include <algorithm>
#include <chrono>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <numeric>
#include <tuple>
#include <unordered_set>
#include <vector>
using namespace std;
struct Gap{int l,r;};
struct Pipe{int id,len,g,b;};
struct PathNode{int parent,op;};
struct State{
 vector<Pipe> p; vector<Gap> gg,bg;
 int nextPid=0,badT=120,used=0,path=-1,volume=0,firstOp=0;
 uint64_t hash=0; int potential=0,divergence=0,maxGood=0,maxBad=0;
};
struct Candidate{State s;};
static inline uint64_t mix64(uint64_t x){x+=0x9e3779b97f4a7c15ULL;x=(x^(x>>30))*0xbf58476d1ce4e5b9ULL;x=(x^(x>>27))*0x94d049bb133111ebULL;return x^(x>>31);}
vector<Gap> makeGaps(const vector<Pipe>& p,bool good,int T){
 vector<pair<int,int>> v;v.reserve(p.size());for(auto x:p)v.push_back({good?x.g:x.b,x.len});sort(v.begin(),v.end());vector<Gap> g;int e=0;for(auto [s,l]:v){if(s>e)g.push_back({e,s});e=max(e,s+l);}if(e<T)g.push_back({e,T});return g;
}
void addGap(vector<Gap>&g,int l,int r){if(l>=r)return;auto it=lower_bound(g.begin(),g.end(),l,[](const Gap&a,int x){return a.l<x;});if(it!=g.begin()&&prev(it)->r==l){l=prev(it)->l;it=g.erase(prev(it));}it=lower_bound(g.begin(),g.end(),l,[](const Gap&a,int x){return a.l<x;});if(it!=g.end()&&it->l==r){r=it->r;it=g.erase(it);}it=g.insert(it,{l,r});
}
int bestGap(const vector<Gap>&g,int L){int idx=-1,sz=1<<30;for(int i=0;i<(int)g.size();i++){int d=g[i].r-g[i].l;if(d>=L&&(d<sz||(d==sz&&(idx<0||g[i].l<g[idx].l)))){idx=i;sz=d;}}return idx;}
int consume(vector<Gap>&g,int idx,int L,int trench,int&newT){
 if(idx>=0){int pos=g[idx].l,r=g[idx].r;g.erase(g.begin()+idx);addGap(g,pos+L,r);newT=trench;return pos;}
 // Match allocator_probe exactly: if no gap fits, reuse the start of the
 // terminal free gap and extend only by the 20m-rounded deficit.
 int pos=trench,tail=-1;for(int i=0;i<(int)g.size();i++)if(g[i].r==trench)tail=i;
 if(tail>=0)pos=g[tail].l;
 int tailLen=trench-pos,deficit=max(0,L-tailLen);
 newT=trench+((deficit+19)/20)*20;
 if(tail>=0)g.erase(g.begin()+tail);
 addGap(g,pos+L,newT);return pos;
}
void metrics(State&s){
 s.maxGood=s.maxBad=0;for(auto g:s.gg)s.maxGood=max(s.maxGood,g.r-g.l);for(auto g:s.bg)s.maxBad=max(s.maxBad,g.r-g.l);
 s.potential=0;int lo=min(40,s.maxBad+1),hi=min(40,s.maxGood);for(int L=lo;L<=hi;L++)s.potential+=L;
 s.divergence=0;for(auto p:s.p)s.divergence+=min(100000,abs(p.g-p.b));
 uint64_t sum=0,xr=0;for(auto p:s.p){uint64_t z=mix64((uint64_t)p.len*1000003ULL+(uint64_t)(p.g+1)*9176ULL+(uint64_t)(p.b+1)*65537ULL);sum+=z;xr^=z;}
 s.hash=mix64(sum)^mix64(xr)^mix64((uint64_t)s.badT*17ULL+(uint64_t)s.p.size());
}
bool better(const State&a,const State&b){if(a.badT!=b.badT)return a.badT>b.badT;if(a.potential!=b.potential)return a.potential>b.potential;if(a.divergence!=b.divergence)return a.divergence>b.divergence;if(a.p.size()!=b.p.size())return a.p.size()>b.p.size();if(a.used!=b.used)return a.used<b.used;return a.hash>b.hash;}
vector<int> deletionChoices(const State&s){
 int n=s.p.size();vector<int> out;if(n<=32){for(int i=0;i<n;i++)out.push_back(i);return out;}
 vector<int> used(n,0);auto put=[&](int i){if(i>=0&&i<n&&!used[i]&&(int)out.size()<32){used[i]=1;out.push_back(i);}};
 vector<int> v(n);iota(v.begin(),v.end(),0);
 sort(v.begin(),v.end(),[&](int a,int b){return abs(s.p[a].g-s.p[a].b)>abs(s.p[b].g-s.p[b].b);});for(int j=0;j<12;j++)put(v[j]);
 sort(v.begin(),v.end(),[&](int a,int b){return s.p[a].g<s.p[b].g;});for(int j=0;j<8;j++)put(v[j*(n-1)/7]);
 sort(v.begin(),v.end(),[&](int a,int b){return s.p[a].b<s.p[b].b;});for(int j=0;j<8;j++)put(v[j*(n-1)/7]);
 sort(v.begin(),v.end(),[&](int a,int b){return s.p[a].len>s.p[b].len;});for(int j=0;j<4;j++)put(v[j]);
 return out;
}
int main(int argc,char**argv){
 if(argc<2){cerr<<"usage states.txt [beam=64] [depth=250] [seconds=75]\n";return 2;}
 int beamWidth=argc>2?atoi(argv[2]):64,maxDepth=argc>3?atoi(argv[3]):250,seconds=argc>4?atoi(argv[4]):75;
 ifstream f(argv[1]);int ns;f>>ns;State init;bool got=false;
 for(int z=0;z<ns;z++){int id,cas,pref,gt,bt,m;f>>id>>cas>>pref>>gt>>bt>>m;vector<Pipe> v(m);for(auto&q:v)f>>q.id>>q.len>>q.g>>q.b;if(id==98){init.p=v;init.nextPid=29;init.badT=bt;init.volume=0;for(auto p:v)init.volume+=p.len;init.gg=makeGaps(init.p,true,gt);init.bg=makeGaps(init.p,false,bt);metrics(init);got=true;}}
 if(!got){cerr<<"state 98 not found\n";return 3;}
 // State 98 is Open15's 32-command prefix; op 33 in the public stream is +6.
 const int expectedNext=6;
 vector<PathNode> nodes;auto addPath=[&](int parent,int op){nodes.push_back({parent,op});return (int)nodes.size()-1;};
 State seed=init;vector<int> keep={11,12,13,14,22};vector<int> dels;for(auto p:seed.p)if(find(keep.begin(),keep.end(),p.id)==keep.end())dels.push_back(p.id);
 for(int pid:dels){auto it=find_if(seed.p.begin(),seed.p.end(),[&](Pipe p){return p.id==pid;});if(it==seed.p.end())continue;Pipe p=*it;seed.p.erase(it);addGap(seed.gg,p.g,p.g+p.len);addGap(seed.bg,p.b,p.b+p.len);seed.volume-=p.len;seed.used++;seed.path=addPath(seed.path,-pid);if(seed.firstOp==0)seed.firstOp=-pid;metrics(seed);}
 for(int j=0;j<3;j++){int ig=bestGap(seed.gg,28),ib=bestGap(seed.bg,28),ng=120,nb=seed.badT;int pg=consume(seed.gg,ig,28,120,ng),pb=consume(seed.bg,ib,28,seed.badT,nb);Pipe p{++seed.nextPid,28,pg,pb};seed.p.push_back(p);seed.volume+=28;seed.badT=nb;seed.used++;seed.path=addPath(seed.path,28);metrics(seed);}
 vector<State> beam={init,seed};metrics(beam[0]);metrics(beam[1]);
 State globalBest=seed;int globalBad=globalBest.badT;auto start=chrono::steady_clock::now();
 for(int depth=0;depth<maxDepth;depth++){
  if(chrono::duration<double>(chrono::steady_clock::now()-start).count()>seconds)break;
  vector<State> cand;cand.reserve(beamWidth*80);for(auto&s:beam)cand.push_back(s);
  for(const State&s:beam){if(s.used>=maxDepth)continue;
   auto ds=deletionChoices(s);
   for(int ix:ds){int op=-s.p[ix].id;if(s.used==0&&op==expectedNext)continue;State c=s;Pipe p=c.p[ix];c.p.erase(c.p.begin()+ix);addGap(c.gg,p.g,p.g+p.len);addGap(c.bg,p.b,p.b+p.len);c.volume-=p.len;c.used++;if(c.used==1)c.firstOp=op;c.path=addPath(s.path,op);metrics(c);cand.push_back(std::move(c));}
   for(int L=1;L<=40;L++){int ig=bestGap(s.gg,L);if(ig<0)continue;int op=L;if(s.used==0&&op==expectedNext)continue;int ib=bestGap(s.bg,L),ng=120,nb=s.badT;State c=s;int pg=consume(c.gg,ig,L,120,ng);int pb=consume(c.bg,ib,L,s.badT,nb);c.p.push_back({++c.nextPid,L,pg,pb});c.volume+=L;c.badT=nb;c.used++;if(c.used==1)c.firstOp=op;c.path=addPath(s.path,op);metrics(c);cand.push_back(std::move(c));}
  }
  sort(cand.begin(),cand.end(),better);
  vector<State> next;next.reserve(beamWidth);unordered_set<uint64_t> seen;seen.reserve(beamWidth*3);
  // First preserve one representative per coarse geometry bucket; then fill by rank.
  unordered_set<uint64_t> buckets;buckets.reserve(beamWidth*2);vector<State> deferred;deferred.reserve(cand.size());
  auto bucket=[&](const State&s){return mix64((uint64_t)(s.badT/20)*0x9e3779b9ULL+(uint64_t)(s.potential/20)*0x85ebca6bULL+(uint64_t)(s.p.size()/5)*0xc2b2ae35ULL+(s.hash>>24));};
  for(auto&c:cand){if(!seen.insert(c.hash).second)continue;uint64_t b=bucket(c);if(buckets.insert(b).second&&next.size()<(size_t)beamWidth)next.push_back(std::move(c));else deferred.push_back(std::move(c));if(next.size()>=(size_t)beamWidth)break;}
  if(next.size()<(size_t)beamWidth){for(auto&c:deferred){if(next.size()>=(size_t)beamWidth)break;next.push_back(std::move(c));}}
  if(next.empty())break;beam=std::move(next);
  for(const auto&s:beam)if(s.badT>globalBad||(s.badT==globalBad&&better(s,globalBest))){globalBest=s;globalBad=s.badT;}
  if(depth%25==0)cerr<<"depth="<<depth<<" beam="<<beam.size()<<" bestT="<<globalBad<<" currentTop="<<beam[0].badT<<" nodes="<<nodes.size()<<" elapsed="<<chrono::duration<double>(chrono::steady_clock::now()-start).count()<<"\n";
 }
 vector<int> ops;for(int p=globalBest.path;p>=0;p=nodes[p].parent)ops.push_back(nodes[p].op);reverse(ops.begin(),ops.end());
 cout<<"best_badT="<<globalBest.badT<<" final_KPI="<<120.0/globalBest.badT<<" prefix_ops=32 suffix_ops="<<ops.size()<<" live_before_fill="<<globalBest.volume<<" fill_ones="<<(120-globalBest.volume)<<" beam="<<beamWidth<<" depth_limit="<<maxDepth<<" elapsed="<<chrono::duration<double>(chrono::steady_clock::now()-start).count()<<"\n";
 cout<<"suffix=[";for(size_t i=0;i<ops.size();i++){if(i)cout<<",";cout<<ops[i];}for(int i=0;i<120-globalBest.volume;i++){if(!ops.empty()||i)cout<<",";cout<<1;}cout<<"]\n";
 cout<<"active_geometry (pid len BFpos replayPos):\n";for(auto p:globalBest.p)cout<<p.id<<" "<<p.len<<" "<<p.g<<" "<<p.b<<"\n";
}
