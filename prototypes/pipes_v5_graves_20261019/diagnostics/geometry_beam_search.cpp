#include <algorithm>
#include <chrono>
#include <cstdint>
#include <iostream>
#include <numeric>
#include <tuple>
#include <unordered_set>
#include <vector>
using namespace std;
struct Gap { int l, r; };
struct Pipe { int id, len, good, bad; };
struct PathNode { int parent, op; };
struct State {
    vector<Pipe> p;
    vector<Gap> gg, bg;
    int nextPid = 5, badT = 40, used = 0, path = -1, volume = 20;
    uint64_t hash = 0;
    int potential = 0, divergence = 0, maxGood = 0, maxBad = 0;
};
static inline uint64_t mix64(uint64_t x) {
    x += 0x9e3779b97f4a7c15ULL;
    x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
    x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
    return x ^ (x >> 31);
}
vector<Gap> makeGaps(const vector<Pipe>& p, bool good, int T) {
    vector<pair<int,int>> v;
    v.reserve(p.size());
    for (auto x : p) v.push_back({good ? x.good : x.bad, x.len});
    sort(v.begin(), v.end());
    vector<Gap> g;
    int e = 0;
    for (auto [s,l] : v) { if (s > e) g.push_back({e,s}); e = max(e,s+l); }
    if (e < T) g.push_back({e,T});
    return g;
}
void addGap(vector<Gap>& g, int l, int r) {
    if (l >= r) return;
    auto it = lower_bound(g.begin(),g.end(),l,[](const Gap& a,int x){return a.l<x;});
    if (it != g.begin() && prev(it)->r == l) { l = prev(it)->l; it = g.erase(prev(it)); }
    it = lower_bound(g.begin(),g.end(),l,[](const Gap& a,int x){return a.l<x;});
    if (it != g.end() && it->l == r) { r = it->r; it = g.erase(it); }
    g.insert(it,{l,r});
}
int bestGap(const vector<Gap>& g, int L) {
    int idx=-1, sz=1<<30;
    for (int i=0;i<(int)g.size();i++) { int d=g[i].r-g[i].l; if (d>=L && (d<sz || (d==sz && (idx<0 || g[i].l<g[idx].l)))) {idx=i;sz=d;} }
    return idx;
}
int consume(vector<Gap>& g,int idx,int L,int trench,int& newT) {
    if (idx>=0) { int pos=g[idx].l,r=g[idx].r;g.erase(g.begin()+idx);addGap(g,pos+L,r);newT=trench;return pos; }
    int pos=trench,tail=-1;
    for(int i=0;i<(int)g.size();i++) if(g[i].r==trench) tail=i;
    if(tail>=0)pos=g[tail].l;
    int tailLen=trench-pos,deficit=max(0,L-tailLen);
    newT=trench+((deficit+19)/20)*20;
    if(tail>=0)g.erase(g.begin()+tail);
    addGap(g,pos+L,newT);
    return pos;
}
void metrics(State& s) {
    s.maxGood=s.maxBad=0;
    for(auto g:s.gg)s.maxGood=max(s.maxGood,g.r-g.l);
    for(auto g:s.bg)s.maxBad=max(s.maxBad,g.r-g.l);
    s.potential=0;
    int lo=min(40,s.maxBad+1),hi=min(40,s.maxGood);
    for(int L=lo;L<=hi;L++)s.potential+=L;
    s.divergence=0;
    uint64_t sum=0,xr=0;
    for(auto p:s.p){
        s.divergence+=min(100000,abs(p.good-p.bad));
        uint64_t z=mix64((uint64_t)p.id*1000000007ULL+(uint64_t)p.len*1000003ULL+(uint64_t)(p.good+1)*9176ULL+(uint64_t)(p.bad+1)*65537ULL);
        sum+=z;xr^=z;
    }
    s.hash=mix64(sum)^mix64(xr)^mix64((uint64_t)s.badT*17ULL+(uint64_t)s.p.size());
}
bool better(const State&a,const State&b){
    if(a.badT!=b.badT)return a.badT>b.badT;
    if(a.potential!=b.potential)return a.potential>b.potential;
    if(a.divergence!=b.divergence)return a.divergence>b.divergence;
    if(a.p.size()!=b.p.size())return a.p.size()>b.p.size();
    if(a.used!=b.used)return a.used<b.used;
    return a.hash>b.hash;
}
vector<int> deletionChoices(const State&s){
    vector<int> out;out.reserve(s.p.size());
    for(int i=0;i<(int)s.p.size();i++)out.push_back(i);
    return out;
}
int main(int argc,char**argv){
    int beamWidth=argc>1?atoi(argv[1]):128;
    int maxDepth=argc>2?atoi(argv[2]):500;
    int seconds=argc>3?atoi(argv[3]):60;
    State init;
    init.p={{3,15,5,1},{5,5,0,16}};
    init.nextPid=5;init.badT=40;init.volume=20;
    init.gg=makeGaps(init.p,true,20);
    init.bg=makeGaps(init.p,false,40);
    metrics(init);
    vector<PathNode> nodes;
    auto addPath=[&](int parent,int op){nodes.push_back({parent,op});return (int)nodes.size()-1;};
    vector<State> beam={init};
    State globalBest=init;
    auto start=chrono::steady_clock::now();
    for(int depth=0;depth<maxDepth;depth++){
        if(chrono::duration<double>(chrono::steady_clock::now()-start).count()>seconds)break;
        vector<State> cand;cand.reserve(beamWidth*64);
        for(const State&s:beam){
            cand.push_back(s);
            for(int ix:deletionChoices(s)){
                State c=s;Pipe p=c.p[ix];c.p.erase(c.p.begin()+ix);
                addGap(c.gg,p.good,p.good+p.len);addGap(c.bg,p.bad,p.bad+p.len);
                c.volume-=p.len;c.used++;c.path=addPath(s.path,-p.id);metrics(c);cand.push_back(move(c));
            }
            for(int L=1;L<=40;L++){
                int ig=bestGap(s.gg,L);if(ig<0)continue;
                int ib=bestGap(s.bg,L),ng=20,nb=s.badT;
                State c=s;
                int pg=consume(c.gg,ig,L,20,ng);
                int pb=consume(c.bg,ib,L,s.badT,nb);
                if(ng!=20)continue;
                c.p.push_back({++c.nextPid,L,pg,pb});c.volume+=L;c.badT=nb;c.used++;
                c.path=addPath(s.path,L);metrics(c);cand.push_back(move(c));
            }
        }
        sort(cand.begin(),cand.end(),better);
        vector<State> next;next.reserve(beamWidth);
        unordered_set<uint64_t> seen;seen.reserve(beamWidth*4);
        unordered_set<uint64_t> buckets;buckets.reserve(beamWidth*2);
        vector<State> deferred;deferred.reserve(cand.size());
        auto bucket=[&](const State&s){return mix64((uint64_t)(s.badT/20)*0x9e3779b9ULL+(uint64_t)(s.potential/10)*0x85ebca6bULL+(uint64_t)(s.p.size()/3)*0xc2b2ae35ULL+(s.hash>>24));};
        for(auto&c:cand){
            if(!seen.insert(c.hash).second)continue;
            uint64_t b=bucket(c);
            if(buckets.insert(b).second&&next.size()<(size_t)beamWidth)next.push_back(move(c));
            else deferred.push_back(move(c));
            if(next.size()>=(size_t)beamWidth)break;
        }
        if(next.size()<(size_t)beamWidth){for(auto&c:deferred){if(next.size()>=(size_t)beamWidth)break;next.push_back(move(c));}}
        if(next.empty())break;
        beam=move(next);
        for(const auto&s:beam)if(better(s,globalBest))globalBest=s;
        if(depth%25==0)cerr<<"depth="<<depth<<" beam="<<beam.size()<<" bestT="<<globalBest.badT<<" topT="<<beam[0].badT<<" nodes="<<nodes.size()<<" elapsed="<<chrono::duration<double>(chrono::steady_clock::now()-start).count()<<"\n";
    }
    vector<int> ops;for(int p=globalBest.path;p>=0;p=nodes[p].parent)ops.push_back(nodes[p].op);reverse(ops.begin(),ops.end());
    int fill=max(0,20-globalBest.volume);
    cout<<"best_target_T="<<globalBest.badT<<" final_target_KPI="<<20.0/globalBest.badT<<" BF_T=20 BF_KPI=1 prefix_ops=8 beam_ops="<<ops.size()<<" fill_ones="<<fill<<" beam="<<beamWidth<<" depth_limit="<<maxDepth<<" elapsed="<<chrono::duration<double>(chrono::steady_clock::now()-start).count()<<"\n";
    cout<<"suffix=[";for(size_t i=0;i<ops.size();i++){if(i)cout<<",";cout<<ops[i];}for(int i=0;i<fill;i++){if(!ops.empty()||i)cout<<",";cout<<1;}cout<<"]\n";
    cout<<"active_geometry (pid len BFpos replayPos):\n";for(auto p:globalBest.p)cout<<p.id<<" "<<p.len<<" "<<p.good<<" "<<p.bad<<"\n";
}
