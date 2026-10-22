// OPEN15 OVERFIT RESEARCH ONLY: this offline builder reads complete public
// lifetimes, including future deletions. It is NOT an online allocator.
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
struct Range {int l,r,c;};
struct Block {int len,seed,first; vector<Range> spans;};
struct Tree {
 int n; vector<int> mx,lazy;
 Tree(int n):n(n),mx(4*n),lazy(4*n,-1){}
 void set(int i,int v){mx[i]=v;lazy[i]=v;}
 void push(int i){if(lazy[i]>=0){set(2*i,lazy[i]);set(2*i+1,lazy[i]);lazy[i]=-1;}}
 int query(int a,int b,int i,int l,int r){if(a<=l&&r<=b)return mx[i];push(i);int m=(l+r)/2,v=0;if(a<m)v=query(a,b,2*i,l,m);if(b>m)v=max(v,query(a,b,2*i+1,m,r));return v;}
 void assign(int a,int b,int v,int i,int l,int r){if(a<=l&&r<=b){set(i,v);return;}push(i);int m=(l+r)/2;if(a<m)assign(a,b,v,2*i,l,m);if(b>m)assign(a,b,v,2*i+1,m,r);mx[i]=max(mx[2*i],mx[2*i+1]);}
};
int main(int argc,char**argv){
 if(argc!=4)return 2;
 ifstream in(argv[1]);int n,nt,k;in>>n>>nt>>k;vector<double>w(k);vector<int>f(k);
 for(int c=0;c<k;++c)in>>w[c]>>f[c];
 vector<Block>b(n);vector<int>best(n),order(n);iota(order.begin(),order.end(),0);
 for(int i=0;i<n;++i){int m;in>>b[i].len>>b[i].seed>>b[i].first>>m;best[i]=b[i].seed;for(int j=0;j<m;++j){Range r;in>>r.l>>r.r>>r.c;b[i].spans.push_back(r);}}
 if(!in)return 3;
 auto score=[&](const vector<int>&p){vector<int>height(k);for(int i=0;i<n;++i)for(auto r:b[i].spans)height[r.c]=max(height[r.c],p[i]+b[i].len);double s=0;for(int c=0;c<k;++c)s+=w[c]*f[c]/(20*((height[c]+19)/20));return pair<double,vector<int>>(s,height);};
 auto initial=score(best);double bs=initial.first;mt19937_64 rng(20261019);int iterations=stoi(argv[3]);
 auto save=[&](int it){ofstream out(string(argv[2])+".tmp");for(int x:best)out<<x<<'\n';out.close();rename((string(argv[2])+".tmp").c_str(),argv[2]);auto s=score(best);cout<<setprecision(15)<<"best iteration="<<it<<" score="<<s.first<<" T=";for(int h:s.second)cout<<20*((h+19)/20)<<',';cout<<endl;};
 save(-1);
 for(int it=0;it<iterations;++it){
  vector<double>key(n);int scale=(it==0?0:(1<<((it-1)%8)));
  for(int i=0;i<n;++i){double u=double(rng()%1000000)/1000000.;key[i]=best[i]+scale*(2*u-1);}
  // Periodically explore a duration-aware order, still selected on Open15 only.
  if(it>0&&it%16==15)for(int i=0;i<n;++i){int duration=0;for(auto r:b[i].spans)duration=max(duration,r.r-r.l);key[i]=best[i]-scale*log1p(duration);}
  stable_sort(order.begin(),order.end(),[&](int x,int y){return key[x]!=key[y]?key[x]<key[y]:x<y;});
  Tree tree(nt);vector<int>pos(n);
  for(int id:order){int x=0;for(auto r:b[id].spans)x=max(x,tree.query(r.l,r.r,1,0,nt));pos[id]=x;for(auto r:b[id].spans)tree.assign(r.l,r.r,x+b[id].len,1,0,nt);}
  auto s=score(pos);
  if(it==0){ofstream proof(string(argv[2])+".compacted");for(int x:pos)proof<<x<<'\n';cout<<setprecision(15)<<"compacted score="<<s.first<<endl;}
  if(s.first>bs+1e-12){best.swap(pos);bs=s.first;save(it);}
  else if(it%16==0)cout<<setprecision(15)<<"trial iteration="<<it<<" score="<<s.first<<endl;
 }
}
