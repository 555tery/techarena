#include <algorithm>
#include <array>
#include <cstdint>
#include <iostream>
#include <iterator>
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
    struct Footprint { int length; int returns; };
    std::vector<int> pipeReturns(1,0);
    std::map<I,Footprint> footprints;
    std::array<std::set<std::pair<int,I>>,41> ready;
    I promoted=0,opportunities=0,changed=0,interior=0,overwritten=0;
    auto footprintKey=[](I start,const Footprint& fp){
        return std::pair<int,I>{-fp.returns,start};
    };
    auto forgetFootprint=[&](std::map<I,Footprint>::iterator it){
        const auto& fp=it->second;
        if(fp.returns>=2)ready[fp.length].erase(footprintKey(it->first,fp));
        footprints.erase(it);
    };
    auto consumeFootprints=[&](I start,I end){
        int inherited=0;
        auto it=footprints.lower_bound(start);
        if(it!=footprints.begin()){
            auto prev=std::prev(it);
            if(prev->first+prev->second.length>start)it=prev;
        }
        while(it!=footprints.end()&&it->first<end){
            auto current=it++;
            if(current->first==start&&current->first+current->second.length==end)
                inherited=current->second.returns;
            else
                ++overwritten;
            forgetFootprint(current);
        }
        return inherited;
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
            const auto pid=static_cast<std::size_t>(-command);
            const auto p=pipes.at(pid);
            std::cout<<p.first<<'\n'<<std::flush;
            add(p.first,p.first+p.second);
            Footprint fp{static_cast<int>(p.second),pipeReturns.at(pid)+1};
            footprints.emplace(p.first,fp);
            if(fp.returns>=2){
                ready[fp.length].insert(footprintKey(p.first,fp));
                if(fp.returns==2)++promoted;
            }
            continue;
        }
        I length=command,digs=0,start=0;
        auto best=sizes.lower_bound({length,-1});
        if(best==sizes.end()){
            I tail=trench;
            if(!gaps.empty()&&std::prev(gaps.end())->second==trench)tail=std::prev(gaps.end())->first;
            digs=(length-(trench-tail)+19)/20;
            I old=trench;trench+=digs*20;add(old,trench);best=sizes.lower_bound({length,-1});
        }
        auto gap=gaps.find(best->second);
        const I bestStart=gap->first;
        start=bestStart;
        if(best->first>length){
            const auto& candidates=ready[static_cast<std::size_t>(length)];
            if(!candidates.empty()){
                const I candidate=candidates.begin()->second;
                auto owner=gaps.upper_bound(candidate);
                if(owner!=gaps.begin()){
                    --owner;
                    if(owner->first<=candidate&&candidate+length<=owner->second){
                        ++opportunities;
                        gap=owner;
                        start=candidate;
                    }
                }
            }
        }
        const I begin=gap->first,end=gap->second;
        if(start!=bestStart){
            ++changed;
            if(begin<start&&start+length<end)++interior;
        }
        const int inherited=consumeFootprints(start,start+length);
        erase(gap);
        add(begin,start);
        add(start+length,end);
        pipes.push_back({start,length});
        pipeReturns.push_back(inherited);
        std::cout<<digs<<' '<<start<<'\n'<<std::flush;
    }
#ifdef ALLOCATOR_DIAGNOSTICS
    std::cerr<<"promotions="<<promoted
             <<" opportunities="<<opportunities
             <<" changed="<<changed
             <<" interior="<<interior
             <<" overwritten="<<overwritten<<'\n';
#endif
}
