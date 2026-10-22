// OPEN15_FULL_OVERFIT. Fixed-placement temporal repair using full lifetimes.
#include <algorithm>
#include <fstream>
#include <iostream>
#include <numeric>
#include <vector>
using namespace std;
int main(int argc,char**argv){if(argc!=7)return 2;ifstream f(argv[1]);double w;int n;f>>w>>n;vector<int>len(1),birth(1),death(1);for(int t=0;t<n;++t){int c;f>>c;if(c>0){len.push_back(c);birth.push_back(t);death.push_back(n);}else death[-c]=t;}
 int H=stoi(argv[4]),mode=stoi(argv[5]),pin=stoi(argv[6]);vector<int>pos(len.size(),-1),todo;ifstream in(argv[2]);for(int i=1;i<(int)len.size();++i){in>>pos[i];if(pos[i]<0)todo.push_back(i);}if(!in)return 3;
 stable_sort(todo.begin(),todo.end(),[&](int a,int b){switch(mode/2){case 0:return (death[a]-birth[a])>(death[b]-birth[b]);case 1:return len[a]>len[b];case 2:return 1LL*len[a]*(death[a]-birth[a])>1LL*len[b]*(death[b]-birth[b]);default:return birth[a]<birth[b];}});
 vector<int>diff(H+2);
 for(int id:todo){fill(diff.begin(),diff.end(),0);int cap=H-len[id];for(int j=1;j<(int)len.size();++j)if(pos[j]>=0&&max(birth[id],birth[j])<min(death[id],death[j])){int l=max(0,pos[j]-len[id]+1),r=min(cap,pos[j]+len[j]-1);if(l<=r){++diff[l];--diff[r+1];}}
  int sum=0,best=-1,bestspan=H+1,start=-1;for(int x=0;x<=cap+1;++x){sum+=diff[x];if(x<=cap&&sum==0){if(start<0)start=x;}else if(start>=0){int span=x-start;if(best<0||((mode&1)&&span<bestspan)){best=start;bestspan=span;}start=-1;}}
  if(best<0){cerr<<"FAIL "<<id<<" repaired "<<(&id-&id)<<endl;return 1;}pos[id]=best;
 }
 if(pin&&pos[1]!=0)return 5;ofstream out(argv[3]);int hi=0;for(int i=1;i<(int)len.size();++i){out<<pos[i]<<'\n';hi=max(hi,pos[i]+len[i]);}cout<<hi<<" repaired "<<todo.size()<<endl;return 0;}
