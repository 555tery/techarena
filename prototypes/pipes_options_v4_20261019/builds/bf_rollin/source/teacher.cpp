#include "policy.hpp"
#ifndef MODEL_HEADER
#define MODEL_HEADER "model.hpp"
#endif
#include MODEL_HEADER
#include <fstream>
#include <iostream>
#include <tuple>
#include <unordered_set>
namespace h=options_v4;
using h::State;using h::Meter;
struct Step {int commandIndex;h::Choice choice;};
struct Node {State state;std::size_t index=0;int blocks=0;std::vector<Step> path;};
struct SearchCounters {std::uint64_t expanded=0,generated=0,deduplicated=0,pruned_bound=0,pruned_width=0,completed=0;};
struct Result {Meter cost=0,referenceCost=0,beamCost=-1;bool usedReference=true;std::vector<Step> path,reference;SearchCounters counters;};
static std::array<double,4> zeros(const std::array<float,128>&){return {{0,0,0,0}};}
static std::string quote(const std::string& s) {
    std::ostringstream out;out<<'"';
    for(unsigned char c:s){if(c=='"'||c=='\\')out<<'\\'<<c;else if(c<32)out<<"\\u"<<std::hex<<std::setw(4)<<std::setfill('0')<<(int)c<<std::dec;else out<<c;}
    out<<'"';return out.str();
}
static void emitPath(std::ostream& out,const std::vector<Step>& path) {
    out<<'[';for(std::size_t i=0;i<path.size();++i){if(i)out<<',';const auto& p=path[i];
        out<<"{\"command_index\":"<<p.commandIndex<<",\"start\":"<<p.choice.action.start<<",\"digs\":"<<p.choice.action.digs
           <<",\"option\":"<<p.choice.option<<",\"block_id\":"<<p.choice.block<<",\"boundary\":"<<(p.choice.boundary?"true":"false")
           <<",\"continuation\":"<<(p.choice.continuation?"true":"false")<<'}';}out<<']';
}
static void emitCounters(std::ostream& out,const h::Counters& c) {
    out<<"{\"placements\":"<<c.placements<<",\"eligible_placements\":"<<c.eligible_placements<<",\"decisions\":"<<c.decisions
       <<",\"non_bf_options\":"<<c.non_bf_options<<",\"continuation_placements\":"<<c.continuation_placements
       <<",\"changes\":"<<c.changes<<",\"cancellations\":"<<c.cancellations<<",\"active_crossed_deletions\":"<<c.active_crossed_deletions<<",\"fallback\":"<<c.fallback<<'}';
}
// One option block; cancellation ends it, and deterministic out-of-domain BF
// commands are absorbed until the next eligible natural option boundary.
static Node advanceBlock(Node n,int option,const std::vector<int>& commands) {
    h::Cursor cursor;cursor.block=n.blocks-1;h::Counters ignored;bool started=false;
    while(n.index<commands.size()) {
        const int command=commands[n.index];
        if(command>0) {
            if(started && cursor.remaining==0 && h::eligible(n.state))break;
            const auto c=h::choose(n.state,command,cursor,ignored,zeros,false,option);
            if(c.boundary)started=true;
            n.state.place(command,c.action);n.path.push_back({static_cast<int>(n.index),c});
        } else {n.state.remove(-command);h::afterDeletion(n.state,cursor,ignored);}
        ++n.index;
    }
    n.blocks=cursor.block+1;return n;
}
static Meter fragmentation(const State& s) {
    Meter small=0;for(const auto& g:s.gaps)if(g.second-g.first<8)small+=8-(g.second-g.first);
    return static_cast<Meter>(s.gaps.size())*1000+small;
}
static std::string nodeKey(const Node& n){return std::to_string(n.index)+"|"+h::physicalKey(n.state);}
static bool better(const Node& a,const Node& b) {
    return std::make_tuple(a.state.trench,fragmentation(a.state),nodeKey(a))<std::make_tuple(b.state.trench,fragmentation(b.state),nodeKey(b));
}
static Result search(const State& before,std::size_t index,int option,const std::vector<int>& commands) {
    Result r;Node initial{before,index,0,{}};initial=advanceBlock(std::move(initial),option,commands);
    Node reference=initial;
    while(reference.index<commands.size())reference=advanceBlock(std::move(reference),0,commands);
    reference.state.validate();r.referenceCost=reference.state.trench;r.reference=reference.path;r.cost=r.referenceCost;r.path=r.reference;
    std::vector<Node> beam{initial};
    while(true) {
        bool unfinished=false;std::vector<Node> next;
        for(const auto& parent:beam) {
            if(parent.index==commands.size()){next.push_back(parent);continue;}
            unfinished=true;++r.counters.expanded;
            for(int childOption=0;childOption<4;++childOption) {
                ++r.counters.generated;Node child=advanceBlock(parent,childOption,commands);
                if(child.state.trench>r.referenceCost){++r.counters.pruned_bound;continue;}
                next.push_back(std::move(child));
            }
        }
        if(!unfinished)break;
        std::sort(next.begin(),next.end(),better);std::unordered_set<std::string> keys;beam.clear();
        for(auto& child:next) {
            if(!keys.insert(nodeKey(child)).second){++r.counters.deduplicated;continue;}
            if(beam.size()<h::BeamWidth)beam.push_back(std::move(child));else ++r.counters.pruned_width;
        }
        if(beam.empty())break;
    }
    for(const auto& node:beam)if(node.index==commands.size())++r.counters.completed;
    if(!beam.empty()) {
        std::sort(beam.begin(),beam.end(),better);beam.front().state.validate();r.beamCost=beam.front().state.trench;
        if(r.beamCost<r.cost){r.cost=r.beamCost;r.path=beam.front().path;r.usedReference=false;}
    }
    return r;
}
int main(int argc,char** argv) {
    try {
        std::string input,output,stats;
        for(int i=1;i<argc;++i){const std::string a=argv[i];if(i+1>=argc)throw std::runtime_error("expected --input FILE --output FILE --stats FILE");
            if(a=="--input")input=argv[++i];else if(a=="--output")output=argv[++i];else if(a=="--stats")stats=argv[++i];else throw std::runtime_error("unknown argument");}
        if(input.empty()||output.empty()||stats.empty())throw std::runtime_error("required --input --output --stats");
        std::ifstream in(input);double weight;int n;
        if(!(in>>weight>>n)||!std::isfinite(weight)||n<1||n>h::MaxCommands)throw std::runtime_error("input must have 1..128 commands");
        std::vector<int> commands(static_cast<std::size_t>(n));for(int& c:commands)if(!(in>>c)||c==0||c>40)throw std::runtime_error("invalid command");
        int zero;std::string extra;if(!(in>>zero)||zero!=0||(in>>extra))throw std::runtime_error("expected final zero and EOF");
        State check;for(int c:commands){if(c>0)check.place(c,check.greedy(c));else check.remove(-c);}check.validate();
        std::ofstream labels(output),report(stats);if(!labels||!report)throw std::runtime_error("cannot open outputs");labels<<std::setprecision(17);report<<std::setprecision(17);
        State rollin;h::Cursor cursor;h::Counters counters;std::vector<Step> actual;std::string prefix;int placement=0,selected=0,informative=0;
        for(std::size_t ci=0;ci<commands.size();++ci) {
            const int command=commands[ci];
            if(command>0) {
                ++placement;const auto choice=h::choose(rollin,command,cursor,counters,h::predict,h::ModelTrained);
                if(choice.boundary && selected<h::MaxLabelStates) {
                    ++selected;const auto physical=h::physicalKey(rollin),observable=prefix+"|"+physical+"|L="+std::to_string(command);
                    const auto x=h::features(rollin,command);std::array<Result,4> results;
                    for(int o=0;o<4;++o)results[static_cast<std::size_t>(o)]=search(rollin,ci,o,commands);
                    bool differs=false;for(int o=1;o<4;++o)if(results[o].cost!=results[0].cost)differs=true;if(differs)++informative;
                    labels<<"{\"schema\":\"pipes-options-v4\",\"feature_schema\":"<<quote(h::FeatureSchema)<<",\"input\":"<<quote(input)
                      <<",\"model_provenance\":"<<quote(h::ModelProvenance)<<",\"command_index\":"<<ci<<",\"placement_index\":"<<placement<<",\"length\":"<<command
                      <<",\"live\":"<<rollin.live<<",\"trench\":"<<rollin.trench<<",\"state_key\":"<<quote(physical)<<",\"state_hash\":"<<quote(h::hashKey(physical))
                      <<",\"observable_key\":"<<quote(observable)<<",\"observable_hash\":"<<quote(h::hashKey(observable))<<",\"rollin_option\":"<<choice.option
                      <<",\"rollin_block_id\":"<<choice.block<<",\"features\":[";
                    for(std::size_t j=0;j<x.size();++j){if(j)labels<<',';labels<<x[j];}labels<<"],\"gains\":[";
                    for(int o=0;o<4;++o){if(o)labels<<',';labels<<static_cast<double>(results[0].cost-results[o].cost)/20.0;}labels<<"],\"options\":[";
                    for(int o=0;o<4;++o) {
                        if(o)labels<<',';const auto& r=results[o];labels<<"{\"index\":"<<o<<",\"cost\":"<<r.cost<<",\"reference_cost\":"<<r.referenceCost
                          <<",\"bf_suffix_cost\":"<<r.referenceCost<<",\"beam_best_cost\":"<<r.beamCost<<",\"used_reference\":"<<(r.usedReference?"true":"false")
                          <<",\"witness\":";emitPath(labels,r.path);labels<<",\"reference_witness\":";emitPath(labels,r.reference);
                        labels<<",\"search_counters\":{\"expanded\":"<<r.counters.expanded<<",\"generated\":"<<r.counters.generated
                          <<",\"deduplicated\":"<<r.counters.deduplicated<<",\"pruned_bound\":"<<r.counters.pruned_bound<<",\"pruned_width\":"<<r.counters.pruned_width
                          <<",\"completed\":"<<r.counters.completed<<"}}";
                    }
                    labels<<"],\"prefix_witness\":";emitPath(labels,actual);labels<<"}\n";
                }
                rollin.place(command,choice.action);actual.push_back({static_cast<int>(ci),choice});
            } else {rollin.remove(-command);h::afterDeletion(rollin,cursor,counters);}
            prefix+=std::to_string(command)+',';
        }
        rollin.validate();report<<"{\"schema\":\"pipes-options-v4-stats\",\"input\":"<<quote(input)<<",\"model_provenance\":"<<quote(h::ModelProvenance)
          <<",\"commands\":"<<n<<",\"weight\":"<<weight<<",\"beam_width\":"<<h::BeamWidth<<",\"option_hold\":"<<OPTION_HOLD<<",\"labeled_states\":"<<selected
          <<",\"informative_states\":"<<informative<<",\"sampling\":\"first8_natural_eligible_option_boundaries\",\"rollin_final_trench\":"<<rollin.trench
          <<",\"rollin_counters\":";emitCounters(report,counters);report<<",\"rollin_witness\":";emitPath(report,actual);report<<",\"optimality_claim\":false}\n";
        labels.flush();report.flush();if(!labels||!report)throw std::runtime_error("output write failed");
        std::cerr<<"teacher labeled="<<selected<<" informative="<<informative<<" rollin_non_bf="<<counters.non_bf_options<<'\n';
    } catch(const std::exception& e){std::cerr<<"teacher error: "<<e.what()<<'\n';return 2;}
}
