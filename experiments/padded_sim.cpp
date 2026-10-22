#include <algorithm>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <set>
#include <string>
#include <vector>

struct Pipe { int start=-1, len=0, slot=0; bool alive=false; };

// Test whether rounded allocation slots can cluster lifetimes and reduce
// external fragmentation. Slot padding is a policy reservation only: it is
// never reported as pipe occupancy and is released together with its PID.
struct Allocator {
    int H=0, q=1;
    bool preserveTail=false;
    std::map<int,int> byStart; // start -> length of free allocation area
    std::map<int,std::set<int>> byLength;
    std::vector<Pipe> pipes{Pipe{}};
    int slot(int len) const { return ((len+q-1)/q)*q; }
    void erase(std::map<int,int>::iterator it) {
        byLength[it->second].erase(it->first);
        if(byLength[it->second].empty()) byLength.erase(it->second);
        byStart.erase(it);
    }
    void add(int s,int len) {
        if(len<=0) return;
        int e=s+len;
        auto it=byStart.lower_bound(s);
        if(it!=byStart.begin()) {
            auto p=std::prev(it);
            if(p->first+p->second==s) { s=p->first; len+=p->second; erase(p); }
        }
        it=byStart.lower_bound(e);
        if(it!=byStart.end() && it->first==e) { len+=it->second; erase(it); }
        byStart[s]=len;
        byLength[len].insert(s);
    }
    bool tail(int s) const {
        auto it=byStart.find(s);
        return it!=byStart.end() && s+it->second==H;
    }
    int choose(int need) const {
        for(auto it=byLength.lower_bound(need);it!=byLength.end();++it) {
            for(int s:it->second) if(!preserveTail || !tail(s)) return s;
        }
        return -1;
    }
    int place(int len) {
        int need=slot(len), s=choose(need);
        if(s>=0) {
            auto it=byStart.find(s); int oldLen=it->second; erase(it);
            add(s+need,oldLen-need);
            pipes.push_back({s,len,need,true});
            return s;
        }
        int old=H, tailStart=H;
        if(!byStart.empty()) {
            auto it=std::prev(byStart.end());
            if(it->first+it->second==H) { tailStart=it->first; erase(it); }
        }
        int extension=std::max(0,need-(old-tailStart));
        H+=((extension+19)/20)*20;
        add(tailStart+need,H-tailStart-need);
        pipes.push_back({tailStart,len,need,true});
        return tailStart;
    }
    void remove(int pid) {
        auto &p=pipes.at(pid);
        add(p.start,p.slot);
        p.alive=false;
    }
};

int main(int argc,char **argv) {
    if(argc<3) { std::cerr<<"usage: padded_sim quantum input... [--tail=preserve]\n"; return 2; }
    int q=std::stoi(argv[1]); bool preserve=false;
    std::vector<std::string> files;
    for(int i=2;i<argc;i++) { std::string s=argv[i]; if(s=="--tail=preserve") preserve=true; else files.push_back(s); }
    double score=0, weights=0;
    for(const auto &file:files) {
        std::ifstream in(file); double weight; int n; in>>weight>>n;
        Allocator a; a.q=q; a.preserveTail=preserve;
        int live=0, peak=0;
        for(int i=0,op;i<n;i++) {
            in>>op;
            if(op>0) { a.place(op); live+=op; peak=std::max(peak,live); }
            else if(op<0) { a.remove(-op); live-=a.pipes[-op].len; }
        }
        int lb=((peak+19)/20)*20;
        double kpi=double(live)/a.H;
        score+=weight*kpi; weights+=weight;
        std::cout<<file<<" weight="<<weight<<" alive="<<live<<" H="<<a.H<<" lb="<<lb
                 <<" gap="<<(a.H-lb)<<" KPI="<<std::setprecision(9)<<kpi<<"\n";
    }
    std::cout<<"weighted_score="<<std::setprecision(12)<<score<<" total_weight="<<weights<<"\n";
}
