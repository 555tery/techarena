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
        bool refill=false;
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
    using ContextCells=std::array<Cell,2>;
    using ContextRates=std::array<Rate,2>;
    std::vector<Record> records_{Record{}};
    std::array<std::array<Cell,bands_>,41> cells_{};
    std::array<std::array<Rate,bands_>,41> rates_{};
    std::array<std::array<ContextCells,bands_>,41> contextCells_{};
    std::array<std::array<ContextRates,bands_>,41> contextRates_{};
    std::array<std::size_t,bands_> crossing_{};
    std::uint64_t clock_=0,deaths_=0,live_=0,livePeak_=0;
    std::uint64_t contextFits_=0;
    bool ready_=false;

    static std::size_t band(std::uint64_t age){
        std::size_t result=0;
        while(result+1<bands_&&age>=lower_[result+1]) ++result;
        return result;
    }
    void enter(const Record& record,std::size_t b){
        const auto length=static_cast<std::size_t>(record.length);
        const auto context=static_cast<std::size_t>(record.refill);
        const auto update=[&](Cell& cell){
            ++cell.active;
            cell.birthSum+=record.born;
        };
        update(cells_[length][b]);
        update(contextCells_[length][b][context]);
    }
    void leave(const Record& record,std::size_t b,std::uint64_t age){
        const auto length=static_cast<std::size_t>(record.length);
        const auto context=static_cast<std::size_t>(record.refill);
        const auto update=[&](Cell& cell){
            cell.completedExposure+=age-lower_[b];
            --cell.active;
            cell.birthSum-=record.born;
        };
        update(cells_[length][b]);
        update(contextCells_[length][b][context]);
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
    std::uint64_t expansionBirths() const {return livePeak_;}
    std::uint64_t refillBirths() const {
        return static_cast<std::uint64_t>(records_.size()-1)-livePeak_;
    }
    std::uint64_t contextFits() const {return contextFits_;}

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
        const bool refill=live_<livePeak_;
        records_.push_back(Record{clock_,length,true,refill});
        enter(records_.back(),0);
        ++live_;
        livePeak_=std::max(livePeak_,live_);
    }
    void death(std::size_t pid){
        Record& record=records_[pid];
        const std::uint64_t age=clock_-record.born;
        leave(record,band(age),age);
        // An event exactly at a landmark ends the preceding interval.
        const auto length=static_cast<std::size_t>(record.length);
        const auto context=static_cast<std::size_t>(record.refill);
        const std::size_t b=band(age==0?0:age-1);
        ++cells_[length][b].deaths;
        ++contextCells_[length][b][context].deaths;
        record.active=false;
        --live_;
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
            const double borrowedExposure=priorEvents/pooledRate;
            for(std::size_t length=1;length<=40;++length){
                const auto& cell=cells_[length][b];
                const double denominator=static_cast<double>(exposure(cell,b))+
                    borrowedExposure;
                const double shape=static_cast<double>(cell.deaths)+priorEvents;
                rates_[length][b]=Rate{
                    shape/denominator,
                    std::sqrt(shape)/denominator+
                        borrowedExposure/denominator*pooledError};
                contextRates_[length][b].fill(rates_[length][b]);
            }

            // Profile out one baseline hazard per length. For theta=log(r),
            // each stratum contributes D1*theta-D*log(E0+r*E1).
            // E includes outstanding, right-censored exposure.
            // A unit Gaussian prior on theta shrinks toward the parent model.
            const auto derivatives=[&](double theta){
                const double ratio=std::exp(theta);
                double gradient=-theta,information=1.0;
                for(std::size_t length=1;length<=40;++length){
                    const auto& split=contextCells_[length][b];
                    const double e0=static_cast<double>(exposure(split[0],b));
                    const double e1=static_cast<double>(exposure(split[1],b));
                    const double d0=static_cast<double>(split[0].deaths);
                    const double d1=static_cast<double>(split[1].deaths);
                    const double events=d0+d1;
                    if(e0<=0.0||e1<=0.0||events<=0.0) continue;
                    const double share=ratio*e1/(e0+ratio*e1);
                    gradient+=d1-events*share;
                    information+=events*share*(1.0-share);
                }
                return std::pair<double,double>{gradient,information};
            };
            double theta=0.0;
            for(int iteration=0;iteration<12;++iteration){
                const auto d=derivatives(theta);
                const double step=std::clamp(d.first/d.second,-1.0,1.0);
                theta+=step;
                if(std::abs(step)<1e-8) break;
            }
            const auto d=derivatives(theta);
            const double sigma=1.0/std::sqrt(d.second);
            if(std::abs(theta)<=2.0*sigma) continue;
            ++contextFits_;
            const double ratio=std::exp(theta);
            for(std::size_t length=1;length<=40;++length){
                const auto& split=contextCells_[length][b];
                const double e0=static_cast<double>(exposure(split[0],b));
                const double e1=static_cast<double>(exposure(split[1],b));
                // Split borrowed exposure equally between the two contexts.
                // Normalization retains the parent's pooled hazard scale.
                const double weight=(e1+0.5*borrowedExposure)/
                    (e0+e1+borrowedExposure);
                const double normalizer=(1.0-weight)+weight*ratio;
                const double ratioShare=weight*ratio/normalizer;
                const Rate base=rates_[length][b];
                for(std::size_t context=0;context<2;++context){
                    const double multiplier=(context==0?1.0:ratio)/normalizer;
                    const double sensitivity=context==0?ratioShare:1.0-ratioShare;
                    const double mean=base.mean*multiplier;
                    // Add uncertainty conservatively, including the learned ratio.
                    contextRates_[length][b][context]=Rate{
                        mean,base.error*multiplier+mean*sensitivity*sigma};
                }
            }
        }
    }

    RaceBounds race(std::size_t leftPid,std::size_t rightPid,int newLength,
                    double fillRate,std::uint64_t horizon,
                    bool useBirthContext=true) const {
        const Record& left=records_[leftPid];
        const Record& right=records_[rightPid];
        const std::uint64_t leftAge=clock_-left.born;
        const std::uint64_t rightAge=clock_-right.born;
        RaceBounds result;
        const std::size_t newContext=live_<livePeak_?1:0;
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
            const Rate& leftRate=useBirthContext?
                contextRates_[static_cast<std::size_t>(left.length)][lb]
                             [static_cast<std::size_t>(left.refill)]:
                rates_[static_cast<std::size_t>(left.length)][lb];
            const Rate& rightRate=useBirthContext?
                contextRates_[static_cast<std::size_t>(right.length)][rb]
                             [static_cast<std::size_t>(right.refill)]:
                rates_[static_cast<std::size_t>(right.length)][rb];
            const Rate& newRate=useBirthContext?
                contextRates_[static_cast<std::size_t>(newLength)][nb][newContext]:
                rates_[static_cast<std::size_t>(newLength)][nb];
            const auto l=interval(leftRate);
            const auto r=interval(rightRate);
            const auto n=interval(newRate);
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
    using LogRateDerivative=std::array<double,maxLength+1>;
    std::array<LogRateDerivative,modelCapacity+1> logRateDerivative{};
    LogRateDerivative aggregateDerivative{};
    std::array<double,maxLength+1> perGapArrivalRate{};
    std::size_t historyCount=0,historyHead=0;
    int recentDeletes=0,liveCount=0;
    std::uint64_t operations=0,lastBuild=0;
    std::uint64_t choices=0,changed=0,builds=0;
    std::uint64_t endpointCandidates=0,endpointForecasts=0;
    std::uint64_t endpointPositiveSurplus=0,endpointHighOverrides=0;
    std::uint64_t contextEndpointChanges=0;
    double endpointGuardedCredit=0.0;
    double predictedSaved=0.0;
    std::uint64_t inventoryComparisons=0,inventoryOverrides=0;
    std::uint64_t inventoryNonzeroCredits=0;
    double inventoryPredictedGain=0.0,inventoryMaxLogRateStep=0.0;
    bool haveModel=false;
    auto bucket=[&](I capacity){
        return static_cast<std::size_t>(std::min<I>(capacity,trackedCapacity+1));
    };
    auto erase=[&](std::map<I,I>::iterator p){
        const I capacity=p->second-p->first;
        --gapCounts[bucket(capacity)];
        if(haveModel){
            const auto& derivative=logRateDerivative[
                static_cast<std::size_t>(std::min<I>(capacity,modelCapacity))];
            const int support=static_cast<int>(std::min<I>(capacity,maxLength));
            for(int request=1;request<=support;++request)
                aggregateDerivative[request]-=derivative[request];
        }
        sizes.erase({capacity,p->first});
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
        const I capacity=end-start;
        ++gapCounts[bucket(capacity)];
        if(haveModel){
            const auto& derivative=logRateDerivative[
                static_cast<std::size_t>(std::min<I>(capacity,modelCapacity))];
            const int support=static_cast<int>(std::min<I>(capacity,maxLength));
            for(int request=1;request<=support;++request)
                aggregateDerivative[request]+=derivative[request];
        }
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
        logRateDerivative[0].fill(0.0);
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

            // Differentiate expiry*V(c)=sum_l rate[l]*(l+V(c-l)-V(c))_+.
            // The derivative is with respect to log(rate[request]), holding
            // expiry and the local Bellman acceptance branch fixed.
            auto& derivative=logRateDerivative[capacity];
            derivative.fill(0.0);
            double derivativeDenominator=expiry;
            for(int length=1;length<=count;++length){
                const double benefit=static_cast<double>(length)+
                    value[capacity-length]-value[capacity];
                if(benefit<=0.0) continue;
                derivativeDenominator+=rate[length];
                const auto& previous=logRateDerivative[capacity-length];
                const int support=std::min(capacity-length,maxLength);
                for(int request=1;request<=support;++request)
                    derivative[request]+=rate[length]*previous[request];
                derivative[length]+=rate[length]*benefit;
            }
            for(int request=1;request<=count;++request)
                derivative[request]/=derivativeDenominator;
        }
        aggregateDerivative.fill(0.0);
        for(int capacity=1;capacity<=trackedCapacity+1;++capacity){
            if(!gapCounts[capacity]) continue;
            const auto& derivative=logRateDerivative[
                static_cast<std::size_t>(std::min(capacity,modelCapacity))];
            const int support=std::min(capacity,maxLength);
            for(int request=1;request<=support;++request)
                aggregateDerivative[request]+=
                    static_cast<double>(gapCounts[capacity])*derivative[request];
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
#ifdef PACKING_DIAGNOSTICS
        const auto pooledForecast=lifetime.race(left->second,right->second,
            static_cast<int>(length),fillRate,historyCapacity,false);
        const double pooledCredit=leftSurplus*pooledForecast.leftLower-
            rightSurplus*pooledForecast.rightUpper;
        if((guardedCredit>1e-9)!=(pooledCredit>1e-9))
            ++contextEndpointChanges;
#endif
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
        // Retain the parent's winner and find its best distinct-width runner-up.
        const I parentWidth=best->first;
        I alternativeWidth=0;
        double alternativeCost=0.0;
        if(parentWidth!=bestFitWidth){
            alternativeWidth=bestFitWidth;
            alternativeCost=originalCost;
        }
        for(int s=static_cast<int>(length);s<=trackedCapacity;++s){
            if(!gapCounts[s]||static_cast<I>(s)==parentWidth) continue;
            const double cost=gapValue(s)-gapValue(s-length);
            if(alternativeWidth==0||cost+tolerance<alternativeCost){
                alternativeWidth=s;
                alternativeCost=cost;
            }
        }
        if(gapCounts[trackedCapacity+1]>0&&parentWidth<=trackedCapacity&&
           (alternativeWidth==0||
            static_cast<double>(length)+tolerance<alternativeCost)){
            const auto overflow=sizes.lower_bound({trackedCapacity+1,-1});
            alternativeWidth=overflow->first;
            alternativeCost=static_cast<double>(length);
        }
        if(alternativeWidth!=0){
            // Removing one fitting gap changes log(rate) by log(N/(N-1)).
            // Use current inventory; the Bellman derivatives retain the
            // parent's existing model rebuild schedule.
            std::array<double,maxLength+1> logRoutingShift{};
            int fitting=0;
            for(int s=trackedCapacity+1;s>=1;--s){
                fitting+=gapCounts[s];
                if(s<=maxLength&&fitting>1)
                    logRoutingShift[s]=std::log1p(
                        1.0/static_cast<double>(fitting-1));
            }
            const auto poolCost=[&](I width,double localCost){
                const I remainder=width-length;
                if(remainder>=maxLength) return localCost;
                const auto& before=logRateDerivative[
                    static_cast<std::size_t>(std::min<I>(width,modelCapacity))];
                const auto& after=logRateDerivative[
                    static_cast<std::size_t>(std::min<I>(remainder,modelCapacity))];
                double credit=0.0;
                for(int request=static_cast<int>(remainder)+1;
                    request<=maxLength&&static_cast<I>(request)<=width;
                    ++request){
                    if(logRoutingShift[request]==0.0) continue;
                    // Sensitivity of all gaps after replacing width by remainder.
                    const double response=std::max(0.0,
                        aggregateDerivative[request]-before[request]+after[request]);
                    credit+=response*logRoutingShift[request];
                    if(response>tolerance)
                        inventoryMaxLogRateStep=std::max(
                            inventoryMaxLogRateStep,logRoutingShift[request]);
                }
                if(credit>tolerance) ++inventoryNonzeroCredits;
                return localCost-credit;
            };
            ++inventoryComparisons;
            const double parentPoolCost=poolCost(parentWidth,selectedCost);
            const double alternativePoolCost=poolCost(alternativeWidth,alternativeCost);
            if(alternativePoolCost+tolerance<parentPoolCost){
                best=sizes.lower_bound({alternativeWidth,-1});
                selectedCost=alternativeCost;
                ++inventoryOverrides;
                inventoryPredictedGain+=parentPoolCost-alternativePoolCost;
            }
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
             <<" endpoint_guarded_credit="<<endpointGuardedCredit
             <<" lifetime_expansion_births="<<lifetime.expansionBirths()
             <<" lifetime_refill_births="<<lifetime.refillBirths()
             <<" lifetime_supported_context_fits="<<lifetime.contextFits()
             <<" lifetime_context_endpoint_changes="<<contextEndpointChanges
             <<" inventory_comparisons="<<inventoryComparisons
             <<" inventory_nonzero_credits="<<inventoryNonzeroCredits
             <<" inventory_overrides="<<inventoryOverrides
             <<" inventory_predicted_gain="<<inventoryPredictedGain
             <<" inventory_max_log_rate_step="<<inventoryMaxLogRateStep<<'\n';
#endif
}
