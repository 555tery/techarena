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
 int order=(mode%1000)/2;
 if(order==1)reverse(survivors.begin(),survivors.end());
 else if(order==2)stable_sort(survivors.begin(),survivors.end(),[&](int a,int b){return len[a]>len[b];});
 else if(order==3)stable_sort(survivors.begin(),survivors.end(),[&](int a,int b){return len[a]<len[b];});
 else if(order>=4){mt19937 rng(2026101900+order);shuffle(survivors.begin(),survivors.end(),rng);}
 if(mode>=2000){
  vector<vector<int>> bylen(41);for(int id:survivors)bylen[len[id]].push_back(id);
  for(auto&v:bylen)sort(v.begin(),v.end(),[&](int a,int b){return birth[a]<birth[b];});
  vector<pair<int,int>> finite;for(auto z:gaps.g)if(z.second<100000000)finite.push_back(z);
  sort(finite.begin(),finite.end(),[](auto a,auto b){return a.second-a.first<b.second-b.first;});
  for(auto gap:finite){int at=gap.first,r=gap.second;vector<int>dp(r-gap.first+1),choose(r-gap.first+1);
   while(at<r){
    for(int x=r-1;x>=at;--x){int ix=x-gap.first;dp[ix]=dp[ix+1];choose[ix]=0;
     for(int l=1;l<=40&&x+l<=r;++l)if(!bylen[l].empty()){
      int id=bylen[l].back();if(fixed.find(x,x+l,n-birth[id],l)!=x)continue;
      int value=l+dp[ix+l];if(value>dp[ix]||(value==dp[ix]&&((mode&1)?l>choose[ix]:choose[ix]==0))){dp[ix]=value;choose[ix]=l;}
     }
    }
    bool recalc=false;
    while(at<r){int l=choose[at-gap.first];if(!l){++at;continue;}
     if(bylen[l].empty()||fixed.find(at,at+l,n-birth[bylen[l].back()],l)!=at){recalc=true;break;}
     int required=0;for(int x=at;x<at+l&&x<(int)available.size();++x)required=max(required,n-available[x]);
     auto it=lower_bound(bylen[l].begin(),bylen[l].end(),required,[&](int id,int d){return birth[id]<d;});if(it==bylen[l].end())return 11;int id=*it;bylen[l].erase(it);if(!gaps.take(at,l))return 10;pos[id]=at;at+=l;
    }
    if(!recalc)break;
   }
  }
 }
 for(int id:survivors)if(pos[id]<0&&!take(id))return 5;
 for(int t=n-1;t>=prefix;--t){int c=cmd[t];if(c>0){int id=pidat[t];gaps.add(pos[id],pos[id]+len[id]);}else if(birth[-c]>=prefix&&!take(-c))return 6;}
 ofstream o(argv[4]);int h=0;for(int id=1;id<(int)len.size();++id){if(pos[id]<0)return 7;o<<pos[id]<<'\n';h=max(h,pos[id]+len[id]);}cout<<20*((h+19)/20)<<endl;
}
