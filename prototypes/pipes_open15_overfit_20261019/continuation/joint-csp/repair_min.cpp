// OPEN15_FULL_OVERFIT: offline exact-domain repair, all future lifetimes known.
#include <algorithm>
#include <chrono>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <numeric>
#include <random>
#include <vector>
using namespace std;
struct Undo{int v,w;uint64_t old;};
int H,W,M; vector<int>L,B,D,P,ids,cnt,assigned;vector<vector<int>>adj;vector<vector<uint64_t>>dom;vector<Undo>trail;mt19937 rng;long long nodes=0;double seconds;chrono::steady_clock::time_point start;bool timed=false;int failures=0;
int pop(uint64_t x){return __builtin_popcountll(x);} 
bool removeRange(int v,int lo,int hi){lo=max(0,lo);hi=min(H-L[ids[v]],hi);if(lo>hi)return cnt[v]>0;int a=lo/64,z=hi/64;for(int w=a;w<=z;++w){uint64_t mask=~0ULL;if(w==a)mask&=(~0ULL<<(lo%64));if(w==z&&hi%64!=63)mask&=((1ULL<<(hi%64+1))-1);uint64_t old=dom[v][w],now=old&~mask;if(old!=now){trail.push_back({v,w,old});cnt[v]-=pop(old)-pop(now);dom[v][w]=now;}}return cnt[v]>0;}
void restore(size_t mark){while(trail.size()>mark){auto u=trail.back();trail.pop_back();cnt[u.v]+=pop(u.old)-pop(dom[u.v][u.w]);dom[u.v][u.w]=u.old;}}
bool dfs(int left){if(!left)return true;if((++nodes&1023)==0&&chrono::duration<double>(chrono::steady_clock::now()-start).count()>seconds){timed=true;return false;}int v=-1;for(int i=0;i<M;++i)if(assigned[i]<0&&(v<0||cnt[i]<cnt[v]||(cnt[i]==cnt[v]&&L[ids[i]]>L[ids[v]])))v=i;if(cnt[v]==0)return false;vector<int>xs;for(int w=0;w<W;++w){auto bits=dom[v][w];while(bits){int b=__builtin_ctzll(bits);xs.push_back(64*w+b);bits&=bits-1;}}
 // Randomized value order can escape an unfavorable early commitment; exact domain is retained.
 if(rng()%2)reverse(xs.begin(),xs.end());if(xs.size()>2&&rng()%3==0)rotate(xs.begin(),xs.begin()+rng()%xs.size(),xs.end());
 for(int x:xs){size_t mark=trail.size();assigned[v]=x;bool good=true;for(int q:adj[v])if(assigned[q]<0&&!removeRange(q,x-L[ids[q]]+1,x+L[ids[v]]-1)){if(failures++<3){cerr<<"DEAD placed "<<ids[v]<<" at "<<x<<" conflict "<<ids[q]<<" depth "<<M-left<<" path";for(int k=0;k<M;++k)if(assigned[k]>=0)cerr<<" "<<ids[k]<<":"<<assigned[k];cerr<<endl;}good=false;break;}if(good&&dfs(left-1))return true;assigned[v]=-1;restore(mark);if(timed)return false;}return false;}
bool minconf(){
 vector<int>x(M),conf(M),diff(H+2),cost(H+1),weight(M,1);long long best=1e18;int stale=0;
 auto overlap=[&](int i,int j){return x[i]<x[j]+L[ids[j]]&&x[j]<x[i]+L[ids[i]];};
 for(int i=0;i<M;++i){int rank=rng()%cnt[i];for(int w=0;w<W;++w){int c=pop(dom[i][w]);if(rank>=c){rank-=c;continue;}auto z=dom[i][w];while(rank--)z&=z-1;x[i]=w*64+__builtin_ctzll(z);break;}}
 for(long long step=0;;++step){
  if((step&255)==0&&chrono::duration<double>(chrono::steady_clock::now()-start).count()>seconds){cout<<"MIN_END best="<<best<<" steps="<<step<<endl;return false;}
  fill(conf.begin(),conf.end(),0);int total=0;vector<int>bad;
  for(int i=0;i<M;++i){for(int j:adj[i])if(j>i&&overlap(i,j)){conf[i]++;conf[j]++;total++;}if(conf[i])bad.push_back(i);}
  if(total<best){best=total;stale=0;cout<<"MIN_BEST "<<best<<" step="<<step<<endl;}else ++stale;
  if(!total){assigned=x;return true;}
  int v=bad[rng()%bad.size()];if(rng()%4){for(int k=0;k<3;++k){int q=bad[rng()%bad.size()];if(conf[q]>conf[v])v=q;}}
  fill(diff.begin(),diff.end(),0);
  for(int q:adj[v]){int l=max(0,x[q]-L[ids[v]]+1),r=min(H-L[ids[v]],x[q]+L[ids[q]]-1);if(l<=r){diff[l]+=weight[q];diff[r+1]-=weight[q];}}
  int sum=0,score=1000000000,chosen=-1,ties=0;bool randomstep=(rng()%100<3);
  for(int at=0;at<=H-L[ids[v]];++at){sum+=diff[at];if(!(dom[v][at/64]>>(at%64)&1)||at==x[v])continue;int val=randomstep?0:sum;
   if(val<score){score=val;chosen=at;ties=1;}else if(val==score&&rng()%++ties==0)chosen=at;}
  if(chosen>=0)x[v]=chosen;
  if(stale>500){for(int q:bad)weight[q]+=1;stale=0;}
 }
}
int main(int argc,char**argv){if(argc!=7)return 2;ifstream f(argv[1]);double wt;int n;f>>wt>>n;L={0};B={0};D={n};for(int t=0;t<n;++t){int c;f>>c;if(c>0){L.push_back(c);B.push_back(t);D.push_back(n);}else D[-c]=t;}P.resize(L.size());ifstream pp(argv[2]);H=stoi(argv[4]);seconds=stod(argv[5]);rng.seed(stoul(argv[6]));for(int i=1;i<(int)L.size();++i){pp>>P[i];if(P[i]<0)ids.push_back(i);}if(!pp)return 3;M=ids.size();W=(H+63)/64;dom.assign(M,vector<uint64_t>(W));cnt.assign(M,0);adj.resize(M);assigned.assign(M,-1);vector<int>diff(H+2);for(int v=0;v<M;++v){int i=ids[v];fill(diff.begin(),diff.end(),0);for(int j=1;j<(int)L.size();++j)if(P[j]>=0&&max(B[i],B[j])<min(D[i],D[j])){int l=max(0,P[j]-L[i]+1),r=min(H-L[i],P[j]+L[j]-1);if(l<=r){++diff[l];--diff[r+1];}}int sum=0;for(int x=0;x<=H-L[i];++x){sum+=diff[x];if(sum==0){dom[v][x/64]|=1ULL<<(x%64);cnt[v]++;}}if(!cnt[v]){cout<<"EMPTY "<<i<<endl;return 4;}for(int q=0;q<v;++q)if(max(B[i],B[ids[q]])<min(D[i],D[ids[q]])){adj[v].push_back(q);adj[q].push_back(v);}}
 cout<<"BEGIN movables="<<M<<" min_domain="<<*min_element(cnt.begin(),cnt.end())<<" max_domain="<<*max_element(cnt.begin(),cnt.end())<<endl;start=chrono::steady_clock::now();bool ok=minconf();cout<<"END ok="<<ok<<" timeout="<<timed<<" nodes="<<nodes<<endl;if(!ok)return timed?5:6;for(int v=0;v<M;++v)P[ids[v]]=assigned[v];ofstream out(argv[3]);for(int i=1;i<(int)L.size();++i)out<<P[i]<<'\n';return 0;}
