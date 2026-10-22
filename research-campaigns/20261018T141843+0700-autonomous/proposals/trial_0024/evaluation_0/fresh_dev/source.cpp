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
int main(){
    std::ios::sync_with_stdio(false);std::cin.tie(nullptr);
    std::map<I,I> gaps;
    std::set<std::pair<I,I>> sizes;
    std::vector<std::pair<I,I>> pipes(1);
    I trench=0,command;
    constexpr int maxLength=40;
    constexpr int modelCapacity=2*maxLength;
    constexpr int trackedCapacity=modelCapacity+maxLength;
    constexpr std::size_t historyCapacity=1024;
    std::array<int,trackedCapacity+2> gapCounts{};
    std::array<int,maxLength+1> arrivals{};
    std::array<int,historyCapacity> history{};
    std::array<double,modelCapacity+1> value{};
    std::size_t historyCount=0,historyHead=0;
    int recentDeletes=0,liveCount=0;
    std::uint64_t operations=0,lastBuild=0;
    std::uint64_t choices=0,changed=0,builds=0;
    double predictedSaved=0.0;
    bool haveModel=false;
    auto bucket=[&](I capacity){
        return static_cast<std::size_t>(std::min<I>(capacity,trackedCapacity+1));
    };
    auto erase=[&](std::map<I,I>::iterator p){
        --gapCounts[bucket(p->second-p->first)];
        sizes.erase({p->second-p->first,p->first});
        gaps.erase(p);
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
        ++gapCounts[bucket(end-start)];
    };
    auto observe=[&](I request){
        ++operations;
        if(historyCount==historyCapacity){
            int old=history[historyHead];
            if(old) --arrivals[old];
            else --recentDeletes;
        }else ++historyCount;
        int item=request>0?static_cast<int>(request):0;
        history[historyHead]=item;
        historyHead=(historyHead+1)%historyCapacity;
        if(item) ++arrivals[item];
        else ++recentDeletes;
    };
    auto rebuild=[&](){
        std::array<double,maxLength+1> rate{};
        int fitting=0;
        for(int s=trackedCapacity+1;s>=1;--s){
            fitting+=gapCounts[s];
            if(s<=maxLength)
                rate[s]=(arrivals[s]+0.5)/std::max(1,fitting);
        }
        const double expiry=2.0*(recentDeletes+0.5)/std::max(1,liveCount);
        std::array<std::pair<double,double>,maxLength> offers{};
        value[0]=0.0;
        for(int capacity=1;capacity<=modelCapacity;++capacity){
            int count=std::min(capacity,maxLength);
            for(int length=1;length<=count;++length)
                offers[length-1]={length+value[capacity-length],rate[length]};
            std::sort(offers.begin(),offers.begin()+count,
                [](const auto& a,const auto& b){return a.first>b.first;});
            double numerator=0.0,denominator=expiry;
            // Descending offers give the exact Bellman acceptance threshold.
            for(int j=0;j<count;++j){
                if(offers[j].first*denominator<=numerator) break;
                numerator+=offers[j].second*offers[j].first;
                denominator+=offers[j].second;
            }
            value[capacity]=numerator/denominator;
        }
        lastBuild=operations;
        haveModel=true;
        ++builds;
    };
    auto gapValue=[&](I capacity)->double{
        if(capacity<=modelCapacity)
            return value[static_cast<std::size_t>(capacity)];
        return value[modelCapacity]+static_cast<double>(capacity-modelCapacity);
    };
    while(std::cin>>command&&command){
        observe(command);
        if(command<0){auto p=pipes.at(static_cast<std::size_t>(-command));std::cout<<p.first<<'\n'<<std::flush;add(p.first,p.first+p.second);--liveCount;continue;}
        I length=command,digs=0,start=0;
        auto best=sizes.lower_bound({length,-1});
        if(best==sizes.end()){
            I tail=trench;
            if(!gaps.empty()&&std::prev(gaps.end())->second==trench)tail=std::prev(gaps.end())->first;
            digs=(length-(trench-tail)+19)/20;
            I old=trench;trench+=digs*20;add(old,trench);best=sizes.lower_bound({length,-1});
        }
        if(!haveModel||operations-lastBuild>=64) rebuild();
        const I bestFitWidth=best->first;
        I selectedWidth=bestFitWidth;
        const double originalCost=gapValue(bestFitWidth)-gapValue(bestFitWidth-length);
        double selectedCost=originalCost;
        constexpr double tolerance=1e-9;
        for(int s=static_cast<int>(length);s<=trackedCapacity;++s){
            if(!gapCounts[s]) continue;
            double cost=gapValue(s)-gapValue(s-length);
            if(cost+tolerance<selectedCost){
                selectedCost=cost;
                selectedWidth=s;
            }
        }
        // All larger gaps have the same marginal value under linear continuation.
        if(gapCounts[trackedCapacity+1]>0&&
           static_cast<double>(length)+tolerance<selectedCost){
            best=sizes.lower_bound({trackedCapacity+1,-1});
            selectedCost=static_cast<double>(length);
        }else if(selectedWidth!=bestFitWidth){
            best=sizes.lower_bound({selectedWidth,-1});
        }
        ++choices;
        if(best->first!=bestFitWidth){
            ++changed;
            predictedSaved+=originalCost-selectedCost;
        }
        auto gap=gaps.find(best->second);start=gap->first;I end=gap->second;erase(gap);add(start+length,end);
        pipes.push_back({start,length});++liveCount;std::cout<<digs<<' '<<start<<'\n'<<std::flush;
    }
#ifdef PACKING_DIAGNOSTICS
    std::cerr<<"packing choices="<<choices
             <<" changed_from_best_fit="<<changed
             <<" model_builds="<<builds
             <<" predicted_opportunity_saved="<<predictedSaved<<'\n';
#endif
}
