// Complete causal rollouts on observed inputs; reference rows never expose a future decision to choose().
#define main original_main
#include "../pipes_g5420_cpu_20261020/cache32/solution.cpp"
#undef main
#include "theory/local_transport.hpp"
#include <fstream>
struct Row {int c,x,T,replay,planned,bid;};
struct Case {string id;vector<Row> rows;vector<int> suffix;int target;};
static int projectedT(int T,int x,int n){return max(T,20*((x+n+19)/20));}
static bool changed(int bid,int profile){
 static const set<int> instant{5321,5343,5407,5418,5443,5468,5293,5291};
 static const set<int> exchange{5499,7242,8517,8518};
 return profile==0?true:profile==1?instant.count(bid):profile==2?!instant.count(bid):exchange.count(bid);
}
static int rollout(const Case& c,int profile,int policy){
 Allocator a,ref;a.emit=false;ref.emit=false;int differing=0;
 for(size_t s=0;s<c.rows.size();++s){
  auto r=c.rows[s];int cmd=r.c;
  if(cmd>0){
   int x=r.x;
   if(r.replay){
    if(profile<4){if(r.planned>=0&&changed(r.bid,profile))x=r.planned;}
    else{const map<int,int>tail{{5321,633},{5343,792},{5443,868},{5293,557}};auto it=tail.find(r.bid);if(it!=tail.end()&&(profile==4||r.bid==5321))x=it->second;}
   }
   else if(differing){
    int bx=a.bf(cmd);x=bx;
    if(policy>=2){auto proposal=local_transport::choose(a,ref.pipes,r.x,r.T,cmd);if(proposal.certificate)x=proposal.x;}
    if((policy==1||policy==3||policy==4)&&x==bx&&a.fits(r.x,cmd)&&projectedT(a.T,r.x,cmd)<=(policy==4?r.T:projectedT(a.T,bx,cmd)))x=r.x;
   }
   if(!a.fits(x,cmd))return -1;
   a.place(cmd,x);ref.place(cmd,r.x);differing+=x!=r.x;
  }else{
   differing-=a.pipes.at(-cmd).first!=r.x;a.remove(-cmd);ref.remove(-cmd);
  }
  if(!r.replay&&!differing&&a.T<=r.T)return max(a.T,c.suffix[s+1]);
 }
 return a.T;
}
int main(int argc,char**argv){
 if(argc!=3)return 2;ifstream in(argv[1]);int count;in>>count;vector<Case> cases(count);
 for(auto&c:cases){int n;in>>c.id>>n>>c.target;c.rows.resize(n);for(auto&r:c.rows)in>>r.c>>r.x>>r.T>>r.replay>>r.planned>>r.bid;
  c.suffix.assign(n+1,0);for(int i=n-1;i>=0;--i)c.suffix[i]=max(c.suffix[i+1],c.rows[i].c>0?20*((c.rows[i].x+c.rows[i].c+19)/20):0);
 }
 if(!in)return 3;ofstream out(argv[2]);out<<"profile,policy,case,T,parentT\n";
 for(int profile=0;profile<6;++profile)for(int policy=0;policy<5;++policy)for(const auto&c:cases)
  out<<profile<<','<<policy<<','<<c.id<<','<<rollout(c,profile,policy)<<','<<c.target<<'\n';
}
