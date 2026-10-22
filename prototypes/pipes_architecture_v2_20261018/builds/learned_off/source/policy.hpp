#pragma once
#include "allocator.hpp"
#include <array>
#include <cmath>
#include <cstdint>

namespace trajectory {
using prototype::Action;
using prototype::Meter;
using prototype::State;
constexpr int Input = 24, Hidden = 4, Parameters = Input * Hidden + Hidden + Hidden + 1;
using Weights = std::array<double, Parameters>;
using Features = std::array<double, Input>;

struct Counters {
    std::uint64_t placements=0, eligible=0, decisions=0, changed=0, candidates=0;
    std::uint64_t interior=0, tail=0, rightEndpoint=0;
};

// The candidate generator reads physical state only. Complexity is bounded by
// four size-index successors, forty bounded size buckets, and sixteen actions.
inline std::vector<Action> candidates(const State& s, int length) {
    std::vector<Action> result;
    result.reserve(16);
    const auto append=[&](Meter start, int kind) {
        if (result.size()>=16) return;
        const auto a=s.at(start,length,kind);
        for(const auto& previous:result) if(previous.start==a.start && previous.digs==a.digs) return;
        result.push_back(a);
    };
    const auto first=s.greedy(length);
    append(first.start,0);
    auto fit=s.sizes.lower_bound({length,-1});
    for(int i=0; fit!=s.sizes.end() && i<4; ++fit,++i) {
        append(fit->second,1);
        append(fit->second+fit->first-length,2);
    }
    Meter firstStart=std::numeric_limits<Meter>::max(),lastStart=-1;
    for(int bucket=length;bucket<=40;++bucket) {
        const auto& starts=s.startsByLength[static_cast<std::size_t>(bucket)];
        if(!starts.empty()) {firstStart=std::min(firstStart,*starts.begin());lastStart=std::max(lastStart,*starts.rbegin());}
    }
    if(lastStart>=0) {
        const auto firstGap=s.gaps.find(firstStart), lastGap=s.gaps.find(lastStart);
        append(firstGap->first,3);append(firstGap->second-length,4);
        append(lastGap->first,5);append(lastGap->second-length,6);
    }
    const auto [tailStart,tailEnd]=s.tailBounds(length);
    append(tailStart,7);append(tailEnd-length,8);
    fit=s.sizes.lower_bound({length,-1});
    if(fit!=s.sizes.end()) {
        const auto slack=fit->first-length;
        append(fit->second+slack/2,9);
        append(fit->second+slack/4,10);
    } else {
        append(tailStart+(tailEnd-tailStart-length)/2,9);
    }
    return result;
}

inline double clipped(Meter value) {return std::min(4.0,static_cast<double>(value)/40.0);}
inline double logAge(double value) {return std::log1p(std::max(0.0,value))/std::log(200001.0);}

struct Context {
    std::array<double,41> frequency{},deletionFrequency{};
    double youngFraction=0, insertionFraction=0, sameRun=0, meanDeletionAge=0;
    explicit Context(const State& s) {
        const double count=static_cast<double>(std::max<std::size_t>(1,s.lengths.size()));
        for(int n=1;n<=40;++n) frequency[static_cast<std::size_t>(n)]=s.frequency[static_cast<std::size_t>(n)]/count;
        const double deletes=static_cast<double>(std::max<std::size_t>(1,s.deletionAges.size()));
        for(std::size_t i=0;i<s.deletionAges.size();++i) {
            meanDeletionAge+=s.deletionAges[i]/deletes;
            if(s.deletionAges[i]<=32) youngFraction+=1/deletes;
            deletionFrequency[static_cast<std::size_t>(s.deletionLengths[i])]+=1/deletes;
        }
        for(int kind:s.eventKinds) if(kind>0) insertionFraction+=1.0/static_cast<double>(s.eventKinds.size());
        sameRun=std::min(1.0,static_cast<double>(s.sameRun)/64.0);
    }
};

inline Features features(const State& s, int length, const Action& a, const Context& c) {
    Features x{};
    const double extent=static_cast<double>(std::max<Meter>(20,s.trench));
    auto [gapStart,gapEnd]=s.tailBounds(length);
    gapEnd=s.trench+20*a.digs;
    auto it=s.gaps.upper_bound(a.start);
    if(it!=s.gaps.begin()) {
        --it;
        if(it->first<=a.start && (it->second>=a.start+length || it->second==s.trench)) {
            gapStart=it->first;
            gapEnd=std::max(it->second,gapEnd);
        }
    }
    if(a.digs==0) {
        auto containing=s.gaps.upper_bound(a.start);
        if(containing==s.gaps.begin()) throw std::runtime_error("feature action has no gap");
        --containing;gapStart=containing->first;gapEnd=containing->second;
    }
    const Meter left=a.start-gapStart,right=gapEnd-a.start-length;
    if(left<0 || right<0) throw std::runtime_error("negative action residual");
    x[0]=static_cast<double>(length)/40;
    x[1]=static_cast<double>(a.digs)/2;
    x[2]=clipped(left);x[3]=clipped(right);
    x[4]=clipped(gapEnd-gapStart);
    x[5]=static_cast<double>(a.start)/extent;
    x[6]=gapEnd>=s.trench ? 1:0;
    x[7]=(left>0 && right>0)?1:0;
    x[8]=(left==0 && right==0)?1:0;
    double capacityLost=0,missProbability=0;
    for(int n=1;n<=40;++n) {
        const auto frequency=c.frequency[static_cast<std::size_t>(n)];
        capacityLost+=frequency*static_cast<double>((gapEnd-gapStart)/n-left/n-right/n);
        if(n>std::max(left,right)) missProbability+=frequency;
    }
    x[9]=capacityLost/40;x[10]=missProbability;
    x[11]=static_cast<double>(s.occupied)/extent;
    x[12]=c.insertionFraction;x[13]=c.sameRun;
    int neighbor[2]={0,0};
    auto boundary=s.byEnd.find(gapStart);
    if(boundary!=s.byEnd.end()) neighbor[0]=boundary->second;
    boundary=s.byEnd.upper_bound(gapEnd);
    if(boundary!=s.byEnd.end() && s.pipes[static_cast<std::size_t>(boundary->second)].start==gapEnd)
        neighbor[1]=boundary->second;
    for(int side=0;side<2;++side) {
        if(!neighbor[side]) continue;
        const auto& p=s.pipes[static_cast<std::size_t>(neighbor[side])];
        x[14+side]=static_cast<double>(p.length)/40;
        x[16+side]=logAge(s.clock-p.born);
        Meter outer=0;
        if(side==0) {
            auto g=s.gaps.lower_bound(p.start);
            if(g!=s.gaps.begin()) {--g;if(g->second==p.start) outer=g->second-g->first;}
        } else {
            auto g=s.gaps.find(p.start+p.length);
            if(g!=s.gaps.end()) outer=g->second-g->first;
        }
        x[18+side]=clipped(outer);
        const Meter residual=side==0?left:right;
        x[20+side]=clipped(residual+p.length+outer);
        // Observed deletion-size frequency is causal; it is not lifetime data
        // for the live neighbor. Adjacency makes the two action sides distinct.
        x[22+side]=(residual==0?1.0:0.25)*c.deletionFrequency[static_cast<std::size_t>(p.length)]
            +(p.length==length?c.sameRun:0.0)+(s.clock-p.born<=32?c.youngFraction:0.0);
    }
    for(double value:x) if(!std::isfinite(value)) throw std::runtime_error("nonfinite actor input");
    return x;
}

inline double score(const Features& x,const Weights& weights) {
    double result=weights[Parameters-1];
    for(int h=0;h<Hidden;++h) {
        double z=weights[Input*Hidden+h];
        for(int j=0;j<Input;++j) z+=weights[h*Input+j]*x[static_cast<std::size_t>(j)];
        result+=weights[Input*Hidden+Hidden+h]*std::tanh(z);
    }
    return result;
}

inline Action choose(const State& s,int length,const Weights& weights,bool enabled,Counters& counters) {
    ++counters.placements;
    const auto baseline=s.greedy(length);
    if((counters.placements-1)%4!=0) return baseline;
    ++counters.eligible;
    if(!enabled) return baseline;
    const auto options=candidates(s,length);
    ++counters.decisions;counters.candidates+=options.size();
    const Context context(s);
    std::size_t best=0;double bestScore=-std::numeric_limits<double>::infinity();
    for(std::size_t i=0;i<options.size();++i) {
        const double value=score(features(s,length,options[i],context),weights);
        if(value>bestScore) {bestScore=value;best=i;}
    }
    const auto action=options[best];
    if(action.start!=baseline.start || action.digs!=baseline.digs) ++counters.changed;
    if(action.kind==9 || action.kind==10) ++counters.interior;
    if(action.kind==7 || action.kind==8) ++counters.tail;
    if(action.kind==2 || action.kind==4 || action.kind==6 || action.kind==8) ++counters.rightEndpoint;
    return action;
}
} // namespace trajectory
