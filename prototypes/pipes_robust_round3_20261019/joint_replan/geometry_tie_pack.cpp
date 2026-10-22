#include <algorithm>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <random>
#include <string>
#include <vector>
using namespace std;
struct Range{int l,r,c;};
struct Block{int len,seed,first;vector<Range>spans;};
struct Tree{int n;vector<int>mx,lazy;Tree(int n):n(n),mx(4*n),lazy(4*n,-1){}void set(int i,int v){mx[i]=v;lazy[i]=v;}void push(int i){if(lazy[i]>=0){set(2*i,lazy[i]);set(2*i+1,lazy[i]);lazy[i]=-1;}}int query(int a,int b,int i,int l,int r){if(a<=l&&r<=b)return mx[i];push(i);int m=(l+r)/2,v=0;if(a<m)v=query(a,b,2*i,l,m);if(b>m)v=max(v,query(a,b,2*i+1,m,r));return v;}void assign(int a,int b,int v,int i,int l,int r){if(a<=l&&r<=b){set(i,v);return;}push(i);int m=(l+r)/2;if(a<m)assign(a,b,v,2*i,l,m);if(b>m)assign(a,b,v,2*i+1,m,r);mx[i]=max(mx[2*i],mx[2*i+1]);}};
static int ceil20(int x){return 20*((x+19)/20);}
int main(int argc,char**argv){if(argc!=6){cerr<<"usage: input output iterations goalT8 goalT13\n";return 2;}ifstream in(argv[1]);int n,nt,k;in>>n>>nt>>k;if(k!=2)return 3;vector<double>w(k);vector<int>f(k),goal(k);for(int c=0;c<k;c++)in>>w[c]>>f[c];goal[0]=stoi(argv[4]);goal[1]=stoi(argv[5]);vector<Block>b(n);vector<int>best(n),order(n);iota(order.begin(),order.end(),0);for(int i=0;i<n;i++){int m;in>>b[i].len>>b[i].seed>>b[i].first>>m;best[i]=b[i].seed;while(m--){Range x;in>>x.l>>x.r>>x.c;b[i].spans.push_back(x);}}if(!in)return 4;
 auto score=[&](const vector<int>&p){vector<int>h(k);for(int i=0;i<n;i++)for(auto r:b[i].spans)h[r.c]=max(h[r.c],p[i]+b[i].len);vector<int>T(k);double s=0;for(int c=0;c<k;c++){T[c]=ceil20(h[c]);s+=w[c]*f[c]/T[c];}return pair<double,vector<int>>(s,T);};
 auto exact=[&](const vector<int>&p){return score(p).second==goal;};
 auto lexbetter=[&](const vector<int>&x,const vector<int>&y){if(x[1]!=y[1])return x[1]<y[1];if(x[0]!=y[0])return x[0]<y[0];for(int i=0;i<min(n,210);i++)if(x[i]!=y[i])return x[i]<y[i];return false;};
 auto initial=score(best);if(initial.second!=goal){cerr<<"seed does not match goal\n";return 5;}double bs=initial.first;mt19937_64 rng(20261019);int iterations=stoi(argv[3]);
 auto save=[&](int it){ofstream o(string(argv[2])+".tmp");for(int x:best)o<<x<<'\n';o.close();rename((string(argv[2])+".tmp").c_str(),argv[2]);auto s=score(best);cout<<setprecision(15)<<"best iteration="<<it<<" score="<<s.first<<" T="<<s.second[0]<<','<<s.second[1]<<" p0,p1="<<best[0]<<','<<best[1]<<"\n";};
 save(-1);
 vector<int> base(n);iota(base.begin(),base.end(),0);
 for(int it=0;it<iterations;it++){
  order=base;int mode=it%4;
  if(mode==0||mode==1||mode==2){
   stable_sort(order.begin(),order.end(),[&](int a,int z){if(mode==2){long long da=0,dz=0;for(auto r:b[a].spans)da=max(da,(long long)r.r-r.l);for(auto r:b[z].spans)dz=max(dz,(long long)r.r-r.l);long long ka=da*b[a].len,kz=dz*b[z].len;if(ka!=kz)return ka>kz;}return b[a].seed!=b[z].seed?b[a].seed<b[z].seed:a<z;});
   int first=(mode==1?1:0),second=(mode==1?0:1);order.erase(find(order.begin(),order.end(),first));order.erase(find(order.begin(),order.end(),second));order.insert(order.begin(),second);order.insert(order.begin(),first);
  }else{
   vector<pair<uint64_t,int>> key;key.reserve(n);for(int i=0;i<n;i++)key.push_back({rng(),i});sort(key.begin(),key.end());for(int i=0;i<n;i++)order[i]=key[i].second;
  }
  Tree tree(nt);vector<int>pos(n);for(int id:order){int x=0;for(auto r:b[id].spans)x=max(x,tree.query(r.l,r.r,1,0,nt));pos[id]=x;for(auto r:b[id].spans)tree.assign(r.l,r.r,x+b[id].len,1,0,nt);}
  auto s=score(pos);if(s.second==goal&&lexbetter(pos,best)){best.swap(pos);bs=s.first;save(it);}
 }
}
