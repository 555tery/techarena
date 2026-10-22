#include "policy.hpp"
#include <fstream>
#include <iostream>
#include <iomanip>
#include <string>
#include <unordered_set>
#include <tuple>

namespace h=hindsight_v3;
using h::Action;using h::State;using h::Meter;
struct Step {int commandIndex;Action action;};
struct Node {State state;std::vector<Step> path;std::string key;};
struct SearchCounters {
    std::uint64_t expanded=0,generated=0,deduplicated=0,prunedBound=0,prunedWidth=0;
    std::uint64_t placementLayers=0,deletionLayers=0,completed=0;
};
struct Result {
    Meter bfCost=0,cost=0,beamCost=-1;bool reference=false;
    std::vector<Step> path;SearchCounters c;
};

static Meter fragmentation(const State& s) {
    // Count holes first, then penalize tiny holes. Only breaks trench ties.
    Meter tiny=0;for(const auto& g:s.gaps) if(g.second-g.first<8)tiny+=8-(g.second-g.first);
    return static_cast<Meter>(s.gaps.size())*1000+tiny;
}
static bool better(const Node& a,const Node& b) {
    return std::make_tuple(a.state.trench,fragmentation(a.state),a.key)<
           std::make_tuple(b.state.trench,fragmentation(b.state),b.key);
}
static void addCounters(SearchCounters& a,const SearchCounters& b) {
    a.expanded+=b.expanded;a.generated+=b.generated;a.deduplicated+=b.deduplicated;
    a.prunedBound+=b.prunedBound;a.prunedWidth+=b.prunedWidth;
    a.placementLayers+=b.placementLayers;a.deletionLayers+=b.deletionLayers;a.completed+=b.completed;
}
static Result search(const State& before,int rootIndex,const Action& root,const std::vector<int>& commands) {
    Result r;Node initial{before,{}, {}};
    initial.state.place(commands[static_cast<std::size_t>(rootIndex)],root);
    initial.path.push_back({rootIndex,root});initial.key=h::physicalKey(initial.state);
    // A COMPLETE BF suffix for EACH forced root is kept outside the beam.
    // Therefore width pruning can never make the label worse than this path.
    Node reference=initial;
    for(std::size_t i=static_cast<std::size_t>(rootIndex+1);i<commands.size();++i) {
        const int command=commands[i];
        if(command>0) {const auto a=reference.state.greedy(command);reference.state.place(command,a);reference.path.push_back({static_cast<int>(i),a});}
        else reference.state.remove(-command);
    }
    reference.state.validate();r.bfCost=reference.state.trench;
    std::vector<Node> beam;beam.push_back(std::move(initial));
    for(std::size_t i=static_cast<std::size_t>(rootIndex+1);i<commands.size() && !beam.empty();++i) {
        const int command=commands[i];std::vector<Node> next;
        if(command>0) {
            ++r.c.placementLayers;
            for(const auto& parent:beam) {
                ++r.c.expanded;
                // Crucial: EVERY subsequent placement branches again. No fixed
                // BF suffix is substituted for these joint placement choices.
                for(const auto& action:h::candidates(parent.state,command)) {
                    ++r.c.generated;Node child=parent;child.state.place(command,action);
                    if(child.state.trench>r.bfCost) {++r.c.prunedBound;continue;}
                    child.path.push_back({static_cast<int>(i),action});
                    child.key=h::physicalKey(child.state);next.push_back(std::move(child));
                }
            }
        } else {
            ++r.c.deletionLayers;
            for(auto& parent:beam) {parent.state.remove(-command);parent.key=h::physicalKey(parent.state);next.push_back(std::move(parent));}
        }
        std::sort(next.begin(),next.end(),better);
        std::unordered_set<std::string> keys;std::vector<Node> unique;
        for(auto& node:next) {
            if(!keys.insert(node.key).second) {++r.c.deduplicated;continue;}
            if(unique.size()<h::BeamWidth)unique.push_back(std::move(node));
            else ++r.c.prunedWidth;
        }
        beam=std::move(unique);
    }
    r.c.completed=beam.size();
    r.cost=r.bfCost;r.path=reference.path;r.reference=true;
    if(!beam.empty()) {
        std::sort(beam.begin(),beam.end(),better);beam[0].state.validate();r.beamCost=beam[0].state.trench;
        if(r.beamCost<=r.bfCost) {r.cost=r.beamCost;r.path=std::move(beam[0].path);r.reference=false;}
    }
    return r;
}

static std::string quote(const std::string& s) {
    std::ostringstream out;out<<'"';
    for(unsigned char c:s) {if(c=='"' || c=='\\')out<<'\\'<<c;else if(c<32)out<<"\\u"<<std::hex<<std::setw(4)<<std::setfill('0')<<static_cast<int>(c)<<std::dec;else out<<c;}
    out<<'"';return out.str();
}
static void emitCounters(std::ostream& out,const SearchCounters& c) {
    out<<"{\"expanded\":"<<c.expanded<<",\"generated\":"<<c.generated<<",\"deduplicated\":"<<c.deduplicated
       <<",\"pruned_bound\":"<<c.prunedBound<<",\"pruned_width\":"<<c.prunedWidth<<",\"placement_layers\":"<<c.placementLayers
       <<",\"deletion_layers\":"<<c.deletionLayers<<",\"completed\":"<<c.completed<<'}';
}
int main(int argc,char** argv) {
    try {
        std::string input,output,stats;
        for(int i=1;i<argc;++i) {
            const std::string arg=argv[i];
            if(i+1>=argc)throw std::runtime_error("expected --input FILE --output LABELS.jsonl --stats STATS.json");
            if(arg=="--input")input=argv[++i];else if(arg=="--output")output=argv[++i];else if(arg=="--stats")stats=argv[++i];
            else throw std::runtime_error("unknown argument: "+arg);
        }
        if(input.empty() || output.empty() || stats.empty())throw std::runtime_error("required: --input FILE --output LABELS.jsonl --stats STATS.json");
        std::ifstream in(input);double weight;int n;
        if(!(in>>weight>>n) || !std::isfinite(weight) || n<1 || n>h::MaxCommands)throw std::runtime_error("teacher input must have 1..96 commands");
        std::vector<int> commands(static_cast<std::size_t>(n));
        for(auto& c:commands)if(!(in>>c) || c==0 || c>40)throw std::runtime_error("invalid command");
        int zero;std::string extra;if(!(in>>zero) || zero!=0 || (in>>extra))throw std::runtime_error("expected one final zero and EOF");
        // Validate the entire stream before opening output files.
        State check;for(int c:commands)if(c>0)check.place(c,check.greedy(c));else check.remove(-c);check.validate();
        std::ofstream labels(output),report(stats);if(!labels || !report)throw std::runtime_error("cannot open output or stats");
        labels<<std::setprecision(9);
        State rollin;int placement=0,lastSelected=-h::SamplePlacementStride,selected=0,eligible=0,jointStates=0,jointActions=0,rootActions=0;
        int alternativeWins=0;SearchCounters total;std::string prefix;
        for(std::size_t ci=0;ci<commands.size();++ci) {
            const int command=commands[ci];
            if(command>0) {
                ++placement;const auto domain=h::candidates(rollin,command);
                const bool can=h::eligible(rollin) && domain.size()>1;if(can)++eligible;
                if(can && selected<h::MaxLabelStates && placement-lastSelected>=h::SamplePlacementStride) {
                    lastSelected=placement;++selected;
                    const auto key=h::physicalKey(rollin),observable=prefix+"|"+key+"|L="+std::to_string(command);
                    labels<<"{\"schema\":\"pipes-hindsight-v3\",\"feature_schema\":"<<quote(h::FeatureSchema)<<",\"input\":"<<quote(input)<<",\"command_index\":"<<ci
                          <<",\"placement_index\":"<<placement<<",\"length\":"<<command<<",\"live\":"<<rollin.live
                          <<",\"trench\":"<<rollin.trench<<",\"state_key\":"<<quote(key)<<",\"state_hash\":"<<quote(h::hashKey(key))
                          <<",\"observable_key\":"<<quote(observable)<<",\"observable_hash\":"<<quote(h::hashKey(observable))<<",\"actions\":[";
                    bool joint=false;Meter bfJoint=0,bestCost=std::numeric_limits<Meter>::max();
                    for(std::size_t ai=0;ai<domain.size();++ai) {
                        const auto& a=domain[ai];const auto r=search(rollin,static_cast<int>(ci),a,commands);++rootActions;addCounters(total,r.c);
                        if(ai==0)bfJoint=r.cost;
                        if(r.cost<r.bfCost) {joint=true;++jointActions;}
                        bestCost=std::min(bestCost,r.cost);
                        if(ai)labels<<',';
                        labels<<"{\"index\":"<<ai<<",\"start\":"<<a.start<<",\"digs\":"<<a.digs<<",\"cost\":"<<r.cost
                              <<",\"bf_suffix_cost\":"<<r.bfCost<<",\"beam_best_cost\":"<<r.beamCost<<",\"used_reference\":"<<(r.reference?"true":"false")
                              <<",\"features\":[";
                        const auto x=h::scoringFeatures(rollin,command,a);for(std::size_t j=0;j<x.size();++j){if(j)labels<<',';labels<<x[j];}
                        labels<<"],\"counters\":";emitCounters(labels,r.c);labels<<",\"witness\":[";
                        for(std::size_t j=0;j<r.path.size();++j) {if(j)labels<<',';const auto& p=r.path[j];labels<<"{\"command_index\":"<<p.commandIndex<<",\"start\":"<<p.action.start<<",\"digs\":"<<p.action.digs<<'}';}
                        labels<<"]}";
                    }
                    if(joint)++jointStates;if(bestCost<bfJoint)++alternativeWins;
                    labels<<"],\"joint_improvement\":"<<(joint?"true":"false")<<",\"best_cost\":"<<bestCost<<",\"bf_root_joint_cost\":"<<bfJoint<<"}\n";
                }
                rollin.place(command,rollin.greedy(command));
            } else rollin.remove(-command);
            prefix+=std::to_string(command)+',';
        }
        report<<"{\"schema\":\"pipes-hindsight-v3\",\"input\":"<<quote(input)<<",\"commands\":"<<n<<",\"weight\":"<<weight
              <<",\"beam_width\":"<<h::BeamWidth<<",\"max_actions\":"<<h::MaxActions<<",\"sampling\":\"first8_ambiguity_stride3placements\""
              <<",\"eligible_states\":"<<eligible<<",\"labeled_states\":"<<selected<<",\"root_actions\":"<<rootActions
              <<",\"joint_improvement_states\":"<<jointStates<<",\"joint_improvement_actions\":"<<jointActions
              <<",\"alternative_root_better_states\":"<<alternativeWins<<",\"bf_rollin_final_trench\":"<<rollin.trench<<",\"optimality_claim\":false,\"counters\":";
        emitCounters(report,total);report<<"}\n";
        labels.flush();report.flush();if(!labels || !report)throw std::runtime_error("output write failed");
        std::cerr<<"teacher labeled="<<selected<<" roots="<<rootActions<<" joint_states="<<jointStates<<" expanded="<<total.expanded<<'\n';
    } catch(const std::exception& e) {std::cerr<<"teacher error: "<<e.what()<<'\n';return 2;}
}
