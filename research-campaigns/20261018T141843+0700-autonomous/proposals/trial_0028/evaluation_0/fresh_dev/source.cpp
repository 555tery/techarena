#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <cmath>
#include <iterator>
#include <iostream>
#include <map>
#include <set>
#include <utility>
#include <vector>
using I=std::int64_t;

class CoalescenceLifetime {
    static constexpr std::array<std::uint64_t,8> lower_{
        0,16,64,256,1024,4096,16384,65536};
    static constexpr std::size_t bands_=lower_.size();
    struct Record {
        std::uint64_t born=0;
        int length=0;
        bool active=false;
    };
    struct Cell {
        std::uint64_t completedExposure=0;
        std::uint64_t birthSum=0;
        std::uint64_t active=0;
        std::uint64_t deaths=0;
    };
    struct Rate {
        double mean=0.0;
        double error=0.0;
    };
    std::vector<Record> records_{Record{}};
    std::array<std::array<Cell,bands_>,41> cells_{};
    std::array<std::array<Rate,bands_>,41> rates_{};
    std::array<std::size_t,bands_> crossing_{};
    std::uint64_t clock_=0,deaths_=0;
    bool ready_=false;

    static std::size_t band(std::uint64_t age){
        std::size_t result=0;
        while(result+1<bands_&&age>=lower_[result+1]) ++result;
        return result;
    }
    void enter(const Record& record,std::size_t b){
        auto& cell=cells_[static_cast<std::size_t>(record.length)][b];
        ++cell.active;
        cell.birthSum+=record.born;
    }
    void leave(const Record& record,std::size_t b,std::uint64_t age){
        auto& cell=cells_[static_cast<std::size_t>(record.length)][b];
        cell.completedExposure+=age-lower_[b];
        --cell.active;
        cell.birthSum-=record.born;
    }
    std::uint64_t exposure(const Cell& cell,std::size_t b) const {
        const std::uint64_t outstanding=cell.active==0?0:
            cell.active*(clock_-lower_[b])-cell.birthSum;
        return cell.completedExposure+outstanding;
    }

public:
    struct RaceBounds {
        double leftLower=0.0;
        double rightUpper=0.0;
    };
    CoalescenceLifetime(){crossing_.fill(1);}
    bool ready() const {return ready_;}

    void advance(){
        ++clock_;
        // Birth order permits one monotone cursor per age landmark.
        for(std::size_t b=1;b<bands_;++b){
            auto& cursor=crossing_[b];
            while(cursor<records_.size()&&
                  clock_-records_[cursor].born>=lower_[b]){
                const Record& record=records_[cursor++];
                if(!record.active) continue;
                leave(record,b-1,lower_[b]);
                enter(record,b);
            }
        }
    }
    void birth(int length){
        records_.push_back(Record{clock_,length,true});
        enter(records_.back(),0);
    }
    void death(std::size_t pid){
        Record& record=records_[pid];
        const std::uint64_t age=clock_-record.born;
        leave(record,band(age),age);
        // An event exactly at a landmark ends the preceding interval.
        ++cells_[static_cast<std::size_t>(record.length)]
                [band(age==0?0:age-1)].deaths;
        record.active=false;
        ++deaths_;
    }
    void fit(double priorHazard){
        ready_=deaths_>0&&priorHazard>0.0;
        if(!ready_) return;
        constexpr double priorEvents=8.0;
        for(std::size_t b=0;b<bands_;++b){
            double pooledExposure=0.0,pooledDeaths=0.0;
            for(std::size_t length=1;length<=40;++length){
                pooledExposure+=static_cast<double>(exposure(cells_[length][b],b));
                pooledDeaths+=static_cast<double>(cells_[length][b].deaths);
            }
            const double pooledDenominator=pooledExposure+priorEvents/priorHazard;
            const double pooledRate=(pooledDeaths+priorEvents)/pooledDenominator;
            const double pooledError=std::sqrt(pooledDeaths+priorEvents)/pooledDenominator;
            for(std::size_t length=1;length<=40;++length){
                const auto& cell=cells_[length][b];
                const double borrowedExposure=priorEvents/pooledRate;
                const double denominator=static_cast<double>(exposure(cell,b))+
                    borrowedExposure;
                const double shape=static_cast<double>(cell.deaths)+priorEvents;
                rates_[length][b]=Rate{
                    shape/denominator,
                    std::sqrt(shape)/denominator+
                        borrowedExposure/denominator*pooledError};
            }
        }
    }

    RaceBounds race(std::size_t leftPid,std::size_t rightPid,int newLength,
                    double fillRate,std::uint64_t horizon) const {
        const Record& left=records_[leftPid];
        const Record& right=records_[rightPid];
        const std::uint64_t leftAge=clock_-left.born;
        const std::uint64_t rightAge=clock_-right.born;
        RaceBounds result;
        double leftSurvival=1.0,rightSurvival=1.0;
        const auto interval=[](const Rate& rate){
            return std::pair<double,double>{
                std::max(0.0,rate.mean-2.0*rate.error),
                rate.mean+2.0*rate.error};
        };
        for(std::uint64_t elapsed=0;elapsed<horizon;){
            const std::uint64_t la=leftAge+elapsed,ra=rightAge+elapsed;
            const std::size_t lb=band(la),rb=band(ra),nb=band(elapsed);
            std::uint64_t width=horizon-elapsed;
            const auto shorten=[&](std::uint64_t age,std::size_t b){
                if(b+1<bands_) width=std::min(width,lower_[b+1]-age);
            };
            shorten(la,lb);
            shorten(ra,rb);
            shorten(elapsed,nb);
            const auto l=interval(rates_[static_cast<std::size_t>(left.length)][lb]);
            const auto r=interval(rates_[static_cast<std::size_t>(right.length)][rb]);
            const auto n=interval(rates_[static_cast<std::size_t>(newLength)][nb]);
            // Lower left-event probability: slow left, fast competitors.
            const double leftTotal=l.first+r.second+n.second+fillRate;
            if(leftTotal>0.0){
                const double event=-std::expm1(-leftTotal*static_cast<double>(width));
                result.leftLower+=leftSurvival*(l.first/leftTotal)*event;
                leftSurvival*=1.0-event;
            }
            // Upper right-event probability: fast right, slow competitors.
            const double rightTotal=l.first+r.second+n.first+fillRate;
            if(rightTotal>0.0){
                const double event=-std::expm1(-rightTotal*static_cast<double>(width));
                result.rightUpper+=rightSurvival*(r.second/rightTotal)*event;
                rightSurvival*=1.0-event;
            }
            elapsed+=width;
        }
        return result;
    }
};

int main(){
    std::ios::sync_with_stdio(false);std::cin.tie(nullptr);
    std::map<I,I> gaps;
    std::set<std::pair<I,I>> sizes;
    std::vector<std::pair<I,I>> pipes(1);
    std::map<I,std::size_t> liveByStart;
    CoalescenceLifetime lifetime;
    I trench=0,command;
    constexpr int maxLength=40;
    constexpr int modelCapacity=2*maxLength;
    constexpr int trackedCapacity=modelCapacity+maxLength;
    constexpr std::size_t historyCapacity=1024;
    std::array<int,trackedCapacity+2> gapCounts{};
    std::array<int,maxLength+1> arrivals{};
    std::array<int,historyCapacity> history{};
    std::array<double,modelCapacity+1> value{};
    std::array<double,maxLength+1> perGapArrivalRate{};
    std::size_t historyCount=0,historyHead=0;
    int recentDeletes=0,liveCount=0;
    std::uint64_t operations=0,lastBuild=0;
    std::uint64_t choices=0,changed=0,builds=0;
    std::uint64_t endpointCandidates=0,endpointForecasts=0;
    std::uint64_t endpointPositiveSurplus=0,endpointHighOverrides=0;
    double endpointGuardedCredit=0.0;
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
        lifetime.advance();
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
            if(s<=maxLength){
                rate[s]=(arrivals[s]+0.5)/std::max(1,fitting);
                perGapArrivalRate[s]=rate[s]/
                    static_cast<double>(std::max<std::size_t>(1,historyCount));
            }
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
        lifetime.fit((recentDeletes+0.5)/
            (static_cast<double>(std::max<std::size_t>(1,historyCount))*
             static_cast<double>(std::max(1,liveCount))));
        lastBuild=operations;
        haveModel=true;
        ++builds;
    };
    auto gapValue=[&](I capacity)->double{
        if(capacity<=modelCapacity)
            return value[static_cast<std::size_t>(capacity)];
        return value[modelCapacity]+static_cast<double>(capacity-modelCapacity);
    };
    auto chooseHighEndpoint=[&](std::map<I,I>::iterator gap,I length){
        const I remainder=gap->second-gap->first-length;
        // Preserve expandable tails and avoid an option unnecessary for
        // remainders already able to fit every legal request.
        if(remainder<=0||remainder>=maxLength||
           gap->first==0||gap->second==trench) return false;
        ++endpointCandidates;
        if(!lifetime.ready()) return false;
        auto right=liveByStart.lower_bound(gap->first);
        if(right==liveByStart.end()||right==liveByStart.begin()||
           right->first!=gap->second) return false;
        auto left=std::prev(right);
        const auto leftPipe=pipes[left->second];
        const auto rightPipe=pipes[right->second];
        if(leftPipe.first+leftPipe.second!=gap->first) return false;
        ++endpointForecasts;

        I leftOutside=0,rightOutside=0;
        if(gap!=gaps.begin()){
            auto outside=std::prev(gap);
            if(outside->second==leftPipe.first)
                leftOutside=outside->second-outside->first;
        }
        auto outside=std::next(gap);
        if(outside!=gaps.end()&&outside->first==rightPipe.first+rightPipe.second)
            rightOutside=outside->second-outside->first;
        const I leftReleased=leftPipe.second+leftOutside;
        const I rightReleased=rightPipe.second+rightOutside;
        const double leftSurplus=std::max(0.0,
            gapValue(remainder+leftReleased)-gapValue(remainder)-gapValue(leftReleased));
        const double rightSurplus=std::max(0.0,
            gapValue(remainder+rightReleased)-gapValue(remainder)-gapValue(rightReleased));
        if(leftSurplus<=1e-9&&rightSurplus<=1e-9) return false;
        ++endpointPositiveSurplus;

        // Stop this local option if any participating free span is filled.
        double fillRate=0.0;
        for(int request=1;request<=maxLength;++request){
            const int exposed=(request<=remainder?1:0)+
                (request<=leftOutside?1:0)+(request<=rightOutside?1:0);
            fillRate+=static_cast<double>(exposed)*perGapArrivalRate[request];
        }
        const auto forecast=lifetime.race(left->second,right->second,
            static_cast<int>(length),fillRate,historyCapacity);
        const double guardedCredit=leftSurplus*forecast.leftLower-
            rightSurplus*forecast.rightUpper;
        if(guardedCredit<=1e-9) return false;
        ++endpointHighOverrides;
        endpointGuardedCredit+=guardedCredit;
        return true;
    };
    while(std::cin>>command&&command){
        observe(command);
        if(command<0){
            const std::size_t pid=static_cast<std::size_t>(-command);
            auto p=pipes.at(pid);
            lifetime.death(pid);
            liveByStart.erase(p.first);
            std::cout<<p.first<<'\n'<<std::flush;
            add(p.first,p.first+p.second);
            --liveCount;
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
        auto gap=gaps.find(best->second);
        const bool highSide=chooseHighEndpoint(gap,length);
        const I gapStart=gap->first,end=gap->second;
        start=highSide?end-length:gapStart;
        erase(gap);
        add(gapStart,start);
        add(start+length,end);
        pipes.push_back({start,length});
        lifetime.birth(static_cast<int>(length));
        liveByStart.emplace(start,pipes.size()-1);
        ++liveCount;
        std::cout<<digs<<' '<<start<<'\n'<<std::flush;
    }
#ifdef PACKING_DIAGNOSTICS
    std::cerr<<"packing choices="<<choices
             <<" changed_from_best_fit="<<changed
             <<" model_builds="<<builds
             <<" predicted_opportunity_saved="<<predictedSaved
             <<" endpoint_candidates="<<endpointCandidates
             <<" endpoint_forecasts="<<endpointForecasts
             <<" endpoint_positive_surplus="<<endpointPositiveSurplus
             <<" endpoint_high_overrides="<<endpointHighOverrides
             <<" endpoint_guarded_credit="<<endpointGuardedCredit<<'\n';
#endif
}
