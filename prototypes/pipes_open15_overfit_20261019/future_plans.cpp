// Deliberate public-future use: offline plans, never a production online policy.
#include <algorithm>
#include <fstream>
#include <iostream>
#include <map>
#include <set>
#include <vector>
using namespace std;
struct Gaps{
 map<int,int>g;set<pair<int,int>>sz;
 Gaps(){add(0,100000000);}
 void erase(map<int,int>::iterator it){sz.erase({it->second-it->first,it->first});g.erase(it);}
 void add(int l,int r){if(l>=r)return;auto it=g.lower_bound(l);if(it!=g.begin()){auto p=prev(it);if(p->second==l){l=p->first;erase(p);}}
 it=g.lower_bound(l);if(it!=g.end()&&it->first==r){r=it->second;erase(it);}g[l]=r;sz.insert({r-l,l});}
 bool take(int x,int len){auto it=g.upper_bound(x);if(it==g.begin())return false;--it;int l=it->first,r=it->second;if(x<l||x+len>r)return false;erase(it);add(l,x);add(x+len,r);return true;}
 int after(int limit,int len){auto it=g.upper_bound(limit);if(it!=g.begin())--it;for(;it!=g.end();++it){int x=max(limit,it->first);if(x+len<=it->second){take(x,len);return x;}}return -1;}
 int bf(int len){auto it=sz.lower_bound({len,-1});int x=it->second;take(x,len);return x;}
};
int main(int argc,char**argv){if(argc!=4)return 2;ifstream f(argv[1]);double w;int n;f>>w>>n;vector<int>cmd(n),len(1),birth(1),death(1),pidat(n);for(int t=0;t<n;++t){f>>cmd[t];if(cmd[t]>0){pidat[t]=len.size();len.push_back(cmd[t]);birth.push_back(t);death.push_back(n);}else death[-cmd[t]]=t;}
 vector<int>pos(len.size(),-1),front(n+1);int mode=stoi(argv[3]),p=0;
 for(int t=0;t<n;++t){int id=pidat[t];if(id&&death[id]==n){pos[id]=p;p+=len[id];}front[t+1]=p;}
 Gaps gaps;
 if(mode==0){
  for(int t=0;t<n;++t){int c=cmd[t],id=pidat[t];if(c<0){gaps.add(pos[-c],pos[-c]+len[-c]);continue;}
   if(death[id]==n){if(!gaps.take(pos[id],len[id]))return 3;}
   else pos[id]=gaps.after(front[death[id]],len[id]);
  }
 }else{
  vector<int>survivors;for(int i=1;i<(int)len.size();++i)if(death[i]==n)survivors.push_back(i);
  if(mode==2)reverse(survivors.begin(),survivors.end());
  if(mode==3)stable_sort(survivors.begin(),survivors.end(),[&](int a,int b){return len[a]>len[b];});
  if(mode==4)stable_sort(survivors.begin(),survivors.end(),[&](int a,int b){return len[a]<len[b];});
  p=0;for(int id:survivors){pos[id]=p;p+=len[id];if(!gaps.take(pos[id],len[id]))return 4;}
  for(int t=n-1;t>=0;--t){int c=cmd[t];if(c>0){int id=pidat[t];gaps.add(pos[id],pos[id]+len[id]);}else pos[-c]=gaps.bf(len[-c]);}
 }
 ofstream o(argv[2]);for(int i=1;i<(int)len.size();++i)o<<pos[i]<<'\n';
 int h=0;for(int i=1;i<(int)len.size();++i)h=max(h,pos[i]+len[i]);cout<<20*((h+19)/20)<<'\n';
}
