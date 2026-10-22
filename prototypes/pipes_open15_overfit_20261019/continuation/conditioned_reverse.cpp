// OPEN15 FULL OVERFIT. Offline builder using all future deletions.
#define main old_future_main
#include "../future_plans.cpp"
#undef main
#include <limits>
struct Space {
 int n;vector<int>lo,hi;
 Space(const vector<int>&a):n(a.size()),lo(4*n),hi(4*n){build(a,1,0,n);}
 void build(const vector<int>&a,int v,int l,int r){if(r-l==1){lo[v]=hi[v]=a[l];return;}int m=(l+r)/2;build(a,2*v,l,m);build(a,2*v+1,m,r);lo[v]=min(lo[2*v],lo[2*v+1]);hi[v]=max(hi[2*v],hi[2*v+1]);}
 int run=0,start=0,answer=-1;
 void walk(int ql,int qr,int death,int length,int v,int l,int r){
  if(answer>=0||r<=ql||qr<=l)return;
  if(ql<=l&&r<=qr&&lo[v]>=death){if(run==0)start=l;run+=r-l;if(run>=length)answer=start;return;}
  if(hi[v]<death){run=0;return;}
  if(r-l==1){if(run==0)start=l;if(++run>=length)answer=start;return;}
  int m=(l+r)/2;walk(ql,qr,death,length,2*v,l,m);walk(ql,qr,death,length,2*v+1,m,r);
 }
 int find(int l,int r,int d,int len){if(l>=n)return r-l>=len?l:-1;run=0;answer=-1;walk(l,min(r,n),d,len,1,0,n);if(answer>=0)return answer;if(r>n){if(!run)start=n;run+=r-n;if(run>=len)return start;}return -1;}
};

#include <random>
int main(int argc,char**argv){
 if(argc!=6)return 2;ifstream f(argv[1]);double w;int n;f>>w>>n;vector<int>cmd(n),len(1),birth(1),death(1),pidat(n);
 for(int t=0;t<n;++t){f>>cmd[t];if(cmd[t]>0){pidat[t]=len.size();len.push_back(cmd[t]);birth.push_back(t);death.push_back(n);}else death[-cmd[t]]=t;}
 int prefix=stoi(argv[3]),mode=stoi(argv[5]),maxend=0;ifstream pins(argv[2]);vector<int>pos(len.size(),-1),survivors;
 for(int id=1;id<(int)len.size();++id)if(birth[id]<prefix){pins>>pos[id];maxend=max(maxend,pos[id]+len[id]);}else if(death[id]==n)survivors.push_back(id);
 if(!pins)return 3;vector<int>available(maxend+40,n+1);
 for(int id=1;id<(int)len.size()&&birth[id]<prefix;++id)for(int x=pos[id];x<pos[id]+len[id];++x)available[x]=min(available[x],n-death[id]);
 Space fixed(available);Gaps gaps;
 auto take=[&](int id){
  int chosen=-1,bestsize=numeric_limits<int>::max();
  if(mode&1){for(auto z:gaps.sz){if(z.first<len[id])continue;int x=fixed.find(z.second,z.second+z.first,n-birth[id],len[id]);if(x>=0){chosen=x;break;}}}
  else for(auto z:gaps.g){if(z.second-z.first<len[id])continue;int x=fixed.find(z.first,z.second,n-birth[id],len[id]);if(x>=0){chosen=x;break;}}
  if(chosen<0||!gaps.take(chosen,len[id]))return false;pos[id]=chosen;return true;
 };
 for(int id=1;id<(int)len.size()&&birth[id]<prefix;++id)if(death[id]==n&&!gaps.take(pos[id],len[id]))return 4;
 int order=mode/2;
 if(order==1)reverse(survivors.begin(),survivors.end());
 else if(order==2)stable_sort(survivors.begin(),survivors.end(),[&](int a,int b){return len[a]>len[b];});
 else if(order==3)stable_sort(survivors.begin(),survivors.end(),[&](int a,int b){return len[a]<len[b];});
 else if(order>=4){mt19937 rng(2026101900+order);shuffle(survivors.begin(),survivors.end(),rng);}
 for(int id:survivors)if(!take(id))return 5;
 for(int t=n-1;t>=prefix;--t){int c=cmd[t];if(c>0){int id=pidat[t];gaps.add(pos[id],pos[id]+len[id]);}else if(birth[-c]>=prefix&&!take(-c))return 6;}
 ofstream o(argv[4]);int h=0;for(int id=1;id<(int)len.size();++id){if(pos[id]<0)return 7;o<<pos[id]<<'\n';h=max(h,pos[id]+len[id]);}cout<<20*((h+19)/20)<<endl;
}
