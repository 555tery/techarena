// Bounded offline diagnostic: same retained PID set, different prefix geometry.
#include <algorithm>
#include <fstream>
#include <iostream>
#include <set>
#include <tuple>
#include <vector>
using namespace std;
struct Pipe { int pid, len, good, bad; };
struct Result { double ratio, goodkpi, badkpi; int state, left, right, len, count, fill, gt, bt; };
int capacity(vector<pair<int,int>> spans, int trench, int length) {
    sort(spans.begin(), spans.end());
    int end = 0, result = 0;
    for (auto [start,size] : spans) { result += (start-end)/length; end=start+size; }
    return result + (trench-end)/length;
}
int main(int argc,char**argv) {
    if (argc != 3) return 2;
    ifstream f(argv[1]); int n; f>>n;
    vector<Result> results;
    for(int s=0;s<n;s++) {
        int id,cas,pref,gt,bt,m; f>>id>>cas>>pref>>gt>>bt>>m;
        vector<Pipe> pipes(m); for(auto& p:pipes) f>>p.pid>>p.len>>p.good>>p.bad;
        if(gt<100) continue;
        for(int length : {40,32,24,16,8}) for(double fraction:{.01,.025,.05,.1,.2,.3,.5,.75,1.}) {
            int width=max(1,int(gt*fraction));
            int step=max(1,width/3);
            for(int left=0;left+width<=gt;left+=step) {
                vector<pair<int,int>> gs,bs; int volume=0;
                for(auto p:pipes) if(p.good>=left && p.good+p.len<=left+width) {
                    gs.push_back({p.good,p.len});bs.push_back({p.bad,p.len});volume+=p.len;
                }
                if(gs.empty()) continue;
                int fill=capacity(gs,gt,length), bc=capacity(bs,bt,length);
                if(fill<=bc || pref + (m-int(gs.size())) + fill > 200000) continue;
                int finalv=volume+fill*length;
                int finalb=bt+((max(0,fill-bc)*length+19)/20)*20;
                double good=double(finalv)/gt,bad=double(finalv)/finalb;
                if(good<.8)continue;
                results.push_back({bad/good,good,bad,id,left,left+width,length,int(gs.size()),fill,gt,finalb});
            }
        }
    }
    sort(results.begin(),results.end(),[](const Result& a,const Result& b){return (a.ratio) < (b.ratio);});
    ofstream o(argv[2]);
    set<int> seen;
    for(int i=0;i<int(results.size());i++) {
        auto r=results[i];
        bool first = seen.insert(r.state).second;
        if(i>=100 && !first) continue;
        o<<r.state<<' '<<r.left<<' '<<r.right<<' '<<r.len<<' '<<r.count<<' '<<r.fill<<' '<<r.goodkpi<<' '<<r.badkpi<<' '<<r.ratio<<' '<<r.gt<<' '<<r.bt<<'\n';
    }
    cerr<<results.size()<<" candidates\n";
}
