#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <deque>
#include <limits>
#include <map>
#include <set>
#include <stdexcept>
#include <utility>
#include <vector>

namespace prototype {
using Meter = std::int64_t;
struct Pipe { Meter start=0; int length=0; int born=0; bool live=false; };
struct Action { Meter start=0; int digs=0; int kind=0; };

class State {
public:
    Meter trench=0, occupied=0, bornSum=0;
    int clock=0, live=0, lastLength=0, sameRun=0;
    std::map<Meter,Meter> gaps;
    std::set<std::pair<Meter,Meter>> sizes;
    std::array<std::set<Meter>,41> startsByLength;
    std::map<Meter,int> byEnd;
    std::vector<Pipe> pipes{Pipe{}};
    std::array<int,41> gapHistogram{}, frequency{};
    std::deque<int> lengths, deletionAges, deletionLengths, eventKinds;

    void eraseGap(std::map<Meter,Meter>::iterator it) {
        const Meter length=it->second-it->first;
        --gapHistogram[static_cast<std::size_t>(std::min<Meter>(40,length))];
        startsByLength[static_cast<std::size_t>(std::min<Meter>(40,length))].erase(it->first);
        sizes.erase({length,it->first}); gaps.erase(it);
    }
    void addGap(Meter start, Meter end) {
        if(start>=end) return;
        auto it=gaps.lower_bound(start);
        if(it!=gaps.begin()) {
            auto previous=std::prev(it);
            if(previous->second>start) throw std::runtime_error("overlapping free spans");
            if(previous->second==start) {
                start=previous->first; eraseGap(previous); it=gaps.lower_bound(start);
            }
        }
        if(it!=gaps.end()) {
            if(it->first<end) throw std::runtime_error("overlapping free spans");
            if(it->first==end) {end=it->second;eraseGap(it);}
        }
        gaps.emplace(start,end); sizes.emplace(end-start,start);
        ++gapHistogram[static_cast<std::size_t>(std::min<Meter>(40,end-start))];
        startsByLength[static_cast<std::size_t>(std::min<Meter>(40,end-start))].insert(start);
    }
    void recordEvent(int kind) {
        eventKinds.push_back(kind);
        if(eventKinds.size()>256) eventKinds.pop_front();
    }
    void place(int length,const Action& action) {
        ++clock;
        if(length<1 || length>40 || action.start<0 || action.digs<0)
            throw std::runtime_error("invalid action values");
        const Meter required=std::max<Meter>(0,action.start+length-trench);
        if(action.digs!=(required+19)/20) throw std::runtime_error("non-minimal digs");
        const Meter newEnd=trench+20*action.digs;
        if(newEnd>100000000) throw std::runtime_error("trench cap");
        if(newEnd>trench) {addGap(trench,newEnd);trench=newEnd;}
        auto it=gaps.upper_bound(action.start);
        if(it==gaps.begin()) throw std::runtime_error("action has no gap");
        --it;
        const Meter left=it->first,right=it->second;
        if(left>action.start || right<action.start+length)
            throw std::runtime_error("overlapping action");
        eraseGap(it); addGap(left,action.start);addGap(action.start+length,right);
        const int pid=static_cast<int>(pipes.size());
        pipes.push_back(Pipe{action.start,length,clock,true});
        byEnd.emplace(action.start+length,pid);
        ++live;occupied+=length;bornSum+=clock;
        lengths.push_back(length);++frequency[static_cast<std::size_t>(length)];
        if(lengths.size()>256) {--frequency[static_cast<std::size_t>(lengths.front())];lengths.pop_front();}
        sameRun=length==lastLength?sameRun+1:1;lastLength=length;recordEvent(1);
    }
    Meter remove(int pid) {
        ++clock;
        if(pid<=0 || static_cast<std::size_t>(pid)>=pipes.size() || !pipes[static_cast<std::size_t>(pid)].live)
            throw std::runtime_error("invalid deletion");
        auto& pipe=pipes[static_cast<std::size_t>(pid)];
        pipe.live=false;byEnd.erase(pipe.start+pipe.length);
        --live;occupied-=pipe.length;bornSum-=pipe.born;
        addGap(pipe.start,pipe.start+pipe.length);
        deletionAges.push_back(clock-pipe.born);deletionLengths.push_back(pipe.length);
        if(deletionAges.size()>256) {deletionAges.pop_front();deletionLengths.pop_front();}
        recordEvent(-1);return pipe.start;
    }
    Action at(Meter coordinate,int length,int kind) const {
        const Meter required=std::max<Meter>(0,coordinate+length-trench);
        return Action{coordinate,static_cast<int>((required+19)/20),kind};
    }
    std::pair<Meter,Meter> tailBounds(int length) const {
        Meter start=trench;
        if(!gaps.empty() && std::prev(gaps.end())->second==trench) start=std::prev(gaps.end())->first;
        const Meter deficit=std::max<Meter>(0,start+length-trench);
        return {start,trench+20*((deficit+19)/20)};
    }
    Action greedy(int length,bool right=false) const {
        const auto it=sizes.lower_bound({length,-1});
        if(it!=sizes.end()) return at(right?it->second+it->first-length:it->second,length,0);
        const auto [start,end]=tailBounds(length);
        return at(right?end-length:start,length,0);
    }
    std::vector<Action> candidates(int length) const {
        std::vector<Action> result;
        const auto append=[&](Action action) {
            if(result.size()>=32) return;
            for(const auto& previous:result)
                if(previous.start==action.start && previous.digs==action.digs) return;
            result.push_back(action);
        };
        append(greedy(length));
        auto fit=sizes.lower_bound({length,-1});
        for(int n=0;fit!=sizes.end() && n<4;++fit,++n) {
            append(at(fit->second,length,1));
            append(at(fit->second+fit->first-length,length,2));
        }
        Meter firstStart=std::numeric_limits<Meter>::max(),lastStart=-1;
        // At most 40 size buckets, independent of the number of physical gaps.
        for(int size=length;size<=40;++size) {
            const auto& starts=startsByLength[static_cast<std::size_t>(size)];
            if(!starts.empty()) {firstStart=std::min(firstStart,*starts.begin());lastStart=std::max(lastStart,*starts.rbegin());}
        }
        if(lastStart>=0) {
            const auto first=gaps.find(firstStart),last=gaps.find(lastStart);
            append(at(first->first,length,3));append(at(first->second-length,length,4));
            append(at(last->first,length,5));append(at(last->second-length,length,6));
        }
        const auto [tailStart,newEnd]=tailBounds(length);
        append(at(tailStart,length,7));append(at(newEnd-length,length,8));
        fit=sizes.lower_bound({length,-1});
        if(fit!=sizes.end()) append(at(fit->second+(fit->first-length)/2,length,9));
        const auto smallDomain=exhaustive(length,32);
        if(!smallDomain.empty()) {
            for(const auto& action:smallDomain) append(action);
            return result;
        }
        fit=sizes.lower_bound({length,-1});
        for(int n=0;fit!=sizes.end() && n<4;++fit,++n) {
            const Meter slack=fit->first-length;
            for(Meter offset:{Meter{1},slack-1,slack/4,3*slack/4}) {
                if(offset>=0 && offset<=slack)append(at(fit->second+offset,length,11));
            }
        }
        return result;
    }
    std::vector<Action> exhaustive(int length,std::size_t cap=256) const {
        std::vector<Action> result;
        // Inspect fitting spans only: many tiny unfit gaps must not cause an
        // O(number-of-gaps) scan at every network decision. Keep address order.
        std::vector<std::pair<Meter,Meter>> fitting;
        std::size_t positions=0;
        for(auto fit=sizes.lower_bound({length,-1});fit!=sizes.end();++fit) {
            const auto count=static_cast<std::size_t>(fit->first-length+1);
            if(count>cap-positions)return {};
            positions+=count;
            fitting.emplace_back(fit->second,fit->second+fit->first);
        }
        std::sort(fitting.begin(),fitting.end());
        for(const auto& [start,end]:fitting) {
            for(Meter position=start;position+length<=end;++position) {
                result.push_back(at(position,length,10));
                if(result.size()>cap) return {};
            }
        }
        const auto [start,end]=tailBounds(length);
        for(Meter position=start;position+length<=end;++position) {
            const auto action=at(position,length,10);
            bool duplicate=false;
            for(const auto& other:result) if(other.start==action.start && other.digs==action.digs) duplicate=true;
            if(!duplicate) result.push_back(action);
            if(result.size()>cap) return {};
        }
        return result;
    }

    std::array<float,128> features(int length,const Action& action) const {
        std::array<float,128> x{};
        const float history=static_cast<float>(std::max<std::size_t>(1,lengths.size()));
        const float gapCount=static_cast<float>(std::max<std::size_t>(1,gaps.size()));
        const float extent=static_cast<float>(std::max<Meter>(20,trench));
        for(std::size_t n=1;n<=40;++n) {
            x[n-1]=static_cast<float>(frequency[n])/history;
            x[39+n]=static_cast<float>(gapHistogram[n])/gapCount;
        }
        const auto clipped=[](Meter value){return std::min(4.0f,static_cast<float>(value)/40.0f);};
        const auto ageFeature=[](double age){return static_cast<float>(std::log1p(std::max(0.0,age))/std::log(200001.0));};
        x[80]=static_cast<float>(length)/40.0f;
        x[81]=ageFeature(live);
        x[82]=static_cast<float>(occupied)/extent;
        x[83]=static_cast<float>(trench-occupied)/extent;
        x[84]=static_cast<float>(gaps.size())/static_cast<float>(std::max(1,live));
        x[85]=sizes.empty()?0:clipped(sizes.rbegin()->first);
        Meter small=0;for(int n=1;n<=7;++n)small+=n*gapHistogram[static_cast<std::size_t>(n)];
        x[86]=static_cast<float>(small)/extent;
        double meanAge=0;for(int age:deletionAges) meanAge+=age;
        const float deletes=static_cast<float>(std::max<std::size_t>(1,deletionAges.size()));
        x[87]=ageFeature(meanAge/deletes);
        for(int age:deletionAges) {if(age<=32)x[88]+=1/deletes;if(age<=256)x[89]+=1/deletes;}
        for(int kind:eventKinds)if(kind>0)x[90]+=1.0f/static_cast<float>(eventKinds.size());
        x[91]=std::min(1.0f,static_cast<float>(sameRun)/64.0f);
        x[92]=ageFeature(live?static_cast<double>(clock)-static_cast<double>(bornSum)/live:0);
        x[93]=static_cast<float>(occupied)/static_cast<float>(std::max(1,live))/40.0f;
        const auto [tailStart,tailEnd]=tailBounds(length);(void)tailEnd;
        x[94]=clipped(trench-tailStart);x[95]=static_cast<float>(lastLength)/40.0f;
        Meter gapStart=tailStart,gapEnd=trench+20*action.digs;
        auto it=gaps.upper_bound(action.start);
        if(it!=gaps.begin()) {--it;if(it->second>=action.start+length || it->second==trench) {gapStart=it->first;gapEnd=std::max(it->second,gapEnd*(action.digs>0));}}
        if(action.digs==0) {
            auto contain=gaps.upper_bound(action.start);--contain;gapStart=contain->first;gapEnd=contain->second;
        }
        const Meter left=action.start-gapStart,right=gapEnd-action.start-length;
        x[96]=static_cast<float>(action.digs)/2.0f;x[97]=clipped(left+right);x[98]=clipped(gapEnd-gapStart);
        x[99]=static_cast<float>(action.start)/extent;x[100]=(gapEnd>=trench)?1:0;
        x[101]=(left+right)>0?static_cast<float>(left)/static_cast<float>(left+right):0;
        x[102]=clipped(left);x[103]=clipped(right);x[104]=(left+right)==0?1:0;
        int misses=0;for(int n=1;n<=40;++n)if(n>left+right)misses+=frequency[static_cast<std::size_t>(n)];
        x[105]=static_cast<float>(misses)/history;
        x[106]=clipped(std::min(left,right));x[107]=static_cast<float>(20*action.digs)/extent;
        int leftPid=0,rightPid=0;
        auto boundary=byEnd.find(gapStart);if(boundary!=byEnd.end())leftPid=boundary->second;
        boundary=byEnd.upper_bound(gapEnd);if(boundary!=byEnd.end() && pipes[static_cast<std::size_t>(boundary->second)].start==gapEnd)rightPid=boundary->second;
        for(int side=0;side<2;++side) {
            const int pid=side==0?leftPid:rightPid;if(!pid)continue;
            const auto& pipe=pipes[static_cast<std::size_t>(pid)];
            x[108+static_cast<std::size_t>(side)]=static_cast<float>(pipe.length)/40.0f;
            x[110+static_cast<std::size_t>(side)]=ageFeature(clock-pipe.born);
            Meter outer=0;
            if(side==0) {auto g=gaps.lower_bound(pipe.start);if(g!=gaps.begin()){--g;if(g->second==pipe.start)outer=g->second-g->first;}}
            else {auto g=gaps.find(pipe.start+pipe.length);if(g!=gaps.end())outer=g->second-g->first;}
            x[112+static_cast<std::size_t>(side)]=clipped(outer);
            x[116+static_cast<std::size_t>(side)]=clipped(pipe.length+outer+(side==0?left:right));
        }
        double lost=0;
        for(int n=1;n<=40;++n)lost+=frequency[static_cast<std::size_t>(n)]*static_cast<double>((gapEnd-gapStart)/n-left/n-right/n)/history;
        x[114]=static_cast<float>(lost/40.0);x[115]=static_cast<float>(length-lastLength)/40.0f;
        x[118]=clipped(left+right+length);x[119]=(left>0 && right>0)?1:0;
        for(std::size_t n=0;n<deletionAges.size();++n) {
            const int age=deletionAges[n],size=deletionLengths[n];
            const std::size_t ab=age<=8?0:(age<=64?1:(age<=512?2:3));
            x[120+ab]+=1/deletes;x[124+static_cast<std::size_t>((size-1)/10)]+=1/deletes;
        }
        for(float value:x)if(!std::isfinite(value))throw std::runtime_error("nonfinite feature");
        return x;
    }
    void validate() const {
        Meter free=0,previous=-1;std::array<int,41> histogram{};
        for(const auto& [start,end]:gaps) {
            if(start<0 || end<=start || end>trench || start<=previous)throw std::runtime_error("gap invariant");
            previous=end;free+=end-start;++histogram[static_cast<std::size_t>(std::min<Meter>(40,end-start))];
            if(!sizes.count({end-start,start}))throw std::runtime_error("size index invariant");
            if(!startsByLength[static_cast<std::size_t>(std::min<Meter>(40,end-start))].count(start))throw std::runtime_error("address index invariant");
        }
        if(free+occupied!=trench || histogram!=gapHistogram || sizes.size()!=gaps.size() || byEnd.size()!=static_cast<std::size_t>(live))throw std::runtime_error("volume invariant");
        Meter last=-1,total=0;int count=0;
        for(const auto& [end,pid]:byEnd) {
            const auto& pipe=pipes[static_cast<std::size_t>(pid)];
            if(!pipe.live || pipe.start<last || end!=pipe.start+pipe.length || end>trench)throw std::runtime_error("pipe invariant");
            last=end;total+=pipe.length;++count;
        }
        if(total!=occupied || count!=live)throw std::runtime_error("live invariant");
    }
};
} // namespace prototype
