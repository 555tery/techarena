#include "policy.hpp"
#ifndef MODEL_HEADER
#define MODEL_HEADER "model.hpp"
#endif
#include MODEL_HEADER
#include <cstdio>
#include <exception>
#ifndef LEARNED_ENABLED
#define LEARNED_ENABLED 1
#endif

int main() {
    prototype::State state;
    trajectory::Counters counters;
    int command;
    try {
        while(std::scanf("%d",&command)==1 && command!=0) {
            if(command>0) {
                const auto action=trajectory::choose(state,command,trajectory::TrainedWeights,LEARNED_ENABLED!=0,counters);
                state.place(command,action);
                std::printf("%d %lld\n",action.digs,static_cast<long long>(action.start));
            } else {
                const auto position=state.remove(-command);
                std::printf("%lld\n",static_cast<long long>(position));
            }
            std::fflush(stdout);
        }
        std::fprintf(stderr,"H2 placements=%llu eligible=%llu decisions=%llu changed=%llu candidates=%llu interior=%llu tail=%llu right_endpoint=%llu T=%lld F=%lld\n",
            static_cast<unsigned long long>(counters.placements),static_cast<unsigned long long>(counters.eligible),
            static_cast<unsigned long long>(counters.decisions),static_cast<unsigned long long>(counters.changed),
            static_cast<unsigned long long>(counters.candidates),static_cast<unsigned long long>(counters.interior),
            static_cast<unsigned long long>(counters.tail),static_cast<unsigned long long>(counters.rightEndpoint),
            static_cast<long long>(state.trench),static_cast<long long>(state.occupied));
    } catch(const std::exception& e) {
        std::fprintf(stderr,"H2 error: %s\n",e.what());return 2;
    }
}
