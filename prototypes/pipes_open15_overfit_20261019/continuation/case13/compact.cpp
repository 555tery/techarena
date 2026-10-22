#include <algorithm>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <numeric>
#include <set>
#include <string>
#include <vector>
using namespace std;
struct Inst { int n; vector<int> cmd,size,birth,death,pidAt; explicit Inst(const string&p){ifstream f(p);double w;f>>w>>n;cmd.resize(n);for(int&x:cmd)f>>x;size.push_back(0);birth.push_back(-1);death.push_back(n);pidAt.assign(n,0);for(int t=0;t<n;++t)if(cmd[t]>0){int id=size.size();size.push_back(cmd[t]);birth.push_back(t);death.push_back(n);pidAt[t]=id;}else death[-cmd[t]]=t;}};
static int maxEnd(const vector<int>&p,const vector<int>&s){int h=0;for(size_t i=1;i<p.size();++i)h=max(h,p[i]+s[i]);return h;}
static long long sumPos(const vector<int>&p){long long x=0;for(size_t i=1;i<p.size();++i)x+=p[i];return x;}
static void save(const vector<int>&p,const string&file){string tmp=file+".tmp";ofstream o(tmp);for(size_t i=1;i<p.size();++i)o<<p[i]<<'\n';o.close();rename(tmp.c_str(),file.c_str());}
int main(int argc,char**argv){if(argc<4)return 2;Inst in(argv[1]);string plan=argv[2],out=argv[3];vector<int>pos(1,0);{ifstream f(plan);int x;while(f>>x)pos.push_back(x);}if(pos.size()!=in.size.size()){cerr<<"wrong position count\n";return 3;}
 vector<vector<int>> adj(in.size.size());set<int> active;
 for(int t=0;t<in.n;++t){int c=in.cmd[t];if(c>0){int id=in.pidAt[t];for(int j:active){adj[id].push_back(j);adj[j].push_back(id);}active.insert(id);}else active.erase(-c);}
 vector<int> ord(in.size.size()-1);iota(ord.begin(),ord.end(),1);
 int h=maxEnd(pos,in.size); long long s=sumPos(pos);cerr<<"initial H="<<h<<" sum="<<s<<"\n";
 for(int sweep=0;sweep<50;++sweep){
  if(sweep%3==0)sort(ord.begin(),ord.end(),[&](int a,int b){return pos[a]>pos[b];});
  else if(sweep%3==1)sort(ord.begin(),ord.end(),[&](int a,int b){return pos[a]<pos[b];});
  else {uint64_t x=20261019u+sweep;for(int i=(int)ord.size()-1;i>0;--i){x=x*6364136223846793005ULL+1;swap(ord[i],ord[x%(i+1)]);}}
  int moves=0;
  for(int i:ord){int cur=pos[i];vector<pair<int,int>> forb;forb.reserve(adj[i].size());for(int j:adj[i]){int l=pos[j]-in.size[i]+1;int r=pos[j]+in.size[j]-1;if(r<0)continue;if(l<0)l=0;forb.push_back({l,r});}sort(forb.begin(),forb.end());int x=0;for(auto [l,r]:forb){if(l>x)break;if(r>=x)x=r+1;if(x>=cur)break;}if(x<cur){pos[i]=x;++moves;}}
  int nh=maxEnd(pos,in.size);long long ns=sumPos(pos);
  cerr<<"sweep="<<sweep+1<<" moves="<<moves<<" H="<<nh<<" sum="<<ns<<"\n";
  if(nh<h || (nh==h && ns<s)){h=nh;s=ns;save(pos,out);}
  if(moves==0)break;
 }
 return 0;
}
