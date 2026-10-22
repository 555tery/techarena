#include "scenario_planner.hpp"
#include <iostream>

static void sameGeometry(const h1::Geometry& local,const prototype::State& exact) {
    local.validate();exact.validate();
    if(local.trench!=exact.trench || local.count!=static_cast<int>(exact.gaps.size()))throw std::runtime_error("geometry size mismatch");
    int at=0;
    for(const auto& [start,end]:exact.gaps) {
        const auto& span=local.gaps[static_cast<std::size_t>(at++)];
        if(span.start!=start || span.end!=end)throw std::runtime_error("geometry boundary mismatch");
    }
}

int main() {
    try {
        h1::LiveIndex index;
        for(int id=1;id<=31;++id)index.add(id,1);
        for(int id=2;id<=30;id+=2)index.add(id,-1);
        for(int rank=1;rank<=16;++rank)if(index.kth(rank)!=2*rank-1)throw std::runtime_error("live-rank invariant");
        if(index.prefix(31)!=16)throw std::runtime_error("live-prefix invariant");

        prototype::State state;h1::Model model;h1::Planner planner;
        auto insert=[&](int length) {
            const auto action=state.greedy(length);state.place(length,action);
            model.insertion(length,static_cast<int>(state.pipes.size())-1,state.clock);state.validate();
        };
        auto remove=[&](int id) {model.deletion(state,id);state.remove(id);state.validate();};
        for(int round=0;round<8;++round) {
            const int first=static_cast<int>(state.pipes.size());
            for(int j=0;j<6;++j)insert(3+(round*7+j*3)%38);
            for(int j=0;j<4;++j)remove(first+j);
        }
        const auto forecast=model.forecast();
        const auto futures=h1::scenarios(state,model,17,forecast);
        const auto again=h1::scenarios(state,model,17,forecast);
        for(int regime=0;regime<h1::Regimes;++regime) {
            for(int step=0;step<h1::Horizon;++step) {
                const auto& a=futures[static_cast<std::size_t>(regime)].events[static_cast<std::size_t>(step)];
                const auto& b=again[static_cast<std::size_t>(regime)].events[static_cast<std::size_t>(step)];
                if(a.length!=b.length || a.id!=b.id || a.start!=b.start)throw std::runtime_error("forecast nondeterminism");
            }
            prototype::State exact=state;
            h1::Geometry geometry;geometry.trench=state.trench;
            for(const auto& [start,end]:state.gaps)geometry.free(start,end);
            std::array<int,h1::Horizon+1> virtualPid{};
            const auto root=exact.greedy(17);
            if(!geometry.place(17,root.start,0))throw std::runtime_error("root test placement");
            exact.place(17,root);virtualPid[0]=static_cast<int>(exact.pipes.size())-1;sameGeometry(geometry,exact);
            for(const auto& event:futures[static_cast<std::size_t>(regime)].events) {
                if(event.length>0) {
                    const auto start=geometry.greedy(event.length);
                    if(!geometry.place(event.length,start,-event.id-1))throw std::runtime_error("future test placement");
                    exact.place(event.length,exact.at(start,event.length,0));virtualPid[static_cast<std::size_t>(-event.id-1)]=static_cast<int>(exact.pipes.size())-1;
                } else {
                    geometry.remove(event,state);
                    exact.remove(event.id>0?event.id:virtualPid[static_cast<std::size_t>(-event.id-1)]);
                }
                sameGeometry(geometry,exact);
            }
        }
        const auto action=planner.choose(state,model,17);
        state.place(17,action);model.insertion(17,static_cast<int>(state.pipes.size())-1,state.clock);state.validate();
        if(PLANNER_ENABLED && planner.counters.expanded==0)throw std::runtime_error("planner did not activate");
        // Follow the highest-weight scenario as a *test fixture* to verify
        // retained-plan execution, real/virtual PID mapping and exhaustion.
        // The interactive solver itself has no access to these future events.
        std::array<int,h1::Horizon+1> mapped{};mapped[0]=static_cast<int>(state.pipes.size())-1;
        for(const auto& event:futures[0].events) {
            if(event.length>0) {
                const auto next=planner.choose(state,model,event.length);state.place(event.length,next);
                mapped[static_cast<std::size_t>(-event.id-1)]=static_cast<int>(state.pipes.size())-1;
                model.insertion(event.length,static_cast<int>(state.pipes.size())-1,state.clock);
            } else {
                const int id=event.id>0?event.id:mapped[static_cast<std::size_t>(-event.id-1)];
                planner.deletion(state,id);model.deletion(state,id);state.remove(id);
            }
            state.validate();
        }
        if(PLANNER_ENABLED && (planner.counters.plannedPlacements==0 || planner.counters.completedPaths==0))throw std::runtime_error("retained plan did not execute");
        planner.report();std::cout<<"selftest: live index, deterministic scenarios, exact local geometry, retained-plan execution and PID mapping OK\n";
    } catch(const std::exception& e) {std::cerr<<"selftest ERROR: "<<e.what()<<'\n';return 1;}
}
