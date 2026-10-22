#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <iterator>
#include <iostream>
#include <map>
#include <set>
#include <utility>
#include <vector>
using I=std::int64_t;
int main(){
    std::ios::sync_with_stdio(false);std::cin.tie(nullptr);
    std::map<I,I> gaps;
    std::set<std::pair<I,I>> sizes;
    std::vector<std::pair<I,I>> pipes(1);
    I trench=0,command;
    struct Race{int key,newcomer,older;bool done;};
    struct Watch{int race,next;};
    std::map<I,int> occupied;
    std::vector<Race> races;
    std::vector<Watch> watches;
    std::vector<int> heads(1,-1),bit(1,0);
    std::array<std::array<std::uint32_t,3>,432> outcomes{};
    std::array<std::uint32_t,41> demand{};
    std::uint32_t demandTotal=0;
    int liveCount=0;
    const double confidenceLog=std::log(200.0);
    auto prefixLive=[&](int id){
        int result=0;
        for(;id>0;id-=id&-id)result+=bit[id];
        return result;
    };
    auto relation=[](I a,I b){return a<b?0:(a==b?1:2);};
    auto watch=[&](int pid,int race){
        watches.push_back({race,heads[pid]});
        heads[pid]=static_cast<int>(watches.size())-1;
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
            int pid=static_cast<int>(-command);
            auto p=pipes.at(static_cast<std::size_t>(pid));
            std::cout<<p.first<<'\n'<<std::flush;
            for(int edge=heads[pid];edge!=-1;edge=watches[edge].next){
                auto& race=races[watches[edge].race];
                if(race.done)continue;
                int outcome=pid==race.newcomer?2:(pid==race.older?0:1);
                ++outcomes[race.key][outcome];
                race.done=true;
            }
            heads[pid]=-1;
            occupied.erase(p.first);
            for(int i=pid;i<static_cast<int>(bit.size());i+=i&-i)--bit[i];
            --liveCount;
            add(p.first,p.first+p.second);
            continue;
        }
        I length=command,digs=0,start=0;
        ++demand[static_cast<std::size_t>(length)];
        ++demandTotal;
        auto best=sizes.lower_bound({length,-1});
        if(best==sizes.end()){
            I tail=trench;
            if(!gaps.empty()&&std::prev(gaps.end())->second==trench)tail=std::prev(gaps.end())->first;
            digs=(length-(trench-tail)+19)/20;
            I old=trench;trench+=digs*20;add(old,trench);best=sizes.lower_bound({length,-1});
        }
        auto gap=gaps.find(best->second);
        start=gap->first;
        I end=gap->second,remainder=end-start-length;
        int key=-1,older=0,younger=0;
        bool highEdge=false;
        auto right=occupied.find(end);
        auto left=occupied.lower_bound(start);
        if(right!=occupied.end()&&left!=occupied.begin()){
            --left;
            int leftPid=left->second,rightPid=right->second;
            if(left->first+pipes[leftPid].second==start){
                older=std::min(leftPid,rightPid);
                younger=std::max(leftPid,rightPid);
                int oldQuartile=4*(prefixLive(older)-1)/liveCount;
                int youngQuartile=4*(prefixLive(younger)-1)/liveCount;
                int shape=9*relation(length,pipes[older].second)
                         +3*relation(length,pipes[younger].second)
                         +relation(pipes[older].second,pipes[younger].second);
                key=16*shape+4*oldQuartile+youngQuartile;
                const auto& count=outcomes[key];
                double n=static_cast<double>(count[0])+count[1]+count[2];
                if(remainder>0&&n>=2.0){
                    auto dividend=[&](I neighborLength){
                        double value=0.0;
                        for(int k=1;k<=40;++k){
                            if(!demand[k])continue;
                            I extra=(remainder+neighborLength)/k
                                   -remainder/k-neighborLength/k;
                            value+=static_cast<double>(demand[k])*k*extra;
                        }
                        return value/static_cast<double>(demandTotal);
                    };
                    double leftGain=dividend(pipes[leftPid].second);
                    double rightGain=dividend(pipes[rightPid].second);
                    double leftWins=count[leftPid==older?0:1];
                    double rightWins=count[rightPid==older?0:1];
                    // High placement leaves the remainder beside the left pipe.
                    // A newcomer-first outcome contributes zero to the difference.
                    double mean=(leftWins*leftGain-rightWins*rightGain)/n;
                    double variance=std::max(0.0,
                        (leftWins*leftGain*leftGain
                         +rightWins*rightGain*rightGain-n*mean*mean)/(n-1.0));
                    // A confidence filter, not a guarantee under arbitrary drift.
                    double radius=std::sqrt(2.0*variance*confidenceLog/n)
                        +7.0*(leftGain+rightGain)*confidenceLog/(3.0*(n-1.0));
                    highEdge=mean>radius;
                }
            }
        }
        I gapStart=start;
        erase(gap);
        if(highEdge){start=end-length;add(gapStart,start);}
        else add(start+length,end);
        int pid=static_cast<int>(pipes.size());
        pipes.push_back({start,length});
        heads.push_back(-1);
        // Append a Fenwick node including all earlier live entries in its range.
        int bitId=static_cast<int>(bit.size());
        int nodeValue=1+prefixLive(bitId-1)-prefixLive(bitId-(bitId&-bitId));
        bit.push_back(nodeValue);
        ++liveCount;
        occupied.emplace(start,pid);
        if(key>=0){
            // Exact fits also provide observations although their edge is fixed.
            int race=static_cast<int>(races.size());
            races.push_back({key,pid,older,false});
            watch(pid,race);watch(older,race);watch(younger,race);
        }
        std::cout<<digs<<' '<<start<<'\n'<<std::flush;
    }
}
