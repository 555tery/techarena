// OPEN15 FULL OVERFIT: uses known future lifetimes and pinned public prefixes.
// Offline builder only. No claim of online generalization.
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
int main(int argc,char**argv){
 if(argc!=6)return 2;ifstream f(argv[1]);double w;int n;f>>w>>n;vector<int>cmd(n),len(1),birth(1),death(1),pidat(n);
 for(int t=0;t<n;++t){f>>cmd[t];if(cmd[t]>0){pidat[t]=len.size();len.push_back(cmd[t]);birth.push_back(t);death.push_back(n);}else death[-cmd[t]]=t;}
 int prefix=stoi(argv[3]),mode=stoi(argv[5]);ifstream pins(argv[2]);vector<int>pos(len.size(),-1);for(int id=1;id<(int)len.size()&&birth[id]<prefix;++id)pins>>pos[id];if(!pins)return 3;
 Gaps reserves;int maxend=0;
 // Determine permanent positions while respecting all pinned prefix lifetimes.
 for(int t=0;t<n;++t){int id=pidat[t],c=cmd[t];if(c>0){
   if(t<prefix){if(!reserves.take(pos[id],len[id]))return 4;}
   else if(death[id]==n)pos[id]=(mode&1)?reserves.bf(len[id]):reserves.after(0,len[id]);
   if(death[id]==n)maxend=max(maxend,pos[id]+len[id]);
  }else if(birth[-c]<prefix)reserves.add(pos[-c],pos[-c]+len[-c]);
 }
 vector<int>available(maxend+40,n+1);
 for(int id=1;id<(int)len.size();++id)if(death[id]==n)for(int x=pos[id];x<pos[id]+len[id];++x)available[x]=birth[id];
 Space future(available);Gaps current;
 for(int t=0;t<n;++t){int c=cmd[t],id=pidat[t];if(c<0){current.add(pos[-c],pos[-c]+len[-c]);continue;}
  if(t<prefix||death[id]==n){if(!current.take(pos[id],len[id]))return 5;continue;}
  int chosen=-1,bestsize=numeric_limits<int>::max();
  for(auto gap:current.g){if(gap.second-gap.first<len[id])continue;int x=future.find(gap.first,gap.second,death[id],len[id]);if(x>=0){
    if(!(mode&2)){chosen=x;break;}
    if(gap.second-gap.first<bestsize){bestsize=gap.second-gap.first;chosen=x;}
   }}
  if(chosen<0||!current.take(chosen,len[id]))return 6;pos[id]=chosen;
 }
 ofstream o(argv[4]);for(int i=1;i<(int)len.size();++i)o<<pos[i]<<'\n';int h=0;for(int i=1;i<(int)len.size();++i)h=max(h,pos[i]+len[i]);cout<<20*((h+19)/20)<<endl;
}
