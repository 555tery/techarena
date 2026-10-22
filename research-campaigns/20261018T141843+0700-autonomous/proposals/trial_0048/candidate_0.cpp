#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <iostream>
#include <iterator>
#include <map>
#include <set>
#include <utility>
#include <vector>
using I=std::int64_t;
struct EndpointEvidence{
    double sum=0,squared=0;
    void observe(double value){sum+=value;squared+=value*value;}
    int direction()const{
        // An evidence margin, not a statistical guarantee.
        double margin=2.0+2.0*std::sqrt(squared);
        if(sum>margin)return 1;
        if(sum<-margin)return -1;
        return 0;
    }
};
struct EndpointProbe{
    bool valid=false,high=false,youngerLeft=false;
    std::size_t pid=0;
    I residual=0;
    int key=0;
};
struct EndpointReplay{
    bool active=false,youngerLeft=false;
    int key=0;
    std::array<I,2> low{0,0};
    std::array<I,2> high{0,0};
    I lowServed=0,highServed=0;
};
static I consumeLocal(std::array<I,2>& space,I length){
    int best=-1;
    for(int j=0;j<2;++j){
        if(space[j]>=length&&(best<0||space[j]<space[best]))best=j;
    }
    if(best<0)return 0;
    space[best]-=length;
    return length;
}
int main(){
    std::ios::sync_with_stdio(false);std::cin.tie(nullptr);
    std::map<I,I> gaps;
    std::set<std::pair<I,I>> sizes;
    std::vector<std::pair<I,I>> pipes(1);
    std::vector<unsigned char> alive(1,0);
    std::map<I,std::size_t> occupied;
    std::array<EndpointEvidence,48> evidence{};
    EndpointProbe probe;
    EndpointReplay replay;
    bool deletionRun=false;
    I trench=0,command;
    auto finishReplay=[&](){
        if(!replay.active)return;
        I advantage=replay.highServed-replay.lowServed;
        if(!replay.youngerLeft)advantage=-advantage;
        double reward=std::clamp(static_cast<double>(advantage)/40.0,-1.0,1.0);
        evidence[replay.key].observe(reward);
        replay.active=false;
    };
    auto beginReplay=[&](){
        replay=EndpointReplay{};
        EndpointProbe old=probe;
        probe.valid=false;
        if(!old.valid||!alive[old.pid])return;
        auto p=pipes[old.pid];
        I leftFree=0,rightFree=0;
        auto it=gaps.lower_bound(p.first);
        if(it!=gaps.begin()){
            auto before=std::prev(it);
            if(before->second==p.first)leftFree=before->second-before->first;
        }
        it=gaps.find(p.first+p.second);
        if(it!=gaps.end())rightFree=it->second-it->first;
        // No insertion occurred between this probe and the deletion run.
        // Remove its original residual to recover both counterfactuals.
        I a=leftFree-(old.high?old.residual:0);
        I b=rightFree-(old.high?0:old.residual);
        if(a==b)return;
        replay.active=true;
        replay.youngerLeft=old.youngerLeft;
        replay.key=old.key;
        replay.low={a,b+old.residual};
        replay.high={a+old.residual,b};
    };
    auto erase=[&](std::map<I,I>::iterator p){sizes.erase({p->second-p->first,p->first});gaps.erase(p);};
    auto add=[&](I start,I end){
        if(start>=end)return;
        auto it=gaps.lower_bound(start);
        if(it!=gaps.begin()){
            auto prev=std::prev(it);
            if(prev->second==start){start=prev->first;erase(prev);}
        }
        it=gaps.lower_bound(start);
        if(it!=gaps.end()&&it->first==end){end=it->second;erase(it);}
        gaps[start]=end;sizes.insert({end-start,start});
    };
    while(std::cin>>command&&command){
        if(command<0){
            if(!deletionRun)finishReplay();
            deletionRun=true;
            auto pid=static_cast<std::size_t>(-command);
            auto p=pipes.at(pid);
            std::cout<<p.first<<'\n'<<std::flush;
            occupied.erase(p.first);
            alive[pid]=0;
            add(p.first,p.first+p.second);
            continue;
        }
        I length=command,digs=0,start=0;
        bool startsRun=deletionRun;
        if(startsRun)beginReplay();
        deletionRun=false;
        // Both local alternatives receive only requests already observed.
        if(replay.active){
            replay.lowServed+=consumeLocal(replay.low,length);
            replay.highServed+=consumeLocal(replay.high,length);
        }
        auto best=sizes.lower_bound({length,-1});
        if(best==sizes.end()){
            I tail=trench;
            if(!gaps.empty()&&std::prev(gaps.end())->second==trench)tail=std::prev(gaps.end())->first;
            digs=(length-(trench-tail)+19)/20;
            I old=trench;trench+=digs*20;add(old,trench);best=sizes.lower_bound({length,-1});
        }
        auto gap=gaps.find(best->second);
        I gapStart=gap->first,end=gap->second;
        I residual=end-gapStart-length;
        std::size_t pid=pipes.size();
        bool high=false;
        EndpointProbe nextProbe;
        if(residual>0&&residual<40){
            auto right=occupied.lower_bound(gapStart);
            if(right!=occupied.end()&&right!=occupied.begin()&&right->first==end){
                auto left=std::prev(right);
                std::size_t leftId=left->second,rightId=right->second;
                auto lp=pipes[leftId],rp=pipes[rightId];
                if(lp.first+lp.second==gapStart){
                    bool youngerLeft=leftId>rightId;
                    I youngAge=static_cast<I>(pid-std::max(leftId,rightId));
                    I oldAge=static_cast<I>(pid-std::min(leftId,rightId));
                    int ageBand=0;
                    while(ageBand<3&&oldAge>=2*youngAge){
                        oldAge/=2;
                        ++ageBand;
                    }
                    I leftRelease=lp.second,rightRelease=rp.second;
                    auto shoulder=gaps.lower_bound(lp.first);
                    if(shoulder!=gaps.begin()){
                        auto before=std::prev(shoulder);
                        if(before->second==lp.first)leftRelease+=before->second-before->first;
                    }
                    shoulder=gaps.find(rp.first+rp.second);
                    if(shoulder!=gaps.end())rightRelease+=shoulder->second-shoulder->first;
                    leftRelease=std::min<I>(40,leftRelease);
                    rightRelease=std::min<I>(40,rightRelease);
                    I youngRelease=youngerLeft?leftRelease:rightRelease;
                    I oldRelease=youngerLeft?rightRelease:leftRelease;
                    int shape=youngRelease<oldRelease?0:(youngRelease>oldRelease?2:1);
                    int key=(((ageBand*3+shape)*2+(residual>=length?1:0))*2)+(startsRun?1:0);
                    int preference=evidence[key].direction();
                    if(preference!=0)high=preference>0?youngerLeft:!youngerLeft;
                    nextProbe.valid=true;
                    nextProbe.high=high;
                    nextProbe.youngerLeft=youngerLeft;
                    nextProbe.pid=pid;
                    nextProbe.residual=residual;
                    nextProbe.key=key;
                }
            }
        }
        start=high?end-length:gapStart;
        erase(gap);
        add(gapStart,start);
        add(start+length,end);
        pipes.push_back({start,length});
        alive.push_back(1);
        occupied.emplace(start,pid);
        probe=nextProbe;
        std::cout<<digs<<' '<<start<<'\n'<<std::flush;
    }
}
