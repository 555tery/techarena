// Causal, paired counterfactual search. No public-test suffix is used here.
// Persistent interval trees share unchanged gaps between simulated trajectories.
#include <ctime>
#include <climits>
#include <numeric>

namespace robust_search {
using U = uint32_t;
struct Exhausted {};
struct Node { U left=0,right=0,priority=0; int start=0,end=0,maxGap=0; };
static_assert(sizeof(Node)==24);

struct Arena {
    // 80 MiB node arena, 128 MiB memo, and delayed real-suffix probes.
    // public replay pays neither cost. Leave RSS margin for live state/tables.
    static constexpr size_t cap=80u*1024u*1024u/sizeof(Node);
    vector<Node> a;
    size_t highWater=0;
    Arena(){a.reserve(cap);a.push_back({});}
    void reset(){highWater=max(highWater,a.size());a.resize(1);}
    U put(Node n){if(a.size()>=cap)throw Exhausted{};a.push_back(n);return U(a.size()-1);}
    U copy(U p){return put(a[p]);}
    static U hash(U x){x^=x>>16;x*=0x7feb352dU;x^=x>>15;x*=0x846ca68bU;return x^(x>>16);}
    U leaf(int l,int r,bool bySize){return put({0,0,hash(U(l)^U(r-l)*0x9e3779b9U^(bySize?0x85ebca6bU:0)),l,r,r-l});}
    void pull(U p){a[p].maxGap=max({a[p].end-a[p].start,a[a[p].left].maxGap,a[a[p].right].maxGap});}
    // Explicit key comparisons avoid temporary tree allocations in searches.
    static bool keyLess(int l,int r,int x,int y,bool sz){return sz?pair(r-l,l)<pair(y-x,x):l<x;}
    pair<U,U> divide(U p,int l,int r,bool sz){
        if(!p)return {0,0};
        U q=copy(p);
        if(keyLess(a[p].start,a[p].end,l,r,sz)){
            auto [x,y]=divide(a[p].right,l,r,sz);a[q].right=x;pull(q);return {q,y};
        }
        auto [x,y]=divide(a[p].left,l,r,sz);a[q].left=y;pull(q);return {x,q};
    }
    U merge(U x,U y){
        if(!x||!y)return x?x:y;
        if(a[x].priority<a[y].priority){U q=copy(x);U z=merge(a[x].right,y);a[q].right=z;pull(q);return q;}
        U q=copy(y);U z=merge(x,a[y].left);a[q].left=z;pull(q);return q;
    }
    U insert(U p,U n,bool sz){
        if(!p)return n;
        if(a[n].priority<a[p].priority){
            auto [x,y]=divide(p,a[n].start,a[n].end,sz);a[n].left=x;a[n].right=y;pull(n);return n;
        }
        U q=copy(p);
        if(keyLess(a[n].start,a[n].end,a[p].start,a[p].end,sz)){
            U z=insert(a[p].left,n,sz);a[q].left=z;
        }else{U z=insert(a[p].right,n,sz);a[q].right=z;}
        pull(q);return q;
    }
    U erase(U p,int l,int r,bool sz){
        if(!p)throw runtime_error("counterfactual gap missing");
        if(a[p].start==l&&a[p].end==r)return merge(a[p].left,a[p].right);
        U q=copy(p);
        if(keyLess(l,r,a[p].start,a[p].end,sz)){U z=erase(a[p].left,l,r,sz);a[q].left=z;}
        else{U z=erase(a[p].right,l,r,sz);a[q].right=z;}
        pull(q);return q;
    }
    U before(U p,int x)const{U found=0;while(p){if(a[p].start<=x){found=p;p=a[p].right;}else p=a[p].left;}return found;}
    U after(U p,int x)const{U found=0;while(p){if(a[p].start>=x){found=p;p=a[p].left;}else p=a[p].right;}return found;}
    U best(U p,int n)const{U found=0;while(p){if(a[p].end-a[p].start>=n){found=p;p=a[p].left;}else p=a[p].right;}return found;}
    U first(U p,int n)const{
        if(!p||a[p].maxGap<n)return 0;
        while(p){if(a[a[p].left].maxGap>=n)p=a[p].left;else if(a[p].end-a[p].start>=n)return p;else p=a[p].right;}return 0;
    }
};

struct Layout {
    Arena* arena; U startRoot=0,sizeRoot=0; int T=0;
    void rawAdd(int l,int r){if(l>=r)return;U n=arena->leaf(l,r,false);startRoot=arena->insert(startRoot,n,false);n=arena->leaf(l,r,true);sizeRoot=arena->insert(sizeRoot,n,true);}
    void eraseGap(int l,int r){startRoot=arena->erase(startRoot,l,r,false);sizeRoot=arena->erase(sizeRoot,l,r,true);}
    void release(int l,int r){
        U p=arena->before(startRoot,l);
        if(p&&arena->a[p].end==l){int x=arena->a[p].start;eraseGap(x,l);l=x;}
        p=arena->after(startRoot,l);
        if(p&&arena->a[p].start==r){int y=arena->a[p].end;eraseGap(r,y);r=y;}
        rawAdd(l,r);
    }
    int bf(int n,int policy=0)const{
        U p=policy==1?arena->first(startRoot,n):arena->best(sizeRoot,n);
        if(p)return arena->a[p].start;
        p=arena->before(startRoot,T);
        return p&&arena->a[p].end==T?arena->a[p].start:T;
    }
    void place(int n,int x){
        if(x+n>T){int old=T;T=20*((x+n+19)/20);release(old,T);}
        U p=arena->before(startRoot,x);
        if(!p||arena->a[p].end<x+n)throw runtime_error("counterfactual overlap");
        int l=arena->a[p].start,r=arena->a[p].end;eraseGap(l,r);rawAdd(l,x);rawAdd(x+n,r);
    }
};

struct Event {int length=0,rank=0,exact=0;};
uint64_t mix64(uint64_t x){x^=x>>30;x*=0xbf58476d1ce4e5b9ULL;x^=x>>27;x*=0x94d049bb133111ebULL;return x^(x>>31);}
uint64_t pipeHash(int pid,int x,int n,uint64_t salt){return mix64(uint64_t(pid)*0x9e3779b97f4a7c15ULL^uint64_t(x)*0x632be59bd9b4e019ULL^uint64_t(n)*salt);}
struct MemoEntry {uint64_t a=0,b=0;int trench=0;uint32_t occupied=0;};
static_assert(sizeof(MemoEntry)==24);
struct alignas(64) MemoBucket {MemoEntry slots[2];};
static_assert(sizeof(MemoBucket)==64);
struct Memo {
    // Two entries per cache line. LRU replacement retains recurring suffixes.
    static constexpr size_t count=1u<<21;
    vector<MemoBucket> table{count};
    uint64_t hits=0,queries=0,stores=0;uint32_t tick=0;
    int get(uint64_t a,uint64_t b){++queries;for(auto& e:table[a&(count-1)].slots)if(e.occupied&&e.a==a&&e.b==b){++hits;e.occupied=++tick;return e.trench;}return -1;}
    void put(uint64_t a,uint64_t b,int T){auto& bucket=table[a&(count-1)];int slot=0;
        if(bucket.slots[1].a==a&&bucket.slots[1].b==b)slot=1;
        else if(!(bucket.slots[0].a==a&&bucket.slots[0].b==b)&&bucket.slots[1].occupied<bucket.slots[0].occupied)slot=1;
        bucket.slots[slot]={a,b,T,++tick};++stores;
    }
};
struct Scenario {vector<int> commands;int policy=0;array<uint64_t,129> suffixA{},suffixB{};};
struct Fenwick {
    vector<int> b;
    explicit Fenwick(int n):b(n+1){}
    void add(int x,int d){for(;x<int(b.size());x+=x&-x)b[x]+=d;}
    int sum(int x)const{int r=0;for(;x;x-=x&-x)r+=b[x];return r;}
    int kth(int k)const{int p=0;for(int d=1<<18;d;d>>=1)if(p+d<int(b.size())&&b[p+d]<k){k-=b[p+d];p+=d;}return p+1;}
};

class Planner {
    struct Probe {unique_ptr<Allocator> state;size_t step;int length,baseline,proposed;};
    vector<Event> history;
    vector<int> observedCommands;
    deque<Probe> pending;
    Fenwick actualRanks{200002};
    vector<int> activeIds;
    int live=0,nextPid=0,placements=0;
    double usedCpu=0;
    double startCpu=double(clock())/CLOCKS_PER_SEC;
    unique_ptr<Arena> arena;
    unique_ptr<Memo> memo;
    uint64_t physicalA=0,physicalB=0;
    uint64_t savedQueries=0,savedHits=0,savedStores=0;unsigned releases=0;bool scratchDisabled=false;
    int confidence=0;
    void releaseScratch(){
        pending.clear();
        if(memo){savedQueries+=memo->queries;savedHits+=memo->hits;savedStores+=memo->stores;memo.reset();++releases;}
        if(arena){peakNodes=max(peakNodes,arena->a.size());arena.reset();}
    }
    void stopForScale(){if(memo||arena)scratchDisabled=true;releaseScratch();}
    uint32_t rng=0x31415927;
    static double cpu(){return double(clock())/CLOCKS_PER_SEC;}
    double headroom(double currentSearch=0)const{
        // N is not revealed. Reserve for the maximum legal remaining stream,
        // including interactive I/O and map maintenance. A fixed search budget
        // alone is unsafe: ordinary processing can exceed two CPU seconds.
        double now=cpu(),seen=max<size_t>(1,history.size());
        double ordinary=max(0.0,now-startCpu-usedCpu-currentSearch);
        double rate=max(0.000016,ordinary/seen);
        double reserve=max(0.0,200000.0-seen)*rate;
        return 4.35-now-reserve;
    }
    uint32_t random(){rng^=rng<<13;rng^=rng>>17;rng^=rng<<5;return rng;}
    vector<Scenario> scenarios(const Allocator& actual,int request){
        constexpr int count=64,depth=128;
        vector<Scenario> out;out.reserve(count);
        int N=int(history.size()),window=min(N,8192);
        vector<int> starts;
        for(int context=4;context>=1&&starts.size()<8;--context){
            starts.clear();
            for(int s=max(context,N-window);s+depth<N;++s){
                bool same=true;
                for(int k=0;k<context&&same;++k){
                    auto a=history[N-context+k],b=history[s-context+k];
                    same=a.length==b.length&&(a.length>0||abs(a.rank-b.rank)<128);
                }
                if(same)starts.push_back(s);
            }
        }
        activeIds.clear();activeIds.reserve(live+depth+1);
        for(int id=1;id<int(actual.pipes.size());++id)if(actual.pipes[id].second)activeIds.push_back(id);
        const int base=int(actual.pipes.size());activeIds.push_back(base);
        array<int,41> freq{};
        for(int i=max(0,N-512);i<N;++i)if(history[i].length>0)++freq[history[i].length];
        int common=int(max_element(freq.begin()+1,freq.end())-freq.begin());
        for(int trial=0;trial<count;++trial){
            Scenario sc;sc.policy=trial%8==7?1:0;sc.commands.reserve(depth);
            Fenwick ranks(base+depth+3);for(int id:activeIds)ranks.add(id,1);
            int alive=int(activeIds.size()),pid=base;
            int begin=starts.empty()?max(0,N-window)+int(random()%max(1,window-depth)):starts[random()%starts.size()];
            for(int k=0;k<depth;++k){
                Event ev=history[min(begin+k,N-1)];
                // Contiguous blocks retain observed deletion/size correlation.
                // Eight distribution-shift probes add no-deletion size bursts.
                if(trial>=40&&trial<48){ev.length=trial<44?(trial%2?40:common):(trial%2?request:1);}
                if(ev.length>0){sc.commands.push_back(ev.length);ranks.add(++pid,1);++alive;}
                else if(alive){
                    int rank=ev.exact>=0?min(alive-1,ev.exact):int(int64_t(ev.rank)*(alive-1)/1000);
                    if(trial>=48){if(trial%4==0)rank=0;else if(trial%4==1)rank=alive-1;else if(trial%4==2)rank=alive-1-rank;else rank=int(random()%alive);}
                    int id=ranks.kth(alive-rank);ranks.add(id,-1);--alive;sc.commands.push_back(-id);
                }
            }
            sc.suffixA[depth]=0x517cc1b727220a95ULL;sc.suffixB[depth]=0x6eed0e9da4d94a4fULL;
            // Every generated scenario currently has exactly depth commands.
            // The guard also supports a shorter all-empty history safely.
            size_t size=sc.commands.size();sc.suffixA[size]=0x517cc1b727220a95ULL;sc.suffixB[size]=0x6eed0e9da4d94a4fULL;
            for(size_t k=size;k-->0;){sc.suffixA[k]=mix64(uint64_t(int64_t(sc.commands[k]))+0x9e3779b97f4a7c15ULL*sc.suffixA[k+1]);sc.suffixB[k]=mix64(uint64_t(int64_t(sc.commands[k]))+0x632be59bd9b4e019ULL*sc.suffixB[k+1]);}
            out.push_back(std::move(sc));
        }
        return out;
    }
    vector<int> actions(const Allocator& s,int n,int baseline){
        vector<int> a{baseline};int digs=max(0,(baseline+n-s.T+19)/20);
        auto add=[&](int x){if(x>=0&&max(0,(x+n-s.T+19)/20)<=digs&&find(a.begin(),a.end(),x)==a.end())a.push_back(x);};
        int count=0;
        for(auto it=s.sizes.lower_bound({n,-1});it!=s.sizes.end()&&count<5;++it,++count){int l=it->second,r=l+it->first;add(l);add(r-n);}
        for(auto [l,r]:s.g)if(r-l>=n){add(l);add(r-n);break;}
        for(auto it=s.g.rbegin();it!=s.g.rend();++it)if(it->second-it->first>=n){add(it->first);add(it->second-n);break;}
        if(!s.g.empty()&&s.g.rbegin()->second==s.T)add(s.g.rbegin()->first);
        if(a.size()>16)a.resize(16);
        return a;
    }
    int simulate(Layout s,int x,int n,const Scenario& sc,const Allocator& actual){
        s.place(n,x);int base=int(actual.pipes.size());
        array<pair<int,int>,130> predicted{};predicted[0]={x,n};int count=1;
        uint64_t a=physicalA^pipeHash(base,x,n,0x94d049bb133111ebULL);
        uint64_t b=physicalB^pipeHash(base,x,n,0xbf58476d1ce4e5b9ULL);
        array<pair<uint64_t,uint64_t>,17> visited{};int visits=0,answer=-1;
#if defined(ROBUST_VERIFY_MEMO)
        int expected=-1;
#endif
        for(size_t k=0;k<sc.commands.size();++k){
            if(k%8==0){
                uint64_t ka=mix64(a^uint64_t(s.T)*0xd6e8feb86659fd93ULL^uint64_t(base+count)*0x517cc1b727220a95ULL^uint64_t(sc.policy))^sc.suffixA[k];
                uint64_t kb=mix64(b^uint64_t(s.T)*0xa0761d6478bd642fULL^uint64_t(base+count)*0x6eed0e9da4d94a4fULL^uint64_t(sc.policy))^sc.suffixB[k];
                int hit=memo->get(ka,kb);
                if(hit>=0){
#if defined(ROBUST_VERIFY_MEMO)
                    if(expected>=0&&hit!=expected)throw runtime_error("memo inconsistent suffix");expected=hit;
#else
                    answer=hit;break;
#endif
                }
                visited[visits++]={ka,kb};
            }
            int c=sc.commands[k];
            if(c>0){int pos=s.bf(c,sc.policy);s.place(c,pos);int id=base+count;predicted[count++]={pos,c};a^=pipeHash(id,pos,c,0x94d049bb133111ebULL);b^=pipeHash(id,pos,c,0xbf58476d1ce4e5b9ULL);}
            else{int id=-c;auto p=id<base?actual.pipes[id]:predicted[id-base];s.release(p.first,p.first+p.second);a^=pipeHash(id,p.first,p.second,0x94d049bb133111ebULL);b^=pipeHash(id,p.first,p.second,0xbf58476d1ce4e5b9ULL);}
            ++simulatedEvents;
        }
        if(answer<0)answer=s.T;
#if defined(ROBUST_VERIFY_MEMO)
        if(expected>=0&&answer!=expected)throw runtime_error("memo terminal mismatch");
#endif
        for(int i=0;i<visits;++i)memo->put(visited[i].first,visited[i].second,answer);
        return answer;
    }
    void checkDelayed(){
        if(pending.empty()||pending.front().step+129>observedCommands.size())return;
        if(!arena||!memo){pending.clear();return;}
        if(pending.front().step+512<observedCommands.size()){pending.pop_front();confidence=0;return;}
        if(headroom()<0.02)return;
        auto probe=std::move(pending.front());pending.pop_front();double begin=cpu();
        try{
            Scenario sc;sc.commands.assign(observedCommands.begin()+probe.step+1,observedCommands.begin()+probe.step+129);
            sc.suffixA[128]=0x517cc1b727220a95ULL;sc.suffixB[128]=0x6eed0e9da4d94a4fULL;
            for(int k=127;k>=0;--k){sc.suffixA[k]=mix64(uint64_t(int64_t(sc.commands[k]))+0x9e3779b97f4a7c15ULL*sc.suffixA[k+1]);sc.suffixB[k]=mix64(uint64_t(int64_t(sc.commands[k]))+0x632be59bd9b4e019ULL*sc.suffixB[k+1]);}
            const auto& state=*probe.state;physicalA=physicalB=0;
            for(size_t id=1;id<state.pipes.size();++id)if(state.pipes[id].second){auto [x,n]=state.pipes[id];physicalA^=pipeHash(int(id),x,n,0x94d049bb133111ebULL);physicalB^=pipeHash(int(id),x,n,0xbf58476d1ce4e5b9ULL);}
            arena->reset();Layout initial{arena.get(),0,0,state.T};for(auto [l,r]:state.g)initial.rawAdd(l,r);
            int ordinary=simulate(initial,probe.baseline,probe.length,sc,state);
            int alternative=simulate(initial,probe.proposed,probe.length,sc,state);
            if(alternative<ordinary){++verifiedWins;confidence=min(8,confidence+2);}
            else if(alternative==ordinary){++verifiedTies;confidence=min(8,confidence+1);}
            else{++verifiedLosses;confidence=max(0,confidence-4);}
            peakNodes=max(peakNodes,arena->a.size());arena->reset();
        }catch(const Exhausted&){confidence=0;++aborted;arena->reset();}
        usedCpu+=cpu()-begin;
        if(usedCpu>3.4||cpu()>4.1)releaseScratch();
    }
public:
    unsigned decisions=0,changes=0,aborted=0;uint64_t simulatedEvents=0,logicalEvents=0;size_t peakNodes=0;
    unsigned proposalsMade=0,verifiedWins=0,verifiedTies=0,verifiedLosses=0;
    void observe(int command,size_t gapCount=0){
        observedCommands.push_back(command);
        if(command>0){actualRanks.add(++nextPid,1);++live;++placements;history.push_back({command,0,0});}
        else{
            int rank=live-actualRanks.sum(-command);
            int exact=rank<=16?rank:-1;
            history.push_back({0,live>1?int(int64_t(rank)*1000/(live-1)):0,exact});
            actualRanks.add(-command,-1);--live;
        }
        // Do not retain a large search workspace while the physical allocator
        // grows beyond the size on which this planner is allowed to operate.
        if(live>8192||gapCount>4096)stopForScale();
        checkDelayed();
    }
    int choose(const Allocator& actual,int n,int baseline){
#if defined(ROBUST_TEST_DECISIONS)
        if(decisions>=ROBUST_TEST_DECISIONS)return baseline;
#endif
        // Bounded search is reserved for genuinely different placements. Work
        // is periodically sampled, rather than exhausting the budget at start.
        if(history.size()<256)return baseline;
        if(scratchDisabled)return baseline;
        if(live>8192||actual.g.size()>4096){stopForScale();return baseline;}
        if(logicalEvents>=12000000||usedCpu>3.4||cpu()>4.1){releaseScratch();return baseline;}
        if(placements%16!=0)return baseline;
        // Avoid repeatedly starting batches as small time credits arrive.
        if(headroom()<0.04)return baseline;
        double begin=cpu();auto candidates=actions(actual,n,baseline);
        if(candidates.size()<2){usedCpu+=cpu()-begin;return baseline;}
        int answer=baseline;
        try{
            auto futures=scenarios(actual,n);
            if(!arena)arena=make_unique<Arena>();arena->reset();
            if(!memo)memo=make_unique<Memo>();
            physicalA=physicalB=0;
            for(int id:activeIds)if(id<int(actual.pipes.size())){auto [x,L]=actual.pipes[id];physicalA^=pipeHash(id,x,L,0x94d049bb133111ebULL);physicalB^=pipeHash(id,x,L,0xbf58476d1ce4e5b9ULL);}
            Layout initial{arena.get(),0,0,actual.T};for(auto [l,r]:actual.g)initial.rawAdd(l,r);
            vector<vector<int>> outcome(candidates.size());bool complete=true;
            for(size_t a=0;a<candidates.size()&&complete;++a){
                for(const auto& sc:futures){
                    outcome[a].push_back(simulate(initial,candidates[a],n,sc,actual));++simulatedEvents;logicalEvents+=sc.commands.size()+1;
                    if((usedCpu+cpu()-begin>3.4)||cpu()>4.1||headroom(cpu()-begin)<0){complete=false;break;}
                }
            }
            ++decisions;
            if(complete){
                int64_t bestSum=0;for(int t:outcome[0])bestSum+=t;
                for(size_t a=1;a<candidates.size();++a){
                    int64_t sum=0;bool safe=true;int empiricalWins=0;
                    for(size_t j=0;j<futures.size();++j){sum+=outcome[a][j];if(outcome[a][j]>outcome[0][j])safe=false;if(j<40&&outcome[a][j]<outcome[0][j])++empiricalWins;}
                    if(safe&&empiricalWins>=3&&sum+int64_t(futures.size())<=bestSum){bestSum=sum;answer=candidates[a];}
                }
            }else ++aborted;
        }catch(const Exhausted&){++aborted;}
        if(arena){peakNodes=max(peakNodes,arena->a.size());arena->reset();}
        if(answer!=baseline){
            ++proposalsMade;
            if(pending.size()<8)pending.push_back(Probe{make_unique<Allocator>(actual),observedCommands.size(),n,baseline,answer});
            else{confidence=0;pending.pop_front();}
            if(confidence<4)answer=baseline;
        }
        usedCpu+=cpu()-begin;if(answer!=baseline)++changes;
        if(logicalEvents>=12000000||usedCpu>3.4||cpu()>4.1)releaseScratch();
        return answer;
    }
    void report()const{fprintf(stderr,"ROBUST_SEARCH decisions=%u changes=%u aborted=%u simulated_events=%llu peak_nodes=%zu node_MiB=%.3f planner_CPU=%.6f\n",decisions,changes,aborted,(unsigned long long)simulatedEvents,peakNodes,peakNodes*24.0/1048576.0,usedCpu);}
    void reportMemo()const{if(memo||releases)fprintf(stderr,"ROBUST_MEMO queries=%llu hits=%llu stores=%llu table_MiB=128 releases=%u logical_events=%llu\n",(unsigned long long)(savedQueries+(memo?memo->queries:0)),(unsigned long long)(savedHits+(memo?memo->hits:0)),(unsigned long long)(savedStores+(memo?memo->stores:0)),releases,(unsigned long long)logicalEvents);}
    void reportValidation()const{fprintf(stderr,"CAUSAL_VALIDATION proposals=%u committed=%u actual_suffix_wins=%u ties=%u losses=%u confidence=%d\n",proposalsMade,changes,verifiedWins,verifiedTies,verifiedLosses,confidence);}
};
}
