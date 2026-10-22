#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <iterator>
#include <iostream>
#include <map>
#include <set>
#include <utility>
#include <vector>
using I=std::int64_t;
constexpr int kMaxLength=40;
constexpr int kPairLimit=2*kMaxLength;
using CarryMasks=std::array<std::array<std::uint64_t,kMaxLength+1>,kPairLimit>;

CarryMasks makeCarryMasks(){
    CarryMasks masks{};
    // Arithmetic capacity table, independent of the input stream.
    // For end>=length, the extra multiple crossed when removing length is
    // [end%s < length%s], after cancelling floor(length/s).
    for(std::size_t end=1;end<masks.size();++end){
        for(std::size_t length=1;length<masks[end].size()&&length<=end;++length){
            for(std::size_t size=1;size<=static_cast<std::size_t>(kMaxLength);++size){
                if(end%size<length%size){
                    masks[end][length]|=std::uint64_t{1}<<(size-1);
                }
            }
        }
    }
    return masks;
}

bool strictlyDominatesPairs(I g,I h,I length){
    // Preconditions: length<=g<h. Compare A=(g-length,h) with B=(g,h-length).
    const I a=g-length;
    const I b=h;
    const I u=std::min(g,h-length);
    const I v=std::max(g,h-length);

    // B must retain every legal singleton that A can hold.
    if(v<kMaxLength)return false;

    // Any pair separated by A also fits B, since a<=u and v>=40.
    // A lost pair must have both items >u and a sum in (v,b].
    if(u<kMaxLength){
        const I smallestLostSum=std::max(2*(u+1),v+1);
        const I largestOldSum=std::min<I>(kPairLimit,b);
        if(smallestLostSum<=largestOldSum)return false;
    }

    // This pair is separated by B but cannot fit either way in A.
    const I witnessSmall=std::min<I>(u,kMaxLength);
    return witnessSmall>a&&witnessSmall+kMaxLength>b;
}

int main(){
    std::ios::sync_with_stdio(false);std::cin.tie(nullptr);
    std::map<I,I> gaps;
    std::set<std::pair<I,I>> sizes;
    std::vector<std::pair<I,I>> pipes(1);
    I trench=0,command;
    const CarryMasks carryMasks=makeCarryMasks();
    std::array<int,kPairLimit> shortGapCounts{};
    std::uint64_t observedOperations=0,capacityComparisons=0,pairCertificates=0;
    std::uint64_t homogeneousVetoes=0,certifiedSteps=0,changedPlacements=0;
    std::uint64_t firstChangedEvent=0;
    auto erase=[&](std::map<I,I>::iterator p){
        const I gapLength=p->second-p->first;
        if(gapLength<kPairLimit){
            --shortGapCounts[static_cast<std::size_t>(gapLength)];
        }
        sizes.erase({gapLength,p->first});gaps.erase(p);
    };
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
        if(end-start<kPairLimit){
            ++shortGapCounts[static_cast<std::size_t>(end-start)];
        }
    };
    while(std::cin>>command&&command){
        ++observedOperations;
        if(command<0){auto p=pipes.at(static_cast<std::size_t>(-command));std::cout<<p.first<<'\n'<<std::flush;add(p.first,p.first+p.second);continue;}
        I length=command,digs=0,start=0;
        auto best=sizes.lower_bound({length,-1});
        if(best==sizes.end()){
            I tail=trench;
            if(!gaps.empty()&&std::prev(gaps.end())->second==trench)tail=std::prev(gaps.end())->first;
            digs=(length-(trench-tail)+19)/20;
            I old=trench;trench+=digs*20;add(old,trench);best=sizes.lower_bound({length,-1});
        }
        if(best->first>length&&best->first<kPairLimit){
            const I originalLength=best->first;
            I selectedLength=originalLength;
            const std::size_t lengthIndex=static_cast<std::size_t>(length);
            // If h>=80, its original span already holds every legal pair;
            // strict pair improvement is therefore impossible.
            for(I other=selectedLength+1;other<kPairLimit;++other){
                const std::size_t otherIndex=static_cast<std::size_t>(other);
                if(shortGapCounts[otherIndex]==0)continue;
                ++capacityComparisons;
                if(!strictlyDominatesPairs(selectedLength,other,length))continue;
                ++pairCertificates;
                const std::uint64_t gained=carryMasks[
                    static_cast<std::size_t>(selectedLength)][lengthIndex];
                const std::uint64_t lost=carryMasks[otherIndex][lengthIndex];
                // Preserve sum floor(gap/s) for every legal homogeneous size.
                if((lost&~gained)!=0){
                    ++homogeneousVetoes;
                    continue;
                }
                selectedLength=other;
                ++certifiedSteps;
            }
            if(selectedLength!=originalLength){
                best=sizes.lower_bound({selectedLength,-1});
                ++changedPlacements;
                if(firstChangedEvent==0)firstChangedEvent=observedOperations;
            }
        }
        auto gap=gaps.find(best->second);start=gap->first;I end=gap->second;erase(gap);add(start+length,end);
        pipes.push_back({start,length});std::cout<<digs<<' '<<start<<'\n'<<std::flush;
    }
    std::cerr<<"complement_probes="<<capacityComparisons
             <<" pair_certificates="<<pairCertificates
             <<" homogeneous_vetoes="<<homogeneousVetoes
             <<" certified_steps="<<certifiedSteps
             <<" changed="<<changedPlacements
             <<" first_changed_event="<<firstChangedEvent
             <<" final_trench="<<trench<<'\n';
}
