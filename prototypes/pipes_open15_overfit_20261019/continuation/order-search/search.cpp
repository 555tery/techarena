// OPEN15_FULL_OVERFIT: optimize offline temporal-conflict orientation.
#include <algorithm>
#include <chrono>
#include <fstream>
#include <iostream>
#include <numeric>
#include <random>
#include <vector>
using namespace std;
struct Seg{int n;vector<int>h,id,lazy;Seg(int n):n(n),h(4*n),id(4*n),lazy(4*n,-1){}void reset(){fill(h.begin(),h.end(),0);fill(id.begin(),id.end(),0);fill(lazy.begin(),lazy.end(),-1);}void put(int v,int x,int who){h[v]=x;id[v]=who;lazy[v]=x;}void push(int v){if(lazy[v]>=0){put(2*v,h[v],id[v]);put(2*v+1,h[v],id[v]);lazy[v]=-1;}}pair<int,int>get(int a,int b,int v,int l,int r){if(a<=l&&r<=b)return {h[v],id[v]};push(v);int m=(l+r)/2;pair<int,int>x={0,0};if(a<m)x=get(a,b,2*v,l,m);if(b>m)x=max(x,get(a,b,2*v+1,m,r));return x;}void set(int a,int b,int x,int who,int v,int l,int r){if(a<=l&&r<=b){put(v,x,who);return;}push(v);int m=(l+r)/2;if(a<m)set(a,b,x,who,2*v,l,m);if(b>m)set(a,b,x,who,2*v+1,m,r);if(h[2*v]>=h[2*v+1]){h[v]=h[2*v];id[v]=id[2*v];}else{h[v]=h[2*v+1];id[v]=id[2*v+1];}}};
int main(int argc,char**argv){if(argc!=6)return 2;ifstream f(argv[1]);double wt;int n;f>>wt>>n;vector<int>L(1),B(1),D(1);for(int t=0;t<n;++t){int x;f>>x;if(x>0){L.push_back(x);B.push_back(t);D.push_back(n);}else D[-x]=t;}int N=L.size()-1;vector<int>seed(N+1),order(N),pos(N+1),prev(N+1),rank(N+1);ifstream ip(argv[2]);for(int i=1;i<=N;++i)ip>>seed[i];iota(order.begin(),order.end(),1);stable_sort(order.begin(),order.end(),[&](int a,int b){return seed[a]<seed[b];});auto it=find(order.begin(),order.end(),1);rotate(order.begin(),it,it+1);Seg seg(n);int last=0;auto eval=[&](const vector<int>&ord){seg.reset();int h=0;for(int i:ord){auto q=seg.get(B[i],D[i],1,0,n);pos[i]=q.first;prev[i]=q.second;int z=pos[i]+L[i];seg.set(B[i],D[i],z,i,1,0,n);if(z>=h){h=z;last=i;}}return h;};int cur=eval(order),best=cur;vector<int>bestorder=order;mt19937 rng(stoul(argv[5]));double secs=stod(argv[4]);auto start=chrono::steady_clock::now();long long steps=0;int stale=0;cout<<"INITIAL "<<cur<<endl;
while(chrono::duration<double>(chrono::steady_clock::now()-start).count()<secs){vector<int>chain;for(int q=last;q;q=prev[q])chain.push_back(q);for(int k=0;k<N;++k)rank[order[k]]=k;auto next=order;int v=chain[rng()%chain.size()],p=prev[v];if(v==1||p==0||p==1)continue;int a=rank[v],b=rank[p];if(rng()%4==0){int off=int(rng()%21)-10;b=max(1,min(N-1,b+off));}if(a==b)continue;int tmp=next[a];next.erase(next.begin()+a);next.insert(next.begin()+b,tmp);int nh=eval(next);++steps;
 if(nh<best){best=nh;bestorder=next;ofstream out(argv[3]);for(int i=1;i<=N;++i)out<<pos[i]<<'\n';cout<<"BEST "<<best<<" step="<<steps<<endl;stale=0;if(best<=20760)break;}else ++stale;
 int allowance=stale>2000?16:stale>500?5:0;bool accept=nh<=cur||((nh-cur)<=allowance&&(rng()%100)<12);if(accept){order=move(next);cur=nh;}else eval(order);if(stale>5000){order=bestorder;cur=eval(order);stale=0;}}
cout<<"FINAL "<<best<<" steps="<<steps<<endl;}
