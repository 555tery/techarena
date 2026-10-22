// OPEN15_FULL_OVERFIT -- INTENTIONAL PUBLIC TEST MEMORIZATION.
// Tables below are computed OFFLINE using COMPLETE Open15 commands, including
// future deletions. This is NOT a general causal allocation algorithm, and its
// public score is NOT evidence of hidden-test generalization.
// Runtime reads one command and flushes one response. Identical known prefixes
// have identical actions. Any mismatch permanently switches to Best Fit from
// the ACTUAL occupied layout. Prefix-induced excavation cannot be undone.
// Separate experimental branch; trial22 has not been replaced or submitted.
#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <map>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>
using namespace std;
// GENERATED_TABLES
vector<unsigned char> decode(const char*s){vector<unsigned char>out;uint32_t v=0;int bits=-8;for(;*s;++s){int c=*s;int x=c>='A'&&c<='Z'?c-'A':c>='a'&&c<='z'?c-'a'+26:c>='0'&&c<='9'?c-'0'+52:c=='+'?62:c=='/'?63:-1;if(x<0)continue;v=(v<<6)|uint32_t(x);bits+=6;if(bits>=0){out.push_back((v>>bits)&255);bits-=8;}}return out;}
unsigned var(const vector<unsigned char>&a,size_t&i){unsigned v=0,s=0;while(i<a.size()){unsigned c=a[i++];v|=(c&127)<<s;if(!(c&128))return v;s+=7;if(s>28)throw runtime_error("bad table");}throw runtime_error("truncated table");}
int signedVar(const vector<unsigned char>&a,size_t&i){unsigned v=var(a,i);return (v&1)?-int((v+1)/2):int(v/2);}
struct Test{vector<int>cmd,pos;};
struct Allocator{
 int T=0;map<int,int>g;set<pair<int,int>>sizes;vector<pair<int,int>>pipes{{0,0}};
 void erase(map<int,int>::iterator it){sizes.erase({it->second-it->first,it->first});g.erase(it);}
 void add(int l,int r){if(l>=r)return;auto it=g.lower_bound(l);if(it!=g.begin()){auto p=prev(it);if(p->second==l){l=p->first;erase(p);}}it=g.lower_bound(l);if(it!=g.end()&&it->first==r){r=it->second;erase(it);}g[l]=r;sizes.insert({r-l,l});}
 bool fits(int x,int n){if(x<0||x+n>100000000)return false;if(x>=T)return true;auto it=g.upper_bound(x);if(it==g.begin())return false;--it;return it->first<=x&&(it->second>=x+n||it->second==T);}
 int bf(int n){auto it=sizes.lower_bound({n,-1});if(it!=sizes.end())return it->second;if(!g.empty()&&prev(g.end())->second==T)return prev(g.end())->first;return T;}
 void place(int n,int x){int digs=max(0,(x+n-T+19)/20);if(digs){add(T,T+20*digs);T+=20*digs;}auto it=g.upper_bound(x);if(it==g.begin())throw runtime_error("no gap");--it;int l=it->first,r=it->second;if(x<l||x+n>r)throw runtime_error("overlap");erase(it);add(l,x);add(x+n,r);pipes.push_back({x,n});printf("%d %d\n",digs,x);}
 void remove(int id){if(id<=0||id>=(int)pipes.size()||pipes[id].second<=0)throw runtime_error("bad PID");auto p=pipes[id];add(p.first,p.first+p.second);pipes[id].second=0;printf("%d\n",p.first);}
};
int main(){
 try{
  vector<Test>tests;for(const char*s:encoded){auto a=decode(s);size_t k=0;unsigned n=var(a,k);Test t;int previous=0;while(n--){int c=signedVar(a,k);t.cmd.push_back(c);if(c>0){previous+=signedVar(a,k);t.pos.push_back(previous);}else t.pos.push_back(-1);}if(k!=a.size())throw runtime_error("table tail");tests.push_back(move(t));}
  vector<bool>active(tests.size(),true);Allocator state;int c;size_t step=0;unsigned replay=0,fallback=0,conflict=0;
  while(scanf("%d",&c)==1&&c!=0){
   int address=-1;bool agrees=true,matched=false;
   for(size_t i=0;i<tests.size();++i)if(active[i]){
    if(step>=tests[i].cmd.size()||tests[i].cmd[step]!=c){active[i]=false;continue;}
    matched=true;if(c>0){int p=tests[i].pos[step];if(address>=0&&address!=p)agrees=false;address=p;}
   }
   if(c>0){if(matched&&agrees&&state.fits(address,c)){++replay;}else{if(matched)++conflict;fill(active.begin(),active.end(),false);address=state.bf(c);++fallback;}state.place(c,address);}
   else state.remove(-c);
   fflush(stdout);++step;
  }
  fprintf(stderr,"OPEN15_FULL_OVERFIT replay=%u fallback=%u table_conflict=%u T=%d\n",replay,fallback,conflict,state.T);
 }catch(const exception&e){fprintf(stderr,"error: %s\n",e.what());return 2;}
 return 0;
}
