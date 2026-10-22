// Offline paired evaluator. References are complete causal parent outputs.
// A rollout receives commands one by one; suffix data never enters choose().
#define main frozen_main
#include "../pipes_ghost_handoff_20261020/coupled-buffer40/solution.cpp"
#undef main
#include <fstream>
struct Row {int c,x,T;bool replay;int planned;};
struct Case {string id;vector<Row>rows;vector<int>suffix;int target;};
static int digT(int T,int x,int n){return max(T,20*((x+n+19)/20));}
static int choose(Allocator&a,int n,int ref,int parentT,int policy){
 int bx=a.bf(n),x=bx;auto best=a.sizes.lower_bound({n,-1});
 if(policy==1&&best!=a.sizes.end())x=a.g.at(best->second)-n;
 if(policy==2){for(auto [l,r]:a.g)if(r-l>=n){x=l;break;}}
 if(policy==3){for(auto [l,r]:a.g)if(r-l>=n){x=r-n;break;}}
 if(policy==4&&a.fits(ref,n)&&digT(a.T,ref,n)<=digT(a.T,bx,n))x=ref;
 if(policy==5){
  // Keep right-aligned intervals ending at a20m boundary whenever doing so
  // has the same best-fit gap size and immediate trench as ordinary BF.
  if(best!=a.sizes.end()){
   int target=best->first;int answer=bx;
   for(auto it=best;it!=a.sizes.end()&&it->first==target;++it){
    int l=it->second,r=a.g.at(l),right=r-n;
    if(r%20==0){answer=right;break;}
   }x=answer;
  }
 }
 if(policy==6){
  // Reference-address tie breaker only, preserving best-fit gap-lengths.
  auto it=a.g.find(ref);
  if(best!=a.sizes.end()&&it!=a.g.end()&&it->second-it->first==best->first)x=ref;
 }
 if(policy==7){
  // Endpoint-biased placement inside an existing gap near the parent action,
  // disallowing additional current excavation compared with actual BF.
  if(best!=a.sizes.end()){
   long long score=LLONG_MAX;
   for(auto [l,r]:a.g)if(r-l>=n){
    for(int q:{l,r-n}){
     long long s=1000000LL*(r-l-n)+llabs(q-ref);
     if(s<score){score=s;x=q;}
    }
   }
  }
 }
 if(policy==8){
  // Avoid exhausting the last address-compatible parent gap when possible.
  // This uses only the current virtual address and current physical gaps.
  if(best!=a.sizes.end()){
   long long score=LLONG_MAX;
   for(auto [l,r]:a.g)if(r-l>=n){
    for(int q:{l,r-n}){
     long long s=llabs(q-ref)*1000LL+(r-l-n);
     if(s<score){score=s;x=q;}
    }
   }
  }
 }
 return x;
}

static int project(int x,int n,int second,size_t t,const vector<Row>&rows,int marker){
 bool early=second==2&&(t==2||!rows[2].replay);
 if(!early)return x;
 if(x+n<=marker)return x;
 if(x>=marker&&x+n<=229)return x+2;
 if(x>=229&&x+n<=231)return x-(229-marker);
 if(x>=231)return x;return -1;
}

static int rollout(const Case&c,int marker,int policy){

 Allocator a;a.emit=false;size_t differing=0;bool coupled=false;map<int,int>coverage;vector<int>lengths(1);auto bump=[&](int x,int d){int v=(coverage[x]+=d);if(!v)coverage.erase(x);};int second=c.rows.size()>1?c.rows[1].c:0;
 for(size_t t=0;t<c.rows.size();++t){auto row=c.rows[t];int cmd=row.c;
  if(row.replay){
   coupled=false;
   if(cmd>0){int x=(t==1&&c.rows[0].c==3&&cmd==2)?marker:row.planned;
    if(!a.fits(x,cmd))return -1;a.place(cmd,x);differing+=x!=row.x;
   }else{if(a.pipes.at(size_t(-cmd)).first!=row.x)--differing;a.remove(-cmd);}
  }else{
   if(!differing&&a.T<=row.T)coupled=true;
   if(cmd>0){int x=coupled?row.x:([&](){if(policy>=9&&coverage.empty()&&a.T<=row.T)return row.x;if(policy>=10){int q=project(row.x,cmd,second,t,c.rows,marker);if(q>=0&&a.fits(q,cmd)&&digT(a.T,q,cmd)<=row.T&&(policy<13||digT(a.T,q,cmd)<=digT(a.T,a.bf(cmd),cmd)))return q;if(policy==11&&a.fits(row.x,cmd)&&digT(a.T,row.x,cmd)<=row.T)return row.x;if(policy==12||policy==14)return choose(a,cmd,row.x,row.T,4);return a.bf(cmd);}return choose(a,cmd,row.x,row.T,policy==9?0:policy);}());
    if(!a.fits(x,cmd))return -2;a.place(cmd,x);differing+=x!=row.x;
   }else{if(a.pipes.at(size_t(-cmd)).first!=row.x)--differing;a.remove(-cmd);}
   if(coupled&&(differing||a.T>row.T))return -3;
   if(!coupled&&!differing&&a.T<=row.T)coupled=true;
  }
  if(cmd>0){lengths.push_back(cmd);int x=a.pipes.back().first;bump(x,1);bump(x+cmd,-1);bump(row.x,-1);bump(row.x+cmd,1);}else{int x=a.pipes[-cmd].first,L=lengths[-cmd];bump(x,-1);bump(x+L,1);bump(row.x,1);bump(row.x+L,-1);}
  if(coupled)return max(a.T,c.suffix[t+1]);
 }return a.T;
}
int main(int argc,char**argv){
 if(argc!=3)return 2;
 ifstream in(argv[1]);int count;in>>count;vector<Case>cases(count);
 for(auto&c:cases){int n;in>>c.id>>n>>c.target;c.rows.resize(n);for(auto&r:c.rows)in>>r.c>>r.x>>r.T>>r.replay>>r.planned;
  c.suffix.assign(n+1,0);for(int i=n-1;i>=0;--i)c.suffix[i]=max(c.suffix[i+1],c.rows[i].c>0?20*((c.rows[i].x+c.rows[i].c+19)/20):0);
 }
 if(!in)return 3;ofstream out(argv[2]);out<<"marker,policy,case,T,parentT\n";
 for(int marker=3;marker<=229;++marker)for(int policy=13;policy<=14;++policy){
  for(const auto&c:cases)out<<marker<<','<<policy<<','<<c.id<<','<<rollout(c,marker,policy)<<','<<c.target<<'\n';
 }
}
