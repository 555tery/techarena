#include "policy.hpp"
#ifndef MODEL_HEADER
#define MODEL_HEADER "model.hpp"
#endif
#include MODEL_HEADER
#include <cstdio>
int main() {
    options_v4::State state;options_v4::Cursor cursor;options_v4::Counters counters;int command;
    try {
        // One command, response, flush. No count, weight, suffix, or model file read.
        while(std::scanf("%d",&command)==1 && command!=0) {
            if(command>0) {
                const auto c=options_v4::choose(state,command,cursor,counters,options_v4::predict,options_v4::ModelTrained);
                state.place(command,c.action);std::printf("%d %lld\n",c.action.digs,static_cast<long long>(c.action.start));
            } else {
                const auto start=state.remove(-command);options_v4::afterDeletion(state,cursor,counters);
                std::printf("%lld\n",static_cast<long long>(start));
            }
            std::fflush(stdout);
        }
        std::fprintf(stderr,"O4 placements=%llu eligible=%llu decisions=%llu non_bf_options=%llu continuation_placements=%llu changes=%llu cancellations=%llu active_crossed_deletions=%llu fallback=%llu T=%lld F=%lld trained=%d enabled=%d hold=%d\n",
          (unsigned long long)counters.placements,(unsigned long long)counters.eligible_placements,(unsigned long long)counters.decisions,
          (unsigned long long)counters.non_bf_options,(unsigned long long)counters.continuation_placements,(unsigned long long)counters.changes,
          (unsigned long long)counters.cancellations,(unsigned long long)counters.active_crossed_deletions,(unsigned long long)counters.fallback,
          (long long)state.trench,(long long)state.occupied,options_v4::ModelTrained,OPTIONS_ENABLED,OPTION_HOLD);
    } catch(const std::exception& e){std::fprintf(stderr,"O4 error: %s\n",e.what());return 2;}
}
