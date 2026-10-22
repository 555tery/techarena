#include "baseline_fork.hpp"
#include <cassert>
#include <fstream>

int main(int argc,char** argv) {
    std::uint64_t commands=0,branches=0,protectedBranches=0;
    for(int file=1;file<argc;++file) {
        std::ifstream in(argv[file]);double weight=0;int n=0;in>>weight>>n;
        Allocator state;state.routerQuiet=true;std::vector<int> cells;
        int ordinarySamples=0,protectedSamples=0;
        for(int i=0;i<n;++i) {
            int command=0;in>>command;assert(command!=0);++commands;
            if(command>0 && (state.pipes.size()-1)%16==0 && (ordinarySamples<64 || protectedSamples<32)) {
                Allocator probe=state;probe.routerCapture=true;probe.place(command);
                std::vector<int> routes;
                if(probe.lastRouterProtected && protectedSamples<32) {routes={1,2,3};++protectedSamples;}
                else if(probe.lastRouterActions.size()>1 && ordinarySamples<64) {
                    for(const auto& action:probe.lastRouterActions)routes.push_back(action.route);
                    ++ordinarySamples;
                }
                const auto originalGaps=state.freeByStart;
                const auto originalFenwick=state.activeFenwick;
                const auto originalTrench=state.trenchLength;
                for(int route:routes) {
                    Allocator branch=state;branch.routerCapture=true;branch.routerForced=route;
                    branch.place(command);branch.validateRouterState();++branches;
                    assert(branch.lastPlacementStart>=0 && branch.lastPlacementStart+command<=branch.trenchLength);
                    for(int k=0;k<command;++k) {
                        const auto point=static_cast<std::size_t>(branch.lastPlacementStart+k);
                        assert(point>=cells.size() || cells[point]==0);
                    }
                    if(probe.lastRouterProtected) {
                        ++protectedBranches;assert(branch.lastRouterChosen==0);
                        assert(branch.lastPlacementStart==probe.lastPlacementStart && branch.lastPlacementDigs==probe.lastPlacementDigs);
                        assert(branch.freeByStart==probe.freeByStart && branch.activeFenwick==probe.activeFenwick);
                        assert(branch.mcDecisionsUsed==probe.mcDecisionsUsed && branch.mcRolloutsRun==probe.mcRolloutsRun);
                    }
                    assert(state.freeByStart==originalGaps && state.activeFenwick==originalFenwick && state.trenchLength==originalTrench);
                }
            }
            if(command>0) {
                state.place(command);cells.resize(static_cast<std::size_t>(state.trenchLength),0);
                const auto pid=static_cast<int>(state.pipes.size())-1;
                for(int k=0;k<command;++k) {auto& value=cells[static_cast<std::size_t>(state.lastPlacementStart+k)];assert(value==0);value=pid;}
            } else {
                const auto pipe=state.pipes[static_cast<std::size_t>(-command)];state.remove(-command);
                for(int k=0;k<pipe.length;++k) {auto& value=cells[static_cast<std::size_t>(pipe.start+k)];assert(value==-command);value=0;}
            }
        }
        state.validateRouterState();
        std::int64_t occupied=0;for(int value:cells)if(value)++occupied;assert(occupied==state.routerOccupied);
    }
    assert(protectedBranches>0 && branches>protectedBranches);
    std::cout<<"{\"commands\":"<<commands<<",\"forced_branches\":"<<branches<<",\"protected_forced_noops\":"<<protectedBranches<<"}\n";
}
