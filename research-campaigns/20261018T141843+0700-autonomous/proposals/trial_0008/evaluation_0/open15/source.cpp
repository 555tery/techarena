#include <algorithm>
#include <array>
#include <cstdint>
#include <cmath>
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
    constexpr int MaxLength=40;
    constexpr int ValueLimit=2*MaxLength;
    std::array<int,ValueLimit+2> gapCount{};
    std::array<int,MaxLength+1> recent{};
    std::array<int,2048> history{};
    std::array<double,ValueLimit+1> value{};
    std::size_t historyPos=0;
    int recentDeletes=0;
    I liveCount=0;
    std::uint64_t step=0,modelStep=0;
    bool modelDirty=true;
    constexpr int ReleaseAgeBands=16;
    struct ReleaseStats { int observed=0,useful=0; };
    std::vector<ReleaseStats> releaseStats(
        (MaxLength+1)*(MaxLength+1)*ReleaseAgeBands);
    std::map<I,int> occupied;
    std::vector<std::uint64_t> born(1,0);
    struct PendingSide {
        int pid=0,cell=-1;
        bool deleted=false;
    };
    std::array<PendingSide,2> pending{};
    int pendingNew=0;
    bool pendingNewDeleted=false;
    auto releaseCell=[&](int pid,int request){
        std::uint64_t age=step-born[static_cast<std::size_t>(pid)];
        int band=0;
        while(age>=4&&band+1<ReleaseAgeBands){age/=4;++band;}
        int neighbour=static_cast<int>(pipes[static_cast<std::size_t>(pid)].second);
        return (request*(MaxLength+1)+neighbour)*ReleaseAgeBands+band;
    };
    // Complete both endpoint observations at the next insertion.
    auto closeInterval=[&](){
        for(auto &probe:pending){
            if(probe.cell<0)continue;
            auto &stats=releaseStats[static_cast<std::size_t>(probe.cell)];
            ++stats.observed;
            if(probe.deleted&&!pendingNewDeleted)++stats.useful;
            probe=PendingSide{};
        }
        pendingNew=0;
        pendingNewDeleted=false;
    };
    auto releaseBounds=[&](int cell){
        const auto &stats=releaseStats[static_cast<std::size_t>(cell)];
        if(stats.observed==0)return std::pair<double,double>{0.0,1.0};
        double n=stats.observed;
        double p=double(stats.useful)/n;
        double denominator=1.0+4.0/n;
        double center=(p+2.0/n)/denominator;
        double radius=2.0*std::sqrt(p*(1.0-p)/n+1.0/(n*n))/denominator;
        return std::pair<double,double>{
            std::max(0.0,center-radius),std::min(1.0,center+radius)};
    };
    auto observe=[&](int event){
        int old=history[historyPos];
        if(old>0){
            if(--recent[old]==0)modelDirty=true;
        }else if(old<0){
            if(--recentDeletes==0)modelDirty=true;
        }
        history[historyPos]=event;
        historyPos=(historyPos+1)%history.size();
        if(event>0){
            if(recent[event]++==0)modelDirty=true;
        }else{
            if(recentDeletes++==0)modelDirty=true;
        }
        ++step;
    };
    auto rebuildValue=[&](){
        std::array<double,MaxLength+1> rate{};
        I fitting=gapCount[ValueLimit+1];
        for(int g=ValueLimit;g>=1;--g){
            fitting+=gapCount[g];
            if(g<=MaxLength)
                rate[g]=double(recent[g])/double(std::max<I>(1,fitting));
        }
        double expiry=2.0*recentDeletes/double(std::max<I>(1,liveCount));
        value.fill(0.0);
        for(int g=1;g<=ValueLimit;++g){
            int top=std::min(g,MaxLength);
            if(expiry==0.0){
                for(int s=1;s<=top;++s)
                    if(rate[s]>0.0)
                        value[g]=std::max(value[g],double(s)+value[g-s]);
                continue;
            }
            std::array<double,MaxLength+1> reward{};
            std::uint64_t active=0;
            double numerator=0.0,denominator=expiry;
            for(int s=1;s<=top;++s){
                if(rate[s]==0.0)continue;
                reward[s]=double(s)+value[g-s];
                numerator+=rate[s]*reward[s];
                denominator+=rate[s];
                active|=std::uint64_t(1)<<s;
            }
            double estimate=numerator/denominator;
            for(;;){
                bool removed=false;
                for(int s=1;s<=top;++s){
                    std::uint64_t bit=std::uint64_t(1)<<s;
                    if((active&bit)&&reward[s]<estimate){
                        numerator-=rate[s]*reward[s];
                        denominator-=rate[s];
                        active&=~bit;
                        removed=true;
                    }
                }
                if(!removed)break;
                estimate=numerator/denominator;
            }
            value[g]=std::clamp(estimate,0.0,double(g));
        }
        modelStep=step;
        modelDirty=false;
    };
    auto erase=[&](std::map<I,I>::iterator p){
        I length=p->second-p->first;
        --gapCount[static_cast<std::size_t>(std::min<I>(ValueLimit+1,length))];
        sizes.erase({length,p->first});gaps.erase(p);
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
        ++gapCount[static_cast<std::size_t>(std::min<I>(ValueLimit+1,end-start))];
    };
    while(std::cin>>command&&command){
        observe(command>0?static_cast<int>(command):-1);
        if(command<0){
            int pid=static_cast<int>(-command);
            auto p=pipes.at(static_cast<std::size_t>(pid));
            std::cout<<p.first<<'\n'<<std::flush;
            if(pid==pendingNew)pendingNewDeleted=true;
            for(auto &probe:pending)
                if(probe.cell>=0&&probe.pid==pid)probe.deleted=true;
            occupied.erase(p.first);
            add(p.first,p.first+p.second);
            --liveCount;
            continue;
        }
        closeInterval();
        I length=command,digs=0,start=0;
        auto best=sizes.lower_bound({length,-1});
        if(best==sizes.end()){
            I tail=trench;
            if(!gaps.empty()&&std::prev(gaps.end())->second==trench)tail=std::prev(gaps.end())->first;
            digs=(length-(trench-tail)+19)/20;
            I old=trench;trench+=digs*20;add(old,trench);best=sizes.lower_bound({length,-1});
        }
        if(best->first>length&&best->first<=ValueLimit){
            if(modelDirty||step-modelStep>=64)rebuildValue();
            int chosen=static_cast<int>(best->first);
            int request=static_cast<int>(length);
            double loss=value[chosen]-value[chosen-request];
            for(int g=chosen+1;g<=ValueLimit;++g){
                if(gapCount[g]==0)continue;
                double candidate=value[g]-value[g-request];
                if(candidate+1e-9<loss){
                    loss=candidate;
                    chosen=g;
                }
            }
            if(chosen!=best->first)best=sizes.lower_bound({chosen,-1});
        }
        auto gap=gaps.find(best->second);
        I begin=gap->first,end=gap->second;
        I remainder=end-begin-length;
        int left=0,right=0,leftCell=-1,rightCell=-1;
        bool takeHigh=false;
        if(remainder>0&&end-begin<=ValueLimit){
            auto rightPipe=occupied.find(end);
            if(rightPipe!=occupied.end())right=rightPipe->second;
            auto leftPipe=occupied.lower_bound(begin);
            if(leftPipe!=occupied.begin()){
                --leftPipe;
                const auto &p=pipes[static_cast<std::size_t>(leftPipe->second)];
                if(p.first+p.second==begin)left=leftPipe->second;
            }
            if(left&&right){
                leftCell=releaseCell(left,static_cast<int>(length));
                rightCell=releaseCell(right,static_cast<int>(length));
                const auto &lp=pipes[static_cast<std::size_t>(left)];
                const auto &rp=pipes[static_cast<std::size_t>(right)];
                I leftFree=lp.second,rightFree=rp.second;
                auto outerLeft=gaps.lower_bound(lp.first);
                if(outerLeft!=gaps.begin()){
                    --outerLeft;
                    if(outerLeft->second==lp.first)
                        leftFree+=outerLeft->second-outerLeft->first;
                }
                auto outerRight=gaps.find(rp.first+rp.second);
                if(outerRight!=gaps.end())
                    rightFree+=outerRight->second-outerRight->first;
                // Use only capacities covered by the existing value DP.
                if(leftFree+remainder<=ValueLimit&&
                   rightFree+remainder<=ValueLimit){
                    double residualValue=value[static_cast<std::size_t>(remainder)];
                    double leftGain=std::max(0.0,
                        value[static_cast<std::size_t>(leftFree+remainder)]-
                        value[static_cast<std::size_t>(leftFree)]-residualValue);
                    double rightGain=std::max(0.0,
                        value[static_cast<std::size_t>(rightFree+remainder)]-
                        value[static_cast<std::size_t>(rightFree)]-residualValue);
                    auto leftBounds=releaseBounds(leftCell);
                    auto rightBounds=releaseBounds(rightCell);
                    takeHigh=leftGain*leftBounds.first>
                             rightGain*rightBounds.second+1e-9;
                }
            }
        }
        erase(gap);
        start=takeHigh?end-length:begin;
        add(begin,start);
        add(start+length,end);
        ++liveCount;
        int pid=static_cast<int>(pipes.size());
        pipes.push_back({start,length});
        born.push_back(step);
        occupied.emplace(start,pid);
        if(leftCell>=0&&rightCell>=0){
            pending[0]=PendingSide{left,leftCell,false};
            pending[1]=PendingSide{right,rightCell,false};
            pendingNew=pid;
            pendingNewDeleted=false;
        }
        std::cout<<digs<<' '<<start<<'\n'<<std::flush;
    }
}
