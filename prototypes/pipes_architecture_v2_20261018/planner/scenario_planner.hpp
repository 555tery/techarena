#pragma once
#include "allocator.hpp"
#include <cassert>
#include <cstdio>
#include <numeric>
#include <optional>

#ifndef PLANNER_ENABLED
#define PLANNER_ENABLED 1
#endif

namespace h1 {
using prototype::Action;
using prototype::Meter;
using prototype::State;

// All caps below were fixed before development/final scoring.
constexpr int Horizon=14, Regimes=3, BeamWidth=3, RootCap=10;
constexpr int RegionCap=96, FutureCap=6, ProbeCount=5;
constexpr std::uint64_t WorkCap=420000;

struct Random {
    std::uint64_t value;
    std::uint64_t next() {
        value+=0x9e3779b97f4a7c15ULL;
        auto x=value; x=(x^(x>>30))*0xbf58476d1ce4e5b9ULL;
        x=(x^(x>>27))*0x94d049bb133111ebULL; return x^(x>>31);
    }
    double unit() {return static_cast<double>(next()>>11)*0x1.0p-53;}
    int integer(int n) {return n>0?static_cast<int>(next()%static_cast<unsigned>(n)):0;}
};

// Online insertion-order index. No input identifiers or future command access.
class LiveIndex {
    static constexpr int Capacity=200004;
    std::array<int,Capacity> tree{};
public:
    void add(int id,int delta) {
        if(id<=0 || id>=Capacity) throw std::runtime_error("PID capacity");
        for(int x=id;x<Capacity;x+=x&-x)tree[static_cast<std::size_t>(x)]+=delta;
    }
    int prefix(int id) const {
        int result=0;
        for(int x=std::min(id,Capacity-1);x>0;x-=x&-x)result+=tree[static_cast<std::size_t>(x)];
        return result;
    }
    int kth(int rank) const {
        int id=0;
        for(int bit=1<<17;bit;bit>>=1) {
            const int candidate=id+bit;
            if(candidate<Capacity && tree[static_cast<std::size_t>(candidate)]<rank) {
                id=candidate;rank-=tree[static_cast<std::size_t>(candidate)];
            }
        }
        return id+1;
    }
};

struct Observation {
    int kind=1,length=1,born=0,age=0;
    double rank=0.5;
};

struct ForecastModel {
    std::array<double,41> pooled{},local{};
    std::array<std::array<double,41>,4> transition{};
    std::array<std::array<double,2>,2> eventTransition{};
    std::vector<double> deletionRanks;
    double insertProbability=0.65, repeat=0.3, cohortEvidence=0, meanAge=64;
    double meanInsertRun=3,meanDeleteRun=2,meanRank=0.5;
    int lastKind=1,lastLength=20,dominant=20;
};

class Model {
public:
    LiveIndex alive;
    std::deque<Observation> history;
    std::array<std::uint64_t,41> totalSizes{};
    std::uint64_t fingerprint=0x243f6a8885a308d3ULL;
    int inserts=0,deletes=0;

    void remember(const Observation& event) {
        history.push_back(event);if(history.size()>512)history.pop_front();
        fingerprint^=static_cast<std::uint64_t>(event.kind>0?event.length:41+static_cast<int>(event.rank*1024));
        fingerprint*=0x100000001b3ULL;
    }
    void insertion(int length,int id,int clock) {
        alive.add(id,1);++inserts;++totalSizes[static_cast<std::size_t>(length)];
        remember({1,length,clock,0,0.5});
    }
    void deletion(const State& state,int id) {
        const auto& p=state.pipes.at(static_cast<std::size_t>(id));
        if(!p.live)throw std::runtime_error("deleting nonlive pipe");
        const double rank=(static_cast<double>(alive.prefix(id))-0.5)/std::max(1,state.live);
        remember({-1,p.length,p.born,state.clock+1-p.born,rank});
        alive.add(id,-1);++deletes;
    }
    ForecastModel forecast() const {
        ForecastModel f;
        for(int length=1;length<=40;++length) {
            f.pooled[static_cast<std::size_t>(length)]=0.25+static_cast<double>(totalSizes[static_cast<std::size_t>(length)]);
            f.local[static_cast<std::size_t>(length)]=0.25;
            for(auto& row:f.transition)row[static_cast<std::size_t>(length)]=0.25;
        }
        for(auto& row:f.eventTransition)row={1.0,1.0};
        int previousKind=-1,previousLength=0,same=0,pairs=0,insertCount=0;
        int runKind=0,runLength=0,insertRuns=0,deleteRuns=0,insertRunSum=0,deleteRunSum=0;
        int previousDeleteBorn=-1000000,previousDeletePosition=-1000000,position=0,close=0,cohortPairs=0;
        double ageSum=0,rankSum=0;
        for(const auto& e:history) {
            const int kind=e.kind>0?1:0;
            if(previousKind>=0)f.eventTransition[static_cast<std::size_t>(previousKind)][static_cast<std::size_t>(kind)]+=1;
            previousKind=kind;
            if(runKind!=e.kind) {
                if(runKind==1){++insertRuns;insertRunSum+=runLength;}
                if(runKind==-1){++deleteRuns;deleteRunSum+=runLength;}
                runKind=e.kind;runLength=0;
            }
            ++runLength;
            if(e.kind>0) {
                ++insertCount;f.local[static_cast<std::size_t>(e.length)]+=1;
                if(previousLength) {
                    f.transition[static_cast<std::size_t>((previousLength-1)/10)][static_cast<std::size_t>(e.length)]+=1;
                    ++pairs;if(previousLength==e.length)++same;
                }
                previousLength=e.length;f.lastLength=e.length;
            } else {
                f.deletionRanks.push_back(e.rank);rankSum+=e.rank;ageSum+=e.age;
                if(previousDeleteBorn>-1000000) {
                    ++cohortPairs;
                    if(position-previousDeletePosition<=4 && std::abs(e.born-previousDeleteBorn)<=8)++close;
                }
                previousDeleteBorn=e.born;previousDeletePosition=position;
            }
            ++position;f.lastKind=e.kind;
        }
        if(runKind==1){++insertRuns;insertRunSum+=runLength;}
        if(runKind==-1){++deleteRuns;deleteRunSum+=runLength;}
        f.insertProbability=(insertCount+2.0)/(history.size()+4.0);
        f.repeat=(same+1.0)/(pairs+4.0);
        f.meanInsertRun=static_cast<double>(insertRunSum+3)/(insertRuns+1);
        f.meanDeleteRun=static_cast<double>(deleteRunSum+2)/(deleteRuns+1);
        f.cohortEvidence=static_cast<double>(close)/(cohortPairs+4.0);
        if(!f.deletionRanks.empty()) {
            f.meanAge=ageSum/f.deletionRanks.size();f.meanRank=rankSum/f.deletionRanks.size();
        }
        f.dominant=static_cast<int>(std::max_element(f.local.begin()+1,f.local.end())-f.local.begin());
        return f;
    }
};

struct Event {
    int length=0; // >0 arrival; 0 deletion.
    int id=0;     // initial PID >0; virtual births -(index+1), root=-1.
    Meter start=0;
};
struct Scenario {
    std::array<Event,Horizon> events{};
    std::array<int,ProbeCount> probe{};
    double weight=1;
    int cohortDeletes=0;
};

inline int drawSize(const std::array<double,41>& counts,Random& rng) {
    double total=0;for(int i=1;i<=40;++i)total+=counts[static_cast<std::size_t>(i)];
    double target=rng.unit()*total;
    for(int i=1;i<=40;++i){target-=counts[static_cast<std::size_t>(i)];if(target<=0)return i;}
    return 40;
}

// Scenarios use a common forecast for every first action. Forecast PID choices
// depend on causal birth-rank observations, never on placement coordinates.
inline std::array<Scenario,Regimes> scenarios(const State& state,const Model& model,int currentLength,
                                             const ForecastModel& f) {
    std::array<Scenario,Regimes> result;
    const double cohortWeight=0.05+0.35*f.cohortEvidence;
    result[0].weight=0.65-cohortWeight/2;result[1].weight=0.35-cohortWeight/2;result[2].weight=cohortWeight;
    for(int regime=0;regime<Regimes;++regime) {
        auto& scenario=result[static_cast<std::size_t>(regime)];
        Random rng{model.fingerprint^static_cast<std::uint64_t>(state.clock+1)*0xd6e8feb86659fd93ULL^
                   static_cast<std::uint64_t>(currentLength+regime*83)*0xa0761d6478bd642fULL};
        std::array<bool,Horizon+1> virtualAlive{};virtualAlive[0]=true;
        std::vector<int> removed;
        int births=1,lastSize=currentLength,lastKind=1;
        const int build=std::clamp(static_cast<int>(std::lround(f.meanInsertRun)),2,5);
        const int retire=std::clamp(static_cast<int>(std::lround(f.meanDeleteRun)),2,5);
        const bool youngCohort=f.meanRank>=0.65 && f.meanAge<=64;
        double cohortRank=f.deletionRanks.empty()?0.5:f.deletionRanks[static_cast<std::size_t>(rng.integer(static_cast<int>(f.deletionRanks.size())))];
        const int phaseSize=drawSize(f.pooled,rng);
        auto realCount=[&](){return state.live-static_cast<int>(removed.size());};
        auto virtualCount=[&](){int n=0;for(int i=0;i<births;++i)n+=virtualAlive[static_cast<std::size_t>(i)];return n;};
        auto kthRemaining=[&](int rank) {
            int lo=1,hi=static_cast<int>(state.pipes.size())-1;
            while(lo<hi) {
                const int mid=(lo+hi)/2;
                int count=model.alive.prefix(mid);for(int id:removed)if(id<=mid)--count;
                if(count>=rank)hi=mid;else lo=mid+1;
            }
            return lo;
        };
        auto deleteRank=[&](double quantile) {
            const int real=realCount(),total=real+virtualCount();
            const int rank=std::clamp(static_cast<int>(quantile*total),0,std::max(0,total-1));
            if(rank<real) {
                const int id=kthRemaining(rank+1);removed.push_back(id);
                const auto& pipe=state.pipes[static_cast<std::size_t>(id)];
                return Event{0,id,pipe.start};
            }
            int wanted=rank-real;
            for(int i=0;i<births;++i)if(virtualAlive[static_cast<std::size_t>(i)] && wanted--==0) {
                virtualAlive[static_cast<std::size_t>(i)]=false;return Event{0,-i-1,0};
            }
            throw std::runtime_error("forecast deletion rank");
        };
        for(int step=0;step<Horizon;++step) {
            double probability=f.insertProbability;
            if(regime==0) {
                const auto& row=f.eventTransition[static_cast<std::size_t>(lastKind)];probability=row[1]/(row[0]+row[1]);
            }
            bool insertion=rng.unit()<probability;
            if(regime==2) {
                const int cycle=build+retire;
                insertion=(step%cycle)<build;
            }
            if(realCount()+virtualCount()==0)insertion=true;
            if(insertion) {
                int length;
                if(regime==1)length=rng.unit()<std::max(0.25,f.repeat)?phaseSize:drawSize(f.pooled,rng);
                else if(rng.unit()<f.repeat)length=lastSize;
                else length=drawSize(f.transition[static_cast<std::size_t>((lastSize-1)/10)],rng);
                scenario.events[static_cast<std::size_t>(step)]={length,-births-1,0};
                virtualAlive[static_cast<std::size_t>(births++)]=true;lastSize=length;lastKind=1;
            } else {
                double quantile;
                if(regime==2) {
                    ++scenario.cohortDeletes;
                    // With observed young deletion cohorts, retire the newly built
                    // cohort as one unit; otherwise retire adjacent initial ranks.
                    if(youngCohort && virtualCount()>0) {
                        const int real=realCount(),total=real+virtualCount();
                        quantile=(real+0.25)/std::max(1,total);
                    } else quantile=cohortRank;
                } else if(f.deletionRanks.empty())quantile=rng.unit();
                else quantile=f.deletionRanks[static_cast<std::size_t>(rng.integer(static_cast<int>(f.deletionRanks.size())))];
                scenario.events[static_cast<std::size_t>(step)]=deleteRank(quantile);lastKind=0;
            }
        }
        for(int& length:scenario.probe)length=regime==1?drawSize(f.pooled,rng):drawSize(f.local,rng);
    }
    return result;
}

struct Span {Meter start=0,end=0;};
struct Location {Meter start=0;int length=0;bool live=false;};
struct Geometry {
    std::array<Span,RegionCap> gaps{};
    std::array<Location,Horizon+1> births{};
    int count=0;
    Meter trench=0;

    void free(Meter start,Meter end) {
        if(start>=end)return;
        int at=0;while(at<count && gaps[static_cast<std::size_t>(at)].start<start)++at;
        if(at>0 && gaps[static_cast<std::size_t>(at-1)].end>=start) {
            --at;start=std::min(start,gaps[static_cast<std::size_t>(at)].start);
            end=std::max(end,gaps[static_cast<std::size_t>(at)].end);
            for(int j=at;j+1<count;++j)gaps[static_cast<std::size_t>(j)]=gaps[static_cast<std::size_t>(j+1)];--count;
        }
        while(at<count && gaps[static_cast<std::size_t>(at)].start<=end) {
            end=std::max(end,gaps[static_cast<std::size_t>(at)].end);
            for(int j=at;j+1<count;++j)gaps[static_cast<std::size_t>(j)]=gaps[static_cast<std::size_t>(j+1)];--count;
        }
        if(count>=RegionCap)throw std::runtime_error("region overflow");
        for(int j=count;j>at;--j)gaps[static_cast<std::size_t>(j)]=gaps[static_cast<std::size_t>(j-1)];
        gaps[static_cast<std::size_t>(at)]={start,end};++count;
    }
    bool place(int length,Meter start,int birth=-1) {
        if(start<0)return false;
        const Meter required=std::max<Meter>(0,start+length-trench);
        const Meter newEnd=trench+20*((required+19)/20);
        if(newEnd>trench){free(trench,newEnd);trench=newEnd;}
        int at=0;while(at<count && gaps[static_cast<std::size_t>(at)].end<=start)++at;
        if(at==count || gaps[static_cast<std::size_t>(at)].start>start || gaps[static_cast<std::size_t>(at)].end<start+length)return false;
        const auto gap=gaps[static_cast<std::size_t>(at)];
        for(int j=at;j+1<count;++j)gaps[static_cast<std::size_t>(j)]=gaps[static_cast<std::size_t>(j+1)];--count;
        free(gap.start,start);free(start+length,gap.end);
        if(birth>=0)births[static_cast<std::size_t>(birth)]={start,length,true};
        return true;
    }
    void remove(const Event& event,const State& state) {
        if(event.id>0) {
            const auto& pipe=state.pipes[static_cast<std::size_t>(event.id)];free(pipe.start,pipe.start+pipe.length);
        } else {
            auto& pipe=births[static_cast<std::size_t>(-event.id-1)];
            if(pipe.live){free(pipe.start,pipe.start+pipe.length);pipe.live=false;}
        }
    }
    Meter greedy(int length) const {
        Meter best=std::numeric_limits<Meter>::max(),start=-1;
        for(int i=0;i<count;++i) {
            const auto& gap=gaps[static_cast<std::size_t>(i)];const auto size=gap.end-gap.start;
            if(size>=length && (size<best || (size==best && gap.start<start))){best=size;start=gap.start;}
        }
        if(start>=0)return start;
        return count>0 && gaps[static_cast<std::size_t>(count-1)].end==trench?gaps[static_cast<std::size_t>(count-1)].start:trench;
    }
    void validate() const {
        Meter previous=-1;
        for(int i=0;i<count;++i) {
            const auto& g=gaps[static_cast<std::size_t>(i)];
            if(g.start<=previous || g.start<0 || g.end<=g.start || g.end>trench)throw std::runtime_error("local geometry invariant");
            previous=g.end;
        }
        for(const auto& p:births)if(p.live)for(int i=0;i<count;++i) {
            const auto& g=gaps[static_cast<std::size_t>(i)];
            if(p.start<g.end && g.start<p.start+p.length)throw std::runtime_error("virtual pipe/free overlap");
        }
    }
};

inline std::vector<Action> roots(const State& state,int length,int dominant) {
    std::vector<Action> actions;
    auto append=[&](Meter start,int kind) {
        for(const auto& a:actions)if(a.start==start)return;
        if(static_cast<int>(actions.size())<RootCap)actions.push_back(state.at(start,length,kind));
    };
    const auto baseline=state.greedy(length);append(baseline.start,0);
    const auto best=state.sizes.lower_bound({length,-1});
    if(best!=state.sizes.end()) {
        append(best->second+best->first-length,1);
        // Address-diverse equal-size alternatives, not just distinct sizes.
        const auto equalLast=std::prev(state.sizes.upper_bound({best->first,std::numeric_limits<Meter>::max()}));
        append(equalLast->second,2);append(equalLast->second+equalLast->first-length,3);
    }
    Meter first=std::numeric_limits<Meter>::max(),last=-1;
    for(int bucket=length;bucket<=40;++bucket) {
        const auto& starts=state.startsByLength[static_cast<std::size_t>(bucket)];
        if(!starts.empty()){first=std::min(first,*starts.begin());last=std::max(last,*starts.rbegin());}
    }
    if(last>=0) {
        const auto left=state.gaps.find(first),right=state.gaps.find(last);
        append(left->first,4);append(left->second-length,5);append(right->first,6);append(right->second-length,7);
    }
    const auto [tail,end]=state.tailBounds(length);append(tail,8);append(end-length,9);
    if(best!=state.sizes.end() && best->first>=length+dominant)append(best->second+dominant,10);
    return actions;
}

inline Geometry region(const State& state,const std::vector<Action>& actions,
                       const std::array<Scenario,Regimes>& forecast,bool& compressed) {
    Geometry result;result.trench=state.trench;
    std::vector<Span> needed;
    auto add=[&](std::map<Meter,Meter>::const_iterator it){if(it!=state.gaps.end())needed.push_back({it->first,it->second});};
    for(const auto& a:actions) {
        auto it=state.gaps.upper_bound(a.start);
        if(it!=state.gaps.begin()){--it;if(it->second>a.start)add(it);}
    }
    if(!state.gaps.empty() && state.gaps.rbegin()->second==state.trench)add(std::prev(state.gaps.end()));
    for(const auto& scenario:forecast)for(const auto& event:scenario.events)if(!event.length && event.id>0) {
        const auto& pipe=state.pipes[static_cast<std::size_t>(event.id)];
        auto it=state.gaps.lower_bound(pipe.start);
        if(it!=state.gaps.begin()) {const auto previous=std::prev(it);if(previous->second==pipe.start)add(previous);}
        it=state.gaps.find(pipe.start+pipe.length);add(it);
    }
    auto unique=[](std::vector<Span>& spans) {
        std::sort(spans.begin(),spans.end(),[](Span a,Span b){return a.start<b.start;});
        spans.erase(std::unique(spans.begin(),spans.end(),[](Span a,Span b){return a.start==b.start;}),spans.end());
    };
    unique(needed);
    constexpr std::size_t InitialCap=RegionCap-Horizon-ProbeCount-3;
    // Root spans and deletion neighbors are mandatory. Reserve one extra span
    // per command for allocation splits / isolated deletions, root/probe splits,
    // and transient insertion before a containing span is removed.
    if(needed.size()>InitialCap)throw std::length_error("critical region cap");
    // Forecast best-fits are optional; cap them without dropping any critical
    // root/deletion span. This approximation freezes all other free regions.
    for(const auto& scenario:forecast)for(const auto& event:scenario.events)if(event.length>0) {
        auto it=state.sizes.lower_bound({event.length,-1});
        if(it!=state.sizes.end()) {
            bool present=false;for(const auto& span:needed)if(span.start==it->second){present=true;break;}
            if(!present && needed.size()<InitialCap)add(state.gaps.find(it->second));
        }
    }
    unique(needed);
    for(auto span:needed)result.free(span.start,span.end);
    compressed=needed.size()<state.gaps.size();return result;
}

inline std::array<Meter,FutureCap> nextActions(const Geometry& g,int length,int dominant,int& count) {
    std::array<Meter,FutureCap> result{};count=0;
    auto append=[&](Meter start) {
        for(int i=0;i<count;++i)if(result[static_cast<std::size_t>(i)]==start)return;
        if(count<FutureCap)result[static_cast<std::size_t>(count++)]=start;
    };
    const Meter baseline=g.greedy(length);append(baseline);
    int best=-1;Meter bestSize=std::numeric_limits<Meter>::max();
    int first=-1,last=-1;
    for(int i=0;i<g.count;++i) {
        const auto& gap=g.gaps[static_cast<std::size_t>(i)];const auto size=gap.end-gap.start;
        if(size<length)continue;
        if(first<0)first=i;last=i;if(size<bestSize){bestSize=size;best=i;}
    }
    if(best>=0)append(g.gaps[static_cast<std::size_t>(best)].end-length);
    if(first>=0)append(g.gaps[static_cast<std::size_t>(first)].start);
    if(last>=0)append(g.gaps[static_cast<std::size_t>(last)].end-length);
    const Meter tail=g.count>0 && g.gaps[static_cast<std::size_t>(g.count-1)].end==g.trench?g.gaps[static_cast<std::size_t>(g.count-1)].start:g.trench;
    append(tail);const Meter end=g.trench+20*((std::max<Meter>(0,tail+length-g.trench)+19)/20);append(end-length);
    if(best>=0 && bestSize>=length+dominant)append(g.gaps[static_cast<std::size_t>(best)].start+dominant);
    return result;
}

inline Meter probeGrowth(Geometry geometry,const std::array<int,ProbeCount>& sizes,int limit=ProbeCount) {
    const Meter initial=geometry.trench;
    for(int i=0;i<limit;++i)if(!geometry.place(sizes[static_cast<std::size_t>(i)],geometry.greedy(sizes[static_cast<std::size_t>(i)])))
        throw std::runtime_error("probe placement");
    return geometry.trench-initial;
}

struct Node {
    Geometry geometry;
    std::array<Meter,Horizon> plan{};
    double priority=0;
    std::uint64_t tie=0;
    int recourseChanges=0;
};
struct ScenarioResult {
    double score=0;
    std::array<Meter,Horizon> plan{};
    int recourseChanges=0;
};
struct Counters {
    std::array<std::uint64_t,4> insertions{},eligible{},scored{},changed{};
    std::array<std::uint64_t,Regimes> regimes{};
    std::uint64_t expanded=0,compressed=0,cohortDecisions=0,rootChanges=0,regionAbstain=0,budgetExhausted=0;
    std::uint64_t recourseBranches=0;
    std::uint64_t plannedPlacements=0,matchedDeletions=0,mismatchAborts=0,legalityAborts=0,pathDivergences=0,completedPaths=0;
    std::uint64_t selectedRecourseChanges=0,cohortDecisive=0;
    std::uint64_t plannedKernelChanges=0;
    std::array<std::uint64_t,Regimes> regimeVotes{};
    double cohortWeightSum=0;
};

class Planner {
    [[maybe_unused]] std::array<int,4> used{},nextClock{};
    struct Pending {
        Scenario scenario;
        std::array<Meter,Horizon> coordinates{};
        std::array<int,Horizon+1> realPid{};
        int step=0;
        bool active=false;
    };
    std::array<Pending,Regimes> pending{};
    static bool legal(const State& state,int length,Meter start) {
        if(start<0)return false;
        if(start+length<=state.trench) {
            auto it=state.gaps.upper_bound(start);
            if(it==state.gaps.begin())return false;
            --it;return it->first<=start && it->second>=start+length;
        }
        Meter tail=state.trench;
        if(!state.gaps.empty() && state.gaps.rbegin()->second==state.trench)tail=state.gaps.rbegin()->first;
        return start>=tail && state.at(start,length,0).digs*20+state.trench<=100000000;
    }
    int expectedPid(const Pending& path,const Event& event) const {
        return event.id>0?event.id:path.realPid[static_cast<std::size_t>(-event.id-1)];
    }
    void advance(Pending& path) {
        if(++path.step==Horizon){path.active=false;++counters.completedPaths;}
    }
    std::optional<Action> continueArrival(const State& state,int length) {
        int chosen=-1;
        for(int regime=0;regime<Regimes;++regime) {
            auto& path=pending[static_cast<std::size_t>(regime)];if(!path.active)continue;
            const auto& event=path.scenario.events[static_cast<std::size_t>(path.step)];
            if(event.length!=length){path.active=false;++counters.mismatchAborts;continue;}
            if(!legal(state,length,path.coordinates[static_cast<std::size_t>(path.step)])) {
                path.active=false;++counters.legalityAborts;continue;
            }
            if(chosen<0 || path.scenario.weight>pending[static_cast<std::size_t>(chosen)].scenario.weight)chosen=regime;
        }
        if(chosen<0)return std::nullopt;
        const Meter coordinate=pending[static_cast<std::size_t>(chosen)].coordinates[static_cast<std::size_t>(pending[static_cast<std::size_t>(chosen)].step)];
        for(auto& path:pending)if(path.active) {
            if(path.coordinates[static_cast<std::size_t>(path.step)]!=coordinate) {
                path.active=false;++counters.pathDivergences;continue;
            }
            const auto& event=path.scenario.events[static_cast<std::size_t>(path.step)];
            path.realPid[static_cast<std::size_t>(-event.id-1)]=static_cast<int>(state.pipes.size());advance(path);
        }
        ++counters.plannedPlacements;return state.at(coordinate,length,20);
    }
    static int scale(int live){return live<64?0:(live<512?1:(live<4096?2:3));}
    static int epoch(int clock){return clock<2048?0:(clock<16384?1:(clock<65536?2:3));}
    double priority(const Geometry& g,const Scenario& scenario,int step,const State& state) const {
        const auto direct=probeGrowth(g,scenario.probe,3);
        Geometry retired=g;
        for(int future=step+1;future<Horizon;++future) {
            const auto& event=scenario.events[static_cast<std::size_t>(future)];
            if(!event.length && (event.id>0 || retired.births[static_cast<std::size_t>(-event.id-1)].live))retired.remove(event,state);
        }
        const auto afterRetirement=probeGrowth(retired,scenario.probe,3);
        return 8.0*g.trench+2.0*direct+afterRetirement;
    }
    ScenarioResult solveScenario(const Geometry& initial,const Action& root,int length,const Scenario& scenario,
                                 const ForecastModel& model,const State& state) {
        std::vector<Node> beam;
        Node first;first.geometry=initial;
        if(!first.geometry.place(length,root.start,0))throw std::runtime_error("root local placement");
        beam.push_back(first);
        for(int step=0;step<Horizon;++step) {
            const auto& event=scenario.events[static_cast<std::size_t>(step)];
            if(!event.length) {
                for(auto& node:beam)node.geometry.remove(event,state);
                continue;
            }
            std::vector<Node> children;children.reserve(BeamWidth*FutureCap);
            for(const auto& previous:beam) {
                int count=0;const auto actions=nextActions(previous.geometry,event.length,model.dominant,count);
                for(int i=0;i<count;++i) {
                    if(counters.expanded>=WorkCap)throw std::length_error("work cap");
                    ++counters.expanded;if(i>0)++counters.recourseBranches;
                    Node child=previous;
                    if(!child.geometry.place(event.length,actions[static_cast<std::size_t>(i)],-event.id-1))throw std::runtime_error("beam placement");
                    child.plan[static_cast<std::size_t>(step)]=actions[static_cast<std::size_t>(i)];
                    child.recourseChanges+=i>0;
                    child.priority=priority(child.geometry,scenario,step,state);
                    child.tie=previous.tie*7+static_cast<std::uint64_t>(i);
                    children.push_back(std::move(child));
                }
            }
            std::stable_sort(children.begin(),children.end(),[](const Node& a,const Node& b){
                return a.priority<b.priority || (a.priority==b.priority && a.tie<b.tie);
            });
            // Preserve geometric diversity: equal address plans that leave the
            // same free spans cannot consume all beam slots.
            beam.clear();
            for(auto& child:children) {
                bool duplicate=false;
                for(const auto& other:beam) {
                    if(child.geometry.trench!=other.geometry.trench || child.geometry.count!=other.geometry.count)continue;
                    bool same=true;
                    for(int k=0;k<child.geometry.count;++k)if(child.geometry.gaps[static_cast<std::size_t>(k)].start!=other.geometry.gaps[static_cast<std::size_t>(k)].start || child.geometry.gaps[static_cast<std::size_t>(k)].end!=other.geometry.gaps[static_cast<std::size_t>(k)].end){same=false;break;}
                    // Keep lifetime labels as well as current geometry.
                    if(same)for(int k=0;k<=Horizon;++k)if(child.geometry.births[static_cast<std::size_t>(k)].live!=other.geometry.births[static_cast<std::size_t>(k)].live || (child.geometry.births[static_cast<std::size_t>(k)].live && child.geometry.births[static_cast<std::size_t>(k)].start!=other.geometry.births[static_cast<std::size_t>(k)].start)){same=false;break;}
                    if(same){duplicate=true;break;}
                }
                if(!duplicate)beam.push_back(std::move(child));
                if(beam.size()==BeamWidth)break;
            }
        }
        ScenarioResult result;result.score=std::numeric_limits<double>::infinity();
        for(const auto& node:beam) {
            const double score=8.0*node.geometry.trench+2.0*probeGrowth(node.geometry,scenario.probe);
            if(score<result.score){result.score=score;result.plan=node.plan;result.recourseChanges=node.recourseChanges;}
        }
        return result;
    }
public:
    Counters counters;
    Action choose(const State& state,const Model& model,int length) {
        const int bucket=scale(state.live);
        ++counters.insertions[static_cast<std::size_t>(bucket)];
        const auto baseline=state.greedy(length);
        if(model.history.size()<16)return baseline;
        // This cheap shortlist is also the control kernel's legal action domain.
        const auto actions=roots(state,length,state.lastLength?state.lastLength:length);
        if(actions.size()>1)++counters.eligible[static_cast<std::size_t>(bucket)];
#if !PLANNER_ENABLED
        return baseline;
#else
        if(const auto continuation=continueArrival(state,length)) {
            if(continuation->start!=baseline.start){++counters.changed[static_cast<std::size_t>(bucket)];++counters.plannedKernelChanges;}
            return *continuation;
        }
        if(actions.size()<2)return baseline;
        const int timeEpoch=epoch(state.clock);
        constexpr std::array<int,4> quota{24,32,32,40},stride{64,384,1536,4096};
        if(used[static_cast<std::size_t>(timeEpoch)]>=quota[static_cast<std::size_t>(timeEpoch)] || state.clock<nextClock[static_cast<std::size_t>(timeEpoch)])return baseline;
        if(counters.expanded>=WorkCap){++counters.budgetExhausted;return baseline;}
        const auto fitted=model.forecast();
        const auto future=scenarios(state,model,length,fitted);
        bool compressed=false;
        Geometry local;
        try {local=region(state,actions,future,compressed);}
        catch(const std::length_error&){++counters.regionAbstain;nextClock[static_cast<std::size_t>(timeEpoch)]=state.clock+stride[static_cast<std::size_t>(timeEpoch)];return baseline;}
        std::vector<double> values(actions.size(),0);
        std::vector<double> worst(actions.size(),-std::numeric_limits<double>::infinity());
        std::array<std::array<ScenarioResult,RootCap>,Regimes> plans{};
        try {
            for(int regime=0;regime<Regimes;++regime)for(std::size_t candidate=0;candidate<actions.size();++candidate) {
                const auto plan=solveScenario(local,actions[candidate],length,future[static_cast<std::size_t>(regime)],fitted,state);
                plans[static_cast<std::size_t>(regime)][candidate]=plan;const double score=plan.score;
                values[candidate]+=future[static_cast<std::size_t>(regime)].weight*score;worst[candidate]=std::max(worst[candidate],score);
            }
        } catch(const std::length_error&) {++counters.budgetExhausted;return baseline;}
        ++used[static_cast<std::size_t>(timeEpoch)];nextClock[static_cast<std::size_t>(timeEpoch)]=state.clock+stride[static_cast<std::size_t>(timeEpoch)];
        ++counters.scored[static_cast<std::size_t>(bucket)];if(compressed)++counters.compressed;
        for(auto& count:counters.regimes)++count;
        ++counters.cohortDecisions;
        counters.cohortWeightSum+=future[2].weight;
        std::size_t selected=0;
        for(std::size_t candidate=1;candidate<actions.size();++candidate) {
            // Small worst-regime component guards against selecting a very
            // optimistic phase scenario; all first actions see identical futures.
            if(0.9*values[candidate]+0.1*worst[candidate]+1e-9<0.9*values[selected]+0.1*worst[selected])selected=candidate;
        }
        std::size_t withoutCohort=0;
        auto nonCohortScore=[&](std::size_t candidate) {
            return 0.9*(future[0].weight*plans[0][candidate].score+future[1].weight*plans[1][candidate].score)/(future[0].weight+future[1].weight)+0.1*std::max(plans[0][candidate].score,plans[1][candidate].score);
        };
        for(std::size_t candidate=1;candidate<actions.size();++candidate)if(nonCohortScore(candidate)+1e-9<nonCohortScore(withoutCohort))withoutCohort=candidate;
        if(selected!=withoutCohort)++counters.cohortDecisive;
        for(int regime=0;regime<Regimes;++regime) {
            std::size_t expert=0;
            for(std::size_t candidate=1;candidate<actions.size();++candidate)if(plans[static_cast<std::size_t>(regime)][candidate].score<plans[static_cast<std::size_t>(regime)][expert].score)expert=candidate;
            if(expert>0)++counters.regimeVotes[static_cast<std::size_t>(regime)];
            auto& path=pending[static_cast<std::size_t>(regime)];path=Pending{};
            path.scenario=future[static_cast<std::size_t>(regime)];path.coordinates=plans[static_cast<std::size_t>(regime)][selected].plan;
            path.realPid[0]=static_cast<int>(state.pipes.size());path.active=true;
            counters.selectedRecourseChanges+=static_cast<std::uint64_t>(plans[static_cast<std::size_t>(regime)][selected].recourseChanges);
        }
        if(actions[selected].start!=baseline.start){++counters.changed[static_cast<std::size_t>(bucket)];++counters.rootChanges;}
        return actions[selected];
#endif
    }
    void deletion(const State& state,int id) {
#if PLANNER_ENABLED
        bool matched=false;
        for(auto& path:pending)if(path.active) {
            const auto& event=path.scenario.events[static_cast<std::size_t>(path.step)];
            if(event.length!=0 || expectedPid(path,event)!=id) {
                path.active=false;++counters.mismatchAborts;continue;
            }
            if(!state.pipes[static_cast<std::size_t>(id)].live){path.active=false;++counters.legalityAborts;continue;}
            advance(path);matched=true;
        }
        if(matched)++counters.matchedDeletions;
#else
        (void)state;(void)id;
#endif
    }
    void report() const {
        std::fprintf(stderr,"H1 enabled=%d horizon=%d beam=%d work=%llu/%llu compressed=%llu region_abstain=%llu budget_exhausted=%llu recourse_branches=%llu cohort_decisions=%llu root_changes=%llu regimes=%llu,%llu,%llu\n",PLANNER_ENABLED,Horizon,BeamWidth,
            static_cast<unsigned long long>(counters.expanded),static_cast<unsigned long long>(WorkCap),static_cast<unsigned long long>(counters.compressed),static_cast<unsigned long long>(counters.regionAbstain),static_cast<unsigned long long>(counters.budgetExhausted),static_cast<unsigned long long>(counters.recourseBranches),static_cast<unsigned long long>(counters.cohortDecisions),static_cast<unsigned long long>(counters.rootChanges),static_cast<unsigned long long>(counters.regimes[0]),static_cast<unsigned long long>(counters.regimes[1]),static_cast<unsigned long long>(counters.regimes[2]));
        constexpr std::array<const char*,4> names{"live_lt64","live_64_511","live_512_4095","live_ge4096"};
        for(std::size_t i=0;i<4;++i)std::fprintf(stderr,"H1 %s insertions=%llu eligible=%llu scored=%llu changed=%llu\n",names[i],static_cast<unsigned long long>(counters.insertions[i]),static_cast<unsigned long long>(counters.eligible[i]),static_cast<unsigned long long>(counters.scored[i]),static_cast<unsigned long long>(counters.changed[i]));
        std::fprintf(stderr,"H1 plan_execution placements=%llu kernel_changes=%llu matched_deletions=%llu mismatch_path_aborts=%llu legality_path_aborts=%llu divergent_path_aborts=%llu completed_paths=%llu selected_recourse_changes=%llu cohort_decisive=%llu cohort_weight_sum=%.6f regime_non_kernel_votes=%llu,%llu,%llu\n",static_cast<unsigned long long>(counters.plannedPlacements),static_cast<unsigned long long>(counters.plannedKernelChanges),static_cast<unsigned long long>(counters.matchedDeletions),static_cast<unsigned long long>(counters.mismatchAborts),static_cast<unsigned long long>(counters.legalityAborts),static_cast<unsigned long long>(counters.pathDivergences),static_cast<unsigned long long>(counters.completedPaths),static_cast<unsigned long long>(counters.selectedRecourseChanges),static_cast<unsigned long long>(counters.cohortDecisive),counters.cohortWeightSum,static_cast<unsigned long long>(counters.regimeVotes[0]),static_cast<unsigned long long>(counters.regimeVotes[1]),static_cast<unsigned long long>(counters.regimeVotes[2]));
    }
};
} // namespace h1
