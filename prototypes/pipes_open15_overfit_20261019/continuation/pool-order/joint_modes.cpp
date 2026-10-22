// OPEN15_FULL_OVERFIT. Bidirectional offline reconstruction around exact peak.
#define main unused_future_main
#include "../../future_plans.cpp"
#undef main
#include <chrono>
#include <random>
#include <numeric>
int main(int argc,char**argv){if(argc!=8)return 2;int classmode=stoi(argv[7]);ifstream f(argv[1]);double wt;int n;f>>wt>>n;vector<int>cmd(n),L(1),B(1),D(1),at(n);int live=0,peak=0,cut=0;for(int t=0;t<n;++t){f>>cmd[t];if(cmd[t]>0){at[t]=L.size();L.push_back(cmd[t]);B.push_back(t);D.push_back(n);live+=cmd[t];}else{D[-cmd[t]]=t;live-=L[-cmd[t]];}if(live>peak){peak=live;cut=t;}}
 vector<int>d15(L.size(),200000);{ifstream ff(argv[5]);double w;int nn;ff>>w>>nn;for(int t=0;t<nn;++t){int c;ff>>c;if(c<0&&-c<(int)L.size())d15[-c]=t;}}auto special=[&](int i){return B[i]<4999&&d15[i]<200000;};vector<int>seedpos(L.size());{ifstream ff(argv[6]);for(int i=1;i<(int)L.size();++i)ff>>seedpos[i];}
 int H=20*((peak+19)/20);vector<int>perms,temps,P(L.size(),-1);for(int i=1;i<(int)L.size();++i)if(B[i]<=cut&&cut<D[i]){if(D[i]==n)perms.push_back(i);else temps.push_back(i);}sort(perms.begin(),perms.end(),[&](int a,int b){if(a==1||b==1)return a<b;if(special(a)!=special(b))return !special(a);if(special(a)){if(classmode==1)return d15[a]>d15[b];if(classmode==2&&L[a]!=L[b])return L[a]<L[b];if(classmode==3&&L[a]!=L[b])return L[a]>L[b];if(classmode==4)return B[a]<B[b];if(classmode==5)return B[a]>B[b];return d15[a]<d15[b];}return B[a]>B[b];});sort(temps.begin(),temps.end(),[&](int a,int b){if(special(a)!=special(b))return special(a);return seedpos[a]<seedpos[b];});int low=0;for(int i:perms){P[i]=low;low+=L[i];}
 int failPid=0,deficit=0;bool reversing=false;auto eval=[&](const vector<int>&order,int policy){reversing=false;Gaps gaps;gaps.g.clear();gaps.sz.clear();gaps.add(low,H);int x=low;for(int i:order){P[i]=x;if(!gaps.take(x,L[i]))return 100000000;x+=L[i];}
 auto take=[&](int i){int x=-1;
 if(reversing&&special(i)){for(auto z:gaps.g){int at=max(low,z.first);if(at+L[i]<=z.second){x=at;break;}}}
 if(x>=0){}else if(policy%2){auto it=gaps.sz.lower_bound({L[i],-1});if(it!=gaps.sz.end())x=it->second;}else{for(auto z:gaps.g)if(z.second-z.first>=L[i]){x=z.first;break;}}if(x<0){failPid=i;int lg=0;for(auto z:gaps.g)lg=max(lg,z.second-z.first);deficit=L[i]-lg;return false;}gaps.take(x,L[i]);P[i]=x;return true;};
 for(int t=cut+1;t<n;++t){int c=cmd[t];if(c<0)gaps.add(P[-c],P[-c]+L[-c]);else if(!take(at[t]))return 1000000+100*(n-t)+deficit;}
 // Restore peak state, then reconstruct earlier history.
 gaps.g.clear();gaps.sz.clear();gaps.add(0,H);for(int i:perms)gaps.take(P[i],L[i]);for(int i:order)gaps.take(P[i],L[i]);
 reversing=true;for(int t=cut;t>=0;--t){int c=cmd[t];if(c>0)gaps.add(P[at[t]],P[at[t]]+L[at[t]]);else if(!take(-c))return 100*t+deficit;}
 return 0;};
 mt19937 rng(stoul(argv[4]));int policy=1,cur=eval(temps,policy),best=cur;vector<int>bestOrder=temps;double secs=stod(argv[3]);auto start=chrono::steady_clock::now();long long steps=0;cout<<"INITIAL score="<<cur<<" fail="<<failPid<<endl;
 auto save=[&](){ofstream out(argv[2]);for(int i=1;i<(int)P.size();++i)out<<P[i]<<'\n';};
 if(cur==0){save();cout<<"INITIAL_SUCCESS H="<<H<<endl;return 0;}
 while(chrono::duration<double>(chrono::steady_clock::now()-start).count()<secs){auto next=temps;int a=rng()%temps.size(),b=rng()%temps.size();if(rng()%4){vector<int>recent;for(int k=0;k<(int)temps.size();++k)if(B[temps[k]]>=9600&&!special(temps[k]))recent.push_back(k);a=recent[rng()%recent.size()];b=recent[rng()%recent.size()];}if(a==b||special(temps[a])||special(temps[b]))continue;if(rng()%2)swap(next[a],next[b]);else{int v=next[a];next.erase(next.begin()+a);next.insert(next.begin()+b,v);}int np=rng()%8?policy:1-policy;int score=eval(next,np);++steps;
 if(score<best){best=score;bestOrder=next;cout<<"BEST "<<best<<" fail="<<failPid<<" step="<<steps<<endl;if(!best){save();cout<<"SUCCESS H="<<H<<endl;return 0;}}
 if(score<=cur||(score<=cur+1000&&rng()%100<3)){temps=std::move(next);cur=score;policy=np;}
 if(steps%5000==0){temps=bestOrder;cur=eval(temps,policy);}
 }
 cout<<"FINAL best="<<best<<" steps="<<steps<<endl;return 1;}
