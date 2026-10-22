#include "baseline_fork.hpp"
#include <fstream>
#include <iomanip>
#include <string>

#if defined(OFFLINE_LABELS)
namespace {
struct Input { std::vector<int> commands; };
Input readInput(const std::string& path) {
    std::ifstream in(path);double weight=0;int n=0;
    if(!(in>>weight>>n) || n<1 || n>200000)throw std::runtime_error("router input header");
    Input result;result.commands.resize(static_cast<std::size_t>(n));
    for(int& c:result.commands)if(!(in>>c) || c==0 || c>40)throw std::runtime_error("router input command");
    return result;
}
void advance(Allocator& state,int command) {
    if(command>0)state.place(command);else state.remove(-command);
}
std::int64_t suffix(Allocator state,const std::vector<int>& commands,std::size_t from) {
    state.routerCapture=false;state.routerEnabled=false;state.routerForced=0;
    for(std::size_t i=from;i<commands.size();++i)advance(state,commands[i]);
    state.validateRouterState();return state.trenchLength;
}
int label(int argc,char** argv) {
    if(argc!=8)throw std::runtime_error("label INPUT OUTPUT STREAM MAX_STATES ROLLIN WARMUP");
    const auto input=readInput(argv[2]);std::ofstream out(argv[3]);const std::string stream=argv[4];
    const auto maxStates=static_cast<std::size_t>(std::stoi(argv[5]));
    const bool learned=std::string(argv[6])=="model";
#if !defined(USE_ROUTER)
    if(learned)throw std::runtime_error("model roll-in requires USE_ROUTER build");
#endif
    const auto warmup=static_cast<std::size_t>(std::stoi(argv[7]));
    const auto placements=static_cast<std::size_t>(std::count_if(input.commands.begin(),input.commands.end(),[](int c){return c>0;}));
    const auto stride=std::max<std::size_t>(16,(placements>2*warmup?placements-2*warmup:1)/maxStates);
    std::size_t nextSample=warmup;
    out<<"stream,state,action,is_base,target_trench,base_trench,route";
    for(int j=0;j<128;++j)out<<",f"<<j;out<<'\n'<<std::setprecision(9);
    Allocator state;state.routerQuiet=true;state.routerEnabled=learned;
    std::size_t states=0,rows=0,signals=0,eligible=0,protectedCount=0;
    std::uint64_t operations=0;double gain=0,randomRegret=0;
    // Direct control continuation is a separate complete baseline trajectory.
    Allocator control;control.routerQuiet=true;
    for(int c:input.commands)advance(control,c);control.validateRouterState();
    for(std::size_t i=0;i<input.commands.size();++i) {
        const int command=input.commands[i];
        if(command>0 && state.pipes.size()-1>=nextSample && (state.pipes.size()-1)%16==0 && states<maxStates) {
            Allocator probe=state;probe.routerCapture=true;probe.routerEnabled=false;probe.routerForced=0;
            probe.place(command);
            if(probe.lastRouterProtected)++protectedCount;
            if(probe.lastRouterActions.size()>1) {
                ++eligible;probe.validateRouterState();
                const auto actions=probe.lastRouterActions;
                std::vector<std::int64_t> outcomes;
                for(const auto& action:actions) {
                    Allocator branch=state;branch.routerForced=action.route;branch.routerEnabled=false;branch.routerCapture=true;
                    branch.place(command);
                    if(branch.lastPlacementStart!=action.start || branch.lastPlacementDigs!=0 || branch.lastRouterChosen!=action.route)
                        throw std::runtime_error("forced router action mismatch");
                    branch.validateRouterState();
                    outcomes.push_back(suffix(std::move(branch),input.commands,i+1));
                    operations+=input.commands.size()-i-1;
                }
                if(!learned && outcomes[0]!=control.trenchLength)throw std::runtime_error("forced baseline final differs from direct baseline replay");
                const auto base=outcomes[0],best=*std::min_element(outcomes.begin(),outcomes.end());
                gain+=static_cast<double>(base-best);if(base>best)++signals;
                double regret=0;for(auto value:outcomes)regret+=static_cast<double>(value-best)/static_cast<double>(outcomes.size());randomRegret+=regret;
                for(std::size_t n=0;n<actions.size();++n) {
                    out<<stream<<','<<(learned?"dagger_":"")<<states<<','<<n<<','<<(n==0?1:0)<<','<<outcomes[n]<<','<<base<<','<<actions[n].route;
                    for(float value:actions[n].features)out<<','<<value;out<<'\n';++rows;
                }
                ++states;nextSample+=stride;
            }
        }
        advance(state,command);
    }
    state.validateRouterState();
    std::cout<<"{\"stream\":\""<<stream<<"\",\"states\":"<<states<<",\"rows\":"<<rows
        <<",\"signal_states\":"<<signals<<",\"mean_one_action_gain_m\":"<<(states?gain/static_cast<double>(states):0)
        <<",\"mean_random_regret_m\":"<<(states?randomRegret/static_cast<double>(states):0)
        <<",\"suffix_commands\":"<<operations<<",\"direct_baseline_trench\":"<<control.trenchLength
        <<",\"rollin_trench\":"<<state.trenchLength<<",\"sampled_protected_opportunities\":"<<protectedCount
        <<",\"eligible_samples\":"<<eligible<<",\"protected_branch_calls\":"<<state.routerProtected
        <<",\"rollin_router_calls\":"<<state.routerCalls<<",\"rollin_router_changes\":"<<state.routerChanges<<"}\n";
    return 0;
}
}
#endif

int main(int argc,char** argv) {
    try {
#if defined(OFFLINE_LABELS)
        if(argc>1 && std::string(argv[1])=="label")return label(argc,argv);
#endif
        std::ios::sync_with_stdio(false);std::cin.tie(nullptr);
        Allocator state;
#if defined(USE_ROUTER)
        state.routerEnabled=true;
#endif
        if(argc>1 && std::string(argv[1])=="baseline")state.routerEnabled=false;
        std::int64_t command=0;
        while(std::cin>>command) {
            if(command==0) {
                state.validateRouterState();
                std::cerr<<"router_calls="<<state.routerCalls<<" router_changes="<<state.routerChanges
                    <<" protected="<<state.routerProtected<<'\n';return 0;
            }
            if(command>0)state.place(static_cast<int>(command));else state.remove(-command);
        }
        return 0;
    } catch(const std::exception& error) {std::cerr<<"router error: "<<error.what()<<'\n';return 2;}
}
