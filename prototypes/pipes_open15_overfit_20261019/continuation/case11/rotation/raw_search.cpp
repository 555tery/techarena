#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <map>
#include <numeric>
#include <random>
#include <set>
#include <string>
#include <vector>
using namespace std;
struct Gaps {
    static constexpr int INF = 100000000;
    map<int,int> g;
    set<pair<int,int>> bySize;
    Gaps() { add(0, INF); }
    void eraseIt(map<int,int>::iterator it) { bySize.erase({it->second-it->first,it->first}); g.erase(it); }
    void add(int l,int r) {
        if(l>=r) return;
        auto it=g.lower_bound(l);
        if(it!=g.begin()) { auto p=prev(it); if(p->second==l) { l=p->first; eraseIt(p); } }
        it=g.lower_bound(l);
        if(it!=g.end() && it->first==r) { r=it->second; eraseIt(it); }
        g[l]=r; bySize.insert({r-l,l});
    }
    bool take(int x,int len) {
        auto it=g.upper_bound(x);
        if(it==g.begin()) return false;
        --it; int l=it->first,r=it->second;
        if(x<l || x+len>r) return false;
        eraseIt(it); add(l,x); add(x+len,r); return true;
    }
    int bestGap(int len,int policy,mt19937_64& rng) {
        auto it=bySize.lower_bound({len, -1});
        if(it==bySize.end()) return -1;
        if(policy==0) return it->second; // best fit, lowest address tie
        if(policy==1) { // best-fit size, highest address among equal sizes
            int sz=it->first, ans=it->second;
            for(;it!=bySize.end() && it->first==sz;++it) ans=it->second;
            return ans;
        }
        if(policy==2) { // first fit by address
            for(auto gi=g.begin();gi!=g.end();++gi) if(gi->second-gi->first>=len) return gi->first;
            return -1;
        }
        if(policy==3) { // largest adequate finite gap; use tail only as fallback
            for(auto ri=bySize.rbegin();ri!=bySize.rend();++ri) {
                if(ri->first>=len && ri->first<Gaps::INF/2) return ri->second;
            }
            return it->second;
        }
        if(policy==4) { // random among the first 12 adequate gaps by size
            vector<int> xs;
            for(;it!=bySize.end() && xs.size()<12;++it) {
                if(it->first>=Gaps::INF/2 && !xs.empty()) continue;
                xs.push_back(it->second);
            }
            if(xs.empty()) return -1;
            return xs[uniform_int_distribution<size_t>(0,xs.size()-1)(rng)];
        }
        if(policy==5) { // best fit, highest finite gap; tail if no finite fits
            for(;it!=bySize.end();++it) if(it->first<Gaps::INF/2) return it->second;
            return bySize.lower_bound({len,-1})->second;
        }
        if(policy==6) { // random per allocation: best-fit, first-fit, or best among 12
            int q=(int)(rng()%3);
            return bestGap(len, q==0?0:(q==1?2:4), rng);
        }
        return it->second;
    }
};
struct Instance {
    int n=0; vector<int> cmd, size, death, pidAt, survivors;
    explicit Instance(const string& path) {
        ifstream in(path); double w; if(!(in>>w>>n)) throw runtime_error("bad input");
        cmd.resize(n); for(int t=0;t<n;++t) in>>cmd[t];
        size.push_back(0); death.push_back(n); pidAt.assign(n,0);
        for(int t=0;t<n;++t) {
            int c=cmd[t];
            if(c>0) { int id=(int)size.size(); size.push_back(c); death.push_back(n); pidAt[t]=id; }
            else death[-c]=t;
        }
        for(int i=1;i<(int)size.size();++i) if(death[i]==n) survivors.push_back(i);
    }
};
struct Result { int h=Gaps::INF; vector<int> pos; bool ok=false; };
Result pack(const Instance& in,const vector<int>& order,const vector<int>& extra,int policy,mt19937_64& rng) {
    Result out; out.pos.assign(in.size.size(),-1); Gaps gaps;
    int p=0;
    for(int k=0;k<(int)order.size();++k) {
        int id=order[k]; out.pos[id]=p;
        if(!gaps.take(p,in.size[id])) return out;
        p+=in.size[id];
        if(k<(int)extra.size() && extra[k]) p+=extra[k];
    }
    out.h=p;
    for(int t=in.n-1;t>=0;--t) {
        int c=in.cmd[t];
        if(c>0) gaps.add(out.pos[in.pidAt[t]],out.pos[in.pidAt[t]]+in.size[in.pidAt[t]]);
        else {
            int id=-c, l=gaps.bestGap(in.size[id],policy,rng);
            if(l<0) return out;
            auto it=gaps.g.upper_bound(l); if(it==gaps.g.begin()) return out; --it;
            int x=l;
            if(policy==5 && it->second<Gaps::INF/2) x=it->second-in.size[id];
            if(policy==6 && (rng()&1) && it->second<Gaps::INF/2) x=it->second-in.size[id];
            if(!gaps.take(x,in.size[id])) return out;
            out.pos[id]=x; out.h=max(out.h,x+in.size[id]);
        }
    }
    out.ok=true; return out;
}
void save(const Result& r,const string& path) {
    string tmp=path+".tmp"; ofstream out(tmp); for(size_t i=1;i<r.pos.size();++i) out<<r.pos[i]<<'\n'; out.close();
    std::rename(tmp.c_str(),path.c_str());
}
int main(int argc,char**argv) {
    if(argc<2) return 2;
    Instance in(argv[1]);
    mt19937_64 rng(20261019);
    vector<int> base=in.survivors;
    vector<int> bestOrder=base,bestExtra(base.size(),0);
    Result best; int evaluations=0;
    auto t0=chrono::steady_clock::now();
    string outPath=argc>=3?argv[2]:"positions.txt";
    {
        ifstream previous(outPath);
        if(previous) {
            vector<int> p(1,0); int x; while(previous>>x) p.push_back(x);
            if(p.size()==in.size.size()) {
                best.pos=std::move(p); best.h=0; best.ok=true;
                for(size_t i=1;i<best.pos.size();++i) best.h=max(best.h,best.pos[i]+in.size[i]);
                cerr<<"loaded previous H="<<best.h<<"\n";
            }
        }
    }
    auto eval=[&](const vector<int>& order,const vector<int>& extra,int pol) {
        Result r=pack(in,order,extra,pol,rng); ++evaluations;
        if(r.ok && r.h<best.h) { best=r; bestOrder=order; bestExtra=extra; save(best,outPath); cerr<<"best H="<<best.h<<" T="<<20*((best.h+19)/20)<<" eval="<<evaluations<<" policy="<<pol<<"\n"; }
        return r.h;
    };
    // Structured orderings and five placement policies.
    for(int pol=0;pol<=6;++pol) {
        vector<int> o=base, ex(o.size(),0);
        if(pol==1) reverse(o.begin(),o.end());
        else if(pol==2) stable_sort(o.begin(),o.end(),[&](int a,int b){return in.size[a]>in.size[b];});
        else if(pol==3) stable_sort(o.begin(),o.end(),[&](int a,int b){return in.size[a]<in.size[b];});
        eval(o,ex,pol);
    }
    // Random starts, including up to 28 bytes of deliberate permanent gaps.
    for(int q=0;q<10000;++q) {
        vector<int> o=base, ex(o.size(),0); shuffle(o.begin(),o.end(),rng);
        int total=(q%3==0)?0:(int)(rng()%29);
        while(total>0) { int j=(int)(rng()%ex.size()); int chunk=min(total,1+(int)(rng()%min(10,total))); ex[j]+=chunk; total-=chunk; }
        eval(o,ex,q%7);
        if(best.h<=20760) break;
    }
    // Anneal survivor order and attached spacer positions from the strongest starts.
    for(int chain=0;chain<250 && best.h>20760;++chain) {
        vector<int> o=base, ex(o.size(),0); shuffle(o.begin(),o.end(),rng);
        if(chain%4==0) stable_sort(o.begin(),o.end(),[&](int a,int b){return in.size[a]>in.size[b];});
        if(chain%4==1) stable_sort(o.begin(),o.end(),[&](int a,int b){return in.size[a]<in.size[b];});
        if(chain%4==2) reverse(o.begin(),o.end());
        if(chain%5==0) {
            int total=1+(int)(rng()%28);
            while(total>0) { int j=(int)(rng()%ex.size()); int chunk=min(total,1+(int)(rng()%min(10,total))); ex[j]+=chunk; total-=chunk; }
        }
        int pol=chain%7; int cur=eval(o,ex,pol);
        for(int it=0;it<1000 && best.h>20760;++it) {
            vector<int> no=o, ne=ex;
            int a=(int)(rng()%no.size()), b=(int)(rng()%no.size());
            int op=(int)(rng()%3);
            if(op==0) { swap(no[a],no[b]); swap(ne[a],ne[b]); }
            else if(op==1) { int id=no[a], sp=ne[a]; no.erase(no.begin()+a); ne.erase(ne.begin()+a); if(a<b)--b; no.insert(no.begin()+b,id); ne.insert(ne.begin()+b,sp); }
            else { if(a>b) swap(a,b); reverse(no.begin()+a,no.begin()+b+1); reverse(ne.begin()+a,ne.begin()+b+1); }
            int nv=eval(no,ne,pol);
            double temp=2.5*(1.0-(double)it/1000.0)+0.08;
            if(nv<=cur || (nv<Gaps::INF && generate_canonical<double,32>(rng)<exp((double)(cur-nv)/temp))) { o.swap(no); ex.swap(ne); cur=nv; }
        }
        if(best.h<=20760) break;
        if(chain%4==3) { auto sec=chrono::duration_cast<chrono::seconds>(chrono::steady_clock::now()-t0).count(); cerr<<"progress eval="<<evaluations<<" best="<<best.h<<" elapsed_s="<<sec<<"\n"; }
    }
    cout<<"best_h "<<best.h<<" T "<<20*((best.h+19)/20)<<" evaluations "<<evaluations<<"\n";
    return best.ok?0:1;
}
