#pragma once
#include "allocator.hpp"
#include <iomanip>
#include <sstream>
#include <string>
#ifndef OPTION_HOLD
#define OPTION_HOLD 4
#endif
#ifndef OPTIONS_ENABLED
#define OPTIONS_ENABLED 1
#endif
static_assert(OPTION_HOLD==1 || OPTION_HOLD==4,"fixed commitment or its ablation");
namespace options_v4 {
using prototype::State; using prototype::Action; using prototype::Meter;
constexpr int FeatureCount=128, OptionCount=4, BeamWidth=8, MaxCommands=128, MaxLabelStates=8;
inline constexpr const char* FeatureSchema="causal_state128_bf_v1";
inline bool eligible(const State& s) {return s.live<=12 && s.trench<=160;}
inline std::array<float,128> features(const State& s,int length) {return s.features(length,s.greedy(length));}
inline Action optionAction(const State& s,int length,int option,int step=0) {
    if(option<0 || option>3)throw std::runtime_error("invalid option");
    if(option<2)return s.greedy(length,option==1);
    // Anchored causal macro: its first placement fixes the left anchor;
    // later placements in this same commitment use BF right endpoints.
    if(option==3)return s.greedy(length,step!=0);
    Meter first=std::numeric_limits<Meter>::max();
    // Bucket 40 contains every span >=40, all fitting because L<=40.
    for(int bucket=length;bucket<=40;++bucket) {
        const auto& starts=s.startsByLength[static_cast<std::size_t>(bucket)];
        if(!starts.empty())first=std::min(first,*starts.begin());
    }
    if(first!=std::numeric_limits<Meter>::max()) {
        return s.at(first,length,option);
    }
    const auto tail=s.tailBounds(length);
    return s.at(tail.first,length,option);
}
inline int selectOption(const std::array<double,4>& gain) {
    int best=0;
    for(int i=1;i<4;++i)if(gain[static_cast<std::size_t>(i)]>gain[static_cast<std::size_t>(best)])best=i;
    for(double value:gain)if(!std::isfinite(value))return 0;
    return gain[static_cast<std::size_t>(best)]>=0.25?best:0;
}
struct Counters {
    std::uint64_t placements=0,eligible_placements=0,decisions=0,non_bf_options=0;
    std::uint64_t continuation_placements=0,changes=0,cancellations=0,active_crossed_deletions=0,fallback=0;
};
struct Cursor {int option=-1,remaining=0,block=-1;};
struct Choice {Action action;int option=-1,block=-1;bool boundary=false,continuation=false;};
inline void cancel(Cursor& cursor,Counters& counters) {
    if(cursor.remaining>0)++counters.cancellations;
    cursor.option=-1;cursor.remaining=0;
}
inline void afterDeletion(const State& s,Cursor& cursor,Counters& counters) {
    if(!eligible(s))cancel(cursor,counters);
    else if(cursor.remaining>0)++counters.active_crossed_deletions;
}
template<class Predictor> Choice choose(const State& s,int length,Cursor& cursor,Counters& counters,
                                       Predictor predict,bool trained,int forced=-1) {
    ++counters.placements;const auto bf=s.greedy(length);
    if(eligible(s))++counters.eligible_placements;
    if(!OPTIONS_ENABLED || !eligible(s)) {
        cancel(cursor,counters);++counters.fallback;return {bf,-1,-1,false,false};
    }
    const bool boundary=cursor.remaining==0;
    if(boundary) {
        ++counters.decisions;++cursor.block;
        cursor.option=forced>=0?forced:(trained?selectOption(predict(features(s,length))):0);
        cursor.remaining=OPTION_HOLD;
        if(cursor.option!=0)++counters.non_bf_options;
    } else ++counters.continuation_placements;
    auto action=optionAction(s,length,cursor.option,OPTION_HOLD-cursor.remaining);
    if(action.start!=bf.start || action.digs!=bf.digs)++counters.changes;
    const Choice result{action,cursor.option,cursor.block,boundary,!boundary};
    --cursor.remaining;
    return result;
}
inline std::string physicalKey(const State& s) {
    std::ostringstream out;out<<s.trench<<'|';
    for(std::size_t pid=1;pid<s.pipes.size();++pid) {
        const auto& p=s.pipes[pid];if(p.live)out<<pid<<':'<<p.start<<':'<<p.length<<':'<<p.born<<';';
    }
    return out.str();
}
inline std::string hashKey(const std::string& key) {
    std::uint64_t h=14695981039346656037ULL;for(unsigned char c:key){h^=c;h*=1099511628211ULL;}
    std::ostringstream out;out<<std::hex<<std::setfill('0')<<std::setw(16)<<h;return out.str();
}
} // namespace options_v4
