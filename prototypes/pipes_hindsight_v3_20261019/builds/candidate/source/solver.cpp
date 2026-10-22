#include "policy.hpp"
#ifndef MODEL_HEADER
#define MODEL_HEADER "model.hpp"
#endif
#include MODEL_HEADER
#include <cstdio>
#include <exception>
#ifndef HINDSIGHT_ENABLED
#define HINDSIGHT_ENABLED 1
#endif

int main() {
    prototype::State state;hindsight_v3::Counters counters;int command;
    try {
        // Read exactly one command, answer and flush before the next read.
        // No weight, command count, horizon, file access, or suffix enters here.
        while(std::scanf("%d",&command)==1 && command!=0) {
            if(command>0) {
                const auto a=hindsight_v3::choose(state,command,hindsight_v3::ModelWeights,
                    HINDSIGHT_ENABLED!=0,hindsight_v3::ModelTrained,counters);
                state.place(command,a);
                std::printf("%d %lld\n",a.digs,static_cast<long long>(a.start));
            } else std::printf("%lld\n",static_cast<long long>(state.remove(-command)));
            std::fflush(stdout);
        }
        std::fprintf(stderr,"H3 placements=%llu eligible=%llu decisions=%llu changed=%llu fallback=%llu T=%lld F=%lld trained=%d enabled=%d\n",
            static_cast<unsigned long long>(counters.placements),static_cast<unsigned long long>(counters.eligible),
            static_cast<unsigned long long>(counters.decisions),static_cast<unsigned long long>(counters.changed),
            static_cast<unsigned long long>(counters.fallback),static_cast<long long>(state.trench),
            static_cast<long long>(state.occupied),hindsight_v3::ModelTrained,HINDSIGHT_ENABLED!=0);
    } catch(const std::exception& e) {std::fprintf(stderr,"H3 error: %s\n",e.what());return 2;}
}
