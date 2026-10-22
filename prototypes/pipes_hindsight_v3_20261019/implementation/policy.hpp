#pragma once
#include "allocator.hpp"
#include <array>
#include <string>
#include <sstream>
#include <iomanip>

namespace hindsight_v3 {
constexpr int FeatureCount=128, MaxActions=8, BeamWidth=12, MaxCommands=96;
constexpr int MaxLive=12, MaxTrench=160, MaxLabelStates=8, SamplePlacementStride=3;
inline constexpr const char* FeatureSchema="causal_cross128_v1";
using prototype::Action;
using prototype::Meter;
using prototype::State;

inline bool eligible(const State& s) { return s.live<=MaxLive && s.trench<=MaxTrench; }

// BF first; first three fitting gaps in (gap length,address) order, left
// then right endpoint; minimal-tail left then right. Exact duplicates vanish.
inline std::vector<Action> candidates(const State& s,int length) {
    std::vector<Action> out;
    const auto append=[&](Action a) {
        for(const auto& b:out) if(a.start==b.start && a.digs==b.digs) return;
        if(out.size()<MaxActions) out.push_back(a);
    };
    append(s.greedy(length));
    auto it=s.sizes.lower_bound({length,-1});
    for(int n=0;it!=s.sizes.end() && n<3;++n,++it) {
        append(s.at(it->second,length,1));
        append(s.at(it->second+it->first-length,length,2));
    }
    const auto tail=s.tailBounds(length);
    append(s.at(tail.first,length,3));
    append(s.at(tail.second-length,length,4));
    return out;
}

// A linear scorer needs explicit state/action interactions: state-only
// histogram bins would cancel from every pairwise feature difference.
inline std::array<float,FeatureCount> scoringFeatures(const State& s,int length,const Action& a) {
    const auto raw=s.features(length,a);auto x=raw;
    Meter gapStart=s.trench,gapEnd=s.trench+20*a.digs;
    auto it=s.gaps.upper_bound(a.start);
    if(it!=s.gaps.begin()) {
        --it;
        if(it->first<=a.start && (it->second>=a.start+length || it->second==s.trench)) {
            gapStart=it->first;gapEnd=std::max(it->second,s.trench+20*a.digs);
            if(a.digs==0)gapEnd=it->second;
        }
    }
    const Meter left=a.start-gapStart,right=gapEnd-a.start-length,h=gapEnd-gapStart;
    if(left<0 || right<0)throw std::runtime_error("invalid scoring geometry");
    for(int n=1;n<=40;++n) {
        const float frequency=raw[static_cast<std::size_t>(n-1)];
        x[static_cast<std::size_t>(n-1)]=frequency*static_cast<float>(h/n-left/n-right/n);
        x[static_cast<std::size_t>(39+n)]=frequency*((std::max(left,right)<n && n<=h)?1.0f:0.0f);
    }
    const std::array<int,4> contexts{{90,88,91,82}},actions{{96,99,101,98}};
    for(std::size_t c=0;c<4;++c)for(std::size_t f=0;f<4;++f)
        x[80+4*c+f]=raw[static_cast<std::size_t>(contexts[c])]*raw[static_cast<std::size_t>(actions[f])];
    for(std::size_t j=0;j<8;++j)x[120+j]=raw[120+j]*raw[j<4?99:100];
    for(float value:x)if(!std::isfinite(value))throw std::runtime_error("nonfinite scoring feature");
    return x;
}

inline std::string physicalKey(const State& s) {
    std::ostringstream out;out<<s.trench<<'|';
    for(std::size_t pid=1;pid<s.pipes.size();++pid) {
        const auto& p=s.pipes[pid];
        if(p.live) out<<pid<<':'<<p.start<<':'<<p.length<<';';
    }
    return out.str();
}
inline std::string hashKey(const std::string& key) {
    std::uint64_t h=14695981039346656037ULL;
    for(unsigned char c:key) {h^=c;h*=1099511628211ULL;}
    std::ostringstream out;out<<std::hex<<std::setfill('0')<<std::setw(16)<<h;return out.str();
}

struct Counters {std::uint64_t placements=0,eligible=0,changed=0,fallback=0,decisions=0;};

inline Action choose(const State& s,int length,const std::array<double,FeatureCount>& w,
                     bool enabled,bool trained,Counters& counters) {
    ++counters.placements;
    const Action bf=s.greedy(length);
    if(eligible(s)) ++counters.eligible;
    if(!enabled || !trained || !eligible(s)) {++counters.fallback;return bf;}
    const auto domain=candidates(s,length);
    if(domain.size()<2) {++counters.fallback;return bf;}
    ++counters.decisions;
    std::size_t best=0;double bestScore=-std::numeric_limits<double>::infinity();
    for(std::size_t i=0;i<domain.size();++i) {
        const auto x=scoringFeatures(s,length,domain[i]);double value=0;
        for(int j=0;j<FeatureCount;++j) value+=w[static_cast<std::size_t>(j)]*x[static_cast<std::size_t>(j)];
        if(!std::isfinite(value)) {++counters.fallback;return bf;}
        // Strict comparison preserves candidate order (BF wins exact ties).
        if(value>bestScore) {bestScore=value;best=i;}
    }
    const auto a=domain[best];
    if(a.start!=bf.start || a.digs!=bf.digs) ++counters.changed;
    return a;
}
} // namespace hindsight_v3
