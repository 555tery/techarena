// INTENTIONAL OPEN15 FULL OVERFIT: both future branches define the shared prefix.
#define main old_future_main
#include "../future_plans.cpp"
#undef main
#include <random>
vector<int> readcmd(const char*p){ifstream f(p);double w;int n;f>>w>>n;vector<int>a(n);for(int&x:a)f>>x;return a;}
int main(int argc,char**argv){
 if(argc!=6)return 2;auto a=readcmd(argv[1]),b=readcmd(argv[2]);int mode=stoi(argv[4]),cut=stoi(argv[5]);
 vector<int>len(1),born(1),da(1),db(1),ids(cut);for(int t=0;t<(int)a.size();++t){int c=a[t];if(c>0){if(t<cut)ids[t]=len.size();len.push_back(c);born.push_back(t);da.push_back(a.size());}else da[-c]=t;}
 int pid=0;db.resize(len.size(),b.size());for(int t=0;t<(int)b.size();++t){int c=b[t];if(c>0)++pid;else if(-c<(int)db.size())db[-c]=t;}
 vector<int>surv,pos(len.size(),-1);for(int i=1;i<(int)len.size()&&born[i]<cut;++i)if(da[i]>=cut)surv.push_back(i);
 auto group=[&](int id){bool sa=da[id]==(int)a.size(),sb=db[id]==(int)b.size();switch((mode/2)%8){case 0:return sb?0:1;case 1:return sa?0:1;case 2:return (sb?0:2)+(sa?0:1);case 3:return (sa?0:2)+(sb?0:1);case 4:return sb?1:0;case 5:return sa?1:0;case 6:return sa==sb?0:1;default:return 0;}};
 stable_sort(surv.begin(),surv.end(),[&](int x,int y){if(x==y)return false;if(x==1||y==1)return x==1;int gx=group(x),gy=group(y);if(gx!=gy)return gx<gy;if(mode>=16)return len[x]>len[y];return x<y;});
 Gaps g;int end=0;for(int i:surv){pos[i]=end;g.take(end,len[i]);end+=len[i];}
 for(int t=cut-1;t>=0;--t){int c=a[t];if(c>0){int id=ids[t];g.add(pos[id],pos[id]+len[id]);}else pos[-c]=(mode&1)?g.after(0,len[-c]):g.bf(len[-c]);}
 ofstream o(argv[3]);int h=0;for(int i=1;i<(int)len.size()&&born[i]<cut;++i){o<<pos[i]<<'\n';h=max(h,pos[i]+len[i]);}cout<<h<<endl;
}
