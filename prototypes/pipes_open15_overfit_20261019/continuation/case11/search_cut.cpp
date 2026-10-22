// Offline-only Open15 case 11 planner using all future deletions.
#include <algorithm>
#include <fstream>
#include <iostream>
#include <map>
#include <numeric>
#include <random>
#include <set>
#include <vector>
using namespace std;

struct Gaps {
  map<int,int> g;
  set<pair<int,int>> sz;
  explicit Gaps(int cap) { add(0,cap); }
  void erase(map<int,int>::iterator it) { sz.erase({it->second-it->first,it->first}); g.erase(it); }
  void add(int l,int r) {
    if(l>=r) return;
    auto it=g.lower_bound(l);
    if(it!=g.begin()) { auto p=prev(it); if(p->second==l) { l=p->first; erase(p); } }
    it=g.lower_bound(l);
    if(it!=g.end() && it->first==r) { r=it->second; erase(it); }
    g[l]=r; sz.insert({r-l,l});
  }
  bool take(int x,int len) {
    auto it=g.upper_bound(x); if(it==g.begin()) return false; --it;
    int l=it->first,r=it->second; if(x<l || x+len>r) return false;
    erase(it); add(l,x); add(x+len,r); return true;
  }
  bool allocate(int len,int mode,mt19937& rng,int& x) {
    auto it=sz.lower_bound({len,-1}); if(it==sz.end()) return false;
    if(mode==0) {
      for(auto q=g.begin();q!=g.end();++q) if(q->second-q->first>=len) { it=sz.find({q->second-q->first,q->first}); break; }
    } else if(mode==2) {
      it=prev(sz.end()); if(it->first<len) return false;
    } else if(mode==3) {
      vector<set<pair<int,int>>::const_iterator> a;
      for(auto q=it;q!=sz.end();++q) a.push_back(q);
      uniform_int_distribution<size_t> pick(0,a.size()-1); it=a[pick(rng)];
    } else if(mode==4) {
      vector<set<pair<int,int>>::const_iterator> a;
      for(auto q=it;q!=sz.end() && a.size()<4;++q) a.push_back(q);
      uniform_int_distribution<size_t> pick(0,a.size()-1); it=a[pick(rng)];
    }
    int l=it->second,r=l+it->first;
    // Left packing keeps the high-water mark small; some restarts use other offsets.
    int offset=mode%3;
    if(offset==0) x=l;
    else if(offset==1) x=r-len;
    else { uniform_int_distribution<int> pick(l,r-len); x=pick(rng); }
    return take(x,len);
  }
};

int main(int argc,char**argv) {
  if(argc!=5) { cerr<<"usage: search_cut input output target iterations\n"; return 2; }
  ifstream in(argv[1]); int width,n; if(!(in>>width>>n)) return 3;
  vector<int> cmd(n),len(1),birth(1,-1),death(1,n),idAt(n);
  for(int t=0;t<n;++t) {
    in>>cmd[t];
    if(cmd[t]>0) { int id=len.size(); idAt[t]=id; len.push_back(cmd[t]); birth.push_back(t); death.push_back(n); }
    else if(cmd[t]<0) { idAt[t]=-cmd[t]; death[-cmd[t]]=t; }
  }
  int target=stoi(argv[3]),iterations=stoi(argv[4]);
  long long live=0,peak=-1; int cut=-1;
  for(int t=0;t<n;++t) { if(cmd[t]>0) live+=cmd[t]; else if(cmd[t]<0) live-=len[-cmd[t]]; if(live>peak) { peak=live; cut=t; } }
  vector<int> critical;
  for(int id=1;id<(int)len.size();++id) if(birth[id]<=cut && death[id]>cut) critical.push_back(id);
  if(peak>target) { cerr<<"LB_EXCEEDS_TARGET peak="<<peak<<" target="<<target<<"\n"; return 4; }
  ofstream out(argv[2]); if(!out) return 5;
  mt19937 rng(20261019);
  long long backFails=0,forwardFails=0,initFails=0;
  int bestBackFail=n,bestForwardFail=-1;
  long long backOkByOrder[14]={},forwardFailByOrder[14]={},fullByOrder[14]={};
  int bestForwardByOrder[14]; fill(bestForwardByOrder,bestForwardByOrder+14,-1);
  for(int it=0;it<iterations;++it) {
    vector<int> order=critical;
    int orderPolicy=it%14;
    if(orderPolicy==0) stable_sort(order.begin(),order.end(),[&](int a,int b){return birth[a]<birth[b];});
    if(orderPolicy==1) stable_sort(order.begin(),order.end(),[&](int a,int b){return birth[a]>birth[b];});
    if(orderPolicy==2) stable_sort(order.begin(),order.end(),[&](int a,int b){return death[a]<death[b];});
    if(orderPolicy==3) stable_sort(order.begin(),order.end(),[&](int a,int b){return death[a]>death[b];});
    if(orderPolicy==4) stable_sort(order.begin(),order.end(),[&](int a,int b){return death[a]-birth[a]<death[b]-birth[b];});
    if(orderPolicy==5) stable_sort(order.begin(),order.end(),[&](int a,int b){return death[a]-birth[a]>death[b]-birth[b];});
    if(orderPolicy==6) stable_sort(order.begin(),order.end(),[&](int a,int b){return len[a]>len[b];});
    if(orderPolicy==7) stable_sort(order.begin(),order.end(),[&](int a,int b){return len[a]<len[b];});
    if(orderPolicy==8) stable_sort(order.begin(),order.end(),[&](int a,int b){return 1LL*len[a]*(death[a]-birth[a])>1LL*len[b]*(death[b]-birth[b]);});
    if(orderPolicy==9) stable_sort(order.begin(),order.end(),[&](int a,int b){return 1LL*len[a]*(death[a]-birth[a])<1LL*len[b]*(death[b]-birth[b]);});
    if(orderPolicy>=10) shuffle(order.begin(),order.end(),rng);
    vector<int> pos(len.size(),-1);
    Gaps init(target); bool ok=true;
    // Fix PID 1 at coordinate zero as requested for shared prefixes.
    if(death[1]>cut && birth[1]<=cut) { pos[1]=0; if(!init.take(0,len[1])) ok=false; }
    int p=len[1];
    for(int id:order) if(ok && id!=1) { pos[id]=p; if(!init.take(p,len[id])) ok=false; p+=len[id]; }
    if(!ok) { ++initFails; continue; }
    Gaps back=init, forward=init;
    int backPolicy=(it/14)%5, forwardPolicy=(it/70)%5;
    int failAt=-1;
    // Undo through the critical command; cut state is defined just after it.
    for(int t=cut;t>=0 && ok;--t) {
      int c=cmd[t];
      if(c>0) { int id=idAt[t]; if(pos[id]<0) { ok=false; failAt=t; } else back.add(pos[id],pos[id]+len[id]); }
      else if(c<0) { int id=-c; if(pos[id]>=0 || !back.allocate(len[id],backPolicy,rng,pos[id])) { ok=false; failAt=t; } }
    }
    if(!ok) { ++backFails; bestBackFail=min(bestBackFail,failAt); continue; }
    ++backOkByOrder[orderPolicy];
    for(int t=cut+1;t<n && ok;++t) {
      int c=cmd[t];
      if(c>0) { int id=idAt[t]; if(pos[id]>=0 || !forward.allocate(len[id],forwardPolicy,rng,pos[id])) { ok=false; failAt=t; } }
      else if(c<0) { int id=-c; if(pos[id]<0) { ok=false; failAt=t; } else forward.add(pos[id],pos[id]+len[id]); }
    }
    if(!ok) { ++forwardFails; bestForwardFail=max(bestForwardFail,failAt); ++forwardFailByOrder[orderPolicy]; bestForwardByOrder[orderPolicy]=max(bestForwardByOrder[orderPolicy],failAt); continue; }
    int extent=0;
    for(int id=1;id<(int)len.size();++id) extent=max(extent,pos[id]+len[id]);
    if(extent<=target) {
      for(int id=1;id<(int)len.size();++id) out<<pos[id]<<'\n';
      cerr<<"FOUND iteration="<<it<<" peak="<<peak<<" cut="<<cut<<" extent="<<extent
          <<" order="<<orderPolicy<<" back="<<backPolicy<<" forward="<<forwardPolicy<<" seed=20261019\n";
      return 0;
    }
    ++fullByOrder[orderPolicy];
  }
  cerr<<"NO_PLAN iterations="<<iterations<<" peak="<<peak<<" cut="<<cut
      <<" initFails="<<initFails<<" backFails="<<backFails<<" bestBackFail="<<bestBackFail
      <<" forwardFails="<<forwardFails<<" bestForwardFail="<<bestForwardFail<<"\n";
  for(int i=0;i<14;++i) cerr<<"order="<<i<<" backOk="<<backOkByOrder[i]<<" forwardFail="<<forwardFailByOrder[i]
                              <<" bestForwardFail="<<bestForwardByOrder[i]<<" full="<<fullByOrder[i]<<"\n";
  return 1;
}
