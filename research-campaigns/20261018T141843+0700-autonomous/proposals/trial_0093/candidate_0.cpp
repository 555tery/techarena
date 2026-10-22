#include <algorithm>
#include <array>
#include <cstdint>
#include <iostream>
#include <map>
#include <set>
#include <utility>
#include <vector>
using I=std::int64_t;

struct ReclaimIndex {
    struct Node {
        int left=0,right=0;
        I starts=0,ends=0;
    };
    std::vector<Node> nodes=std::vector<Node>(2);
    int root=1;
    I limit=1;

    void update(I position,I startDelta,I endDelta){
        while(position>=limit){
            Node parent;
            parent.left=root;
            parent.starts=nodes[root].starts;
            parent.ends=nodes[root].ends;
            nodes.push_back(parent);
            root=static_cast<int>(nodes.size())-1;
            limit*=2;
        }
        int node=root;
        I lower=0,upper=limit;
        for(;;){
            nodes[node].starts+=startDelta;
            nodes[node].ends+=endDelta;
            if(upper-lower==1)break;
            I middle=lower+(upper-lower)/2;
            bool goLeft=position<middle;
            int child=goLeft?nodes[node].left:nodes[node].right;
            if(!child){
                child=static_cast<int>(nodes.size());
                nodes.emplace_back();
                if(goLeft)nodes[node].left=child;
                else nodes[node].right=child;
            }
            if(goLeft)upper=middle;
            else lower=middle;
            node=child;
        }
    }

    // Inclusive prefix sums of witness lengths at their two endpoints.
    std::pair<I,I> prefix(I position) const {
        if(position<0)return {0,0};
        if(position>=limit-1)
            return {nodes[root].starts,nodes[root].ends};
        std::pair<I,I> result{0,0};
        int node=root;
        I lower=0,upper=limit;
        while(node){
            if(upper-lower==1){
                result.first+=nodes[node].starts;
                result.second+=nodes[node].ends;
                break;
            }
            I middle=lower+(upper-lower)/2;
            if(position<middle){
                node=nodes[node].left;
                upper=middle;
            }else{
                int left=nodes[node].left;
                if(left){
                    result.first+=nodes[left].starts;
                    result.second+=nodes[left].ends;
                }
                node=nodes[node].right;
                lower=middle;
            }
        }
        return result;
    }
};

int main(){
    std::ios::sync_with_stdio(false);std::cin.tie(nullptr);
    std::map<I,I> gaps;
    std::set<std::pair<I,I>> sizes;
    std::set<std::pair<I,I>> reclaimedByStart,reclaimedByEnd;
    ReclaimIndex reclaimIndex;
    std::vector<std::pair<I,I>> pipes(1);
    I trench=0,command;
    constexpr int K=40;
    constexpr int PairStates=(K+1)*(K+2)/2;
    std::array<std::set<I>,K+1> small;
    std::array<I,K+1> frequency{},outgoing{};
    std::array<std::array<I,K+1>,K+1> transitions{};
    std::array<std::array<double,K+1>,PairStates> pairValue{};
    I insertions=0,nextRebuild=1;
    int previousLength=0;
    auto pairIndex=[](int a,int b){
        if(a>b)std::swap(a,b);
        return b*(b+1)/2+a;
    };
    auto rebuild=[&](){
        std::array<double,K+1> marginal{};
        std::array<std::array<double,K+1>,K+1> probability{};
        for(int length=1;length<=K;++length)
            marginal[length]=(frequency[length]+0.5)/(insertions+0.5*K);
        for(int last=1;last<=K;++last)
            for(int length=1;length<=K;++length)
                probability[last][length]=
                    (transitions[last][length]+K*marginal[length])/
                    (outgoing[last]+static_cast<double>(K));

        // Expected accepted volume until the first request fitting neither hole.
        // Both legal placements are evaluated after observing the request size.
        for(int b=1;b<=K;++b){
            for(int a=0;a<=b;++a){
                std::array<double,K+1> offer{};
                for(int length=1;length<=b;++length){
                    double continuation=pairValue[pairIndex(a,b-length)][length];
                    if(length<=a)
                        continuation=std::max(continuation,
                            pairValue[pairIndex(a-length,b)][length]);
                    offer[length]=length+continuation;
                }
                int state=pairIndex(a,b);
                for(int last=1;last<=K;++last){
                    double value=0;
                    for(int length=1;length<=b;++length)
                        value+=probability[last][length]*offer[length];
                    pairValue[state][last]=value;
                }
            }
        }
    };
    auto observeInsertion=[&](int length){
        ++insertions;++frequency[length];
        if(previousLength){
            ++transitions[previousLength][length];
            ++outgoing[previousLength];
        }
        previousLength=length;
        if(insertions==nextRebuild){
            rebuild();
            // Refresh cadence controls computation only.
            nextRebuild+=std::min<I>(nextRebuild,1024);
        }
    };
    auto erase=[&](std::map<I,I>::iterator p){
        I width=p->second-p->first;
        if(width<=K)small[static_cast<int>(width)].erase(p->first);
        sizes.erase({width,p->first});gaps.erase(p);
    };
    auto add=[&](I start,I end){
        if(start>=end)return;
        auto it=gaps.lower_bound(start);
        if(it!=gaps.begin()){
            auto prev=std::prev(it);
            if(prev->second==start){start=prev->first;erase(prev);}
        }
        it=gaps.lower_bound(start);
        if(it!=gaps.end()&&it->first==end){end=it->second;erase(it);}
        gaps[start]=end;sizes.insert({end-start,start});
        if(end-start<=K)small[static_cast<int>(end-start)].insert(start);
    };
    // A witness records an interval observed wholly free after deletion.
    // Nested witnesses survive independently until an allocation overlaps them.
    auto rememberSpan=[&](I start,I end){
        if(!reclaimedByStart.insert({start,end}).second)return;
        reclaimedByEnd.insert({end,start});
        I width=end-start;
        reclaimIndex.update(start,width,0);
        reclaimIndex.update(end,0,width);
    };
    auto forgetSpan=[&](I start,I end){
        reclaimedByStart.erase({start,end});
        reclaimedByEnd.erase({end,start});
        I width=end-start;
        reclaimIndex.update(start,-width,0);
        reclaimIndex.update(end,0,-width);
    };
    while(std::cin>>command&&command){
        if(command<0){
            previousLength=0;
            auto p=pipes.at(static_cast<std::size_t>(-command));
            std::cout<<p.first<<'\n'<<std::flush;
            add(p.first,p.first+p.second);
            auto reclaimed=gaps.upper_bound(p.first);
            --reclaimed;
            rememberSpan(reclaimed->first,reclaimed->second);
            continue;
        }
        I length=command,digs=0,start=0;
        observeInsertion(static_cast<int>(length));
        auto best=sizes.lower_bound({length,-1});
        if(best==sizes.end()){
            I tail=trench;
            if(!gaps.empty()&&std::prev(gaps.end())->second==trench)tail=std::prev(gaps.end())->first;
            digs=(length-(trench-tail)+19)/20;
            I old=trench;trench+=digs*20;add(old,trench);best=sizes.lower_bound({length,-1});
        }
        if(best->first>length&&best->first<K){
            int base=static_cast<int>(best->first);
            int current=static_cast<int>(length);
            int selected=base;
            double bestGain=0;
            for(int width=base+1;width<=K;++width){
                if(small[width].empty())continue;
                double parentValue=pairValue[pairIndex(base-current,width)][current];
                double alternativeValue=pairValue[pairIndex(base,width-current)][current];
                double gain=alternativeValue-parentValue;
                if(gain>bestGain+1e-10){
                    bestGain=gain;selected=width;
                }
            }
            if(selected!=base)
                best=sizes.find({selected,*small[selected].begin()});
        }
        auto gap=gaps.find(best->second);
        I begin=gap->first,end=gap->second;
        start=begin;
        if(end-begin>length){
            // Every surviving witness lies wholly inside one current gap.
            // A prefix intersects exactly the witnesses starting before its cut;
            // a suffix intersects exactly those ending after its cut.
            I leftLoss=reclaimIndex.prefix(begin+length-1).first
                      -reclaimIndex.prefix(begin-1).first;
            I rightLoss=reclaimIndex.prefix(end).second
                       -reclaimIndex.prefix(end-length).second;
            if(rightLoss<leftLoss)start=end-length;
        }
        if(start==begin){
            auto it=reclaimedByStart.lower_bound({begin,-1});
            while(it!=reclaimedByStart.end()&&it->first<start+length){
                auto witness=*it;
                ++it;
                forgetSpan(witness.first,witness.second);
            }
        }else{
            auto it=reclaimedByEnd.lower_bound({start+1,-1});
            while(it!=reclaimedByEnd.end()&&it->first<=end){
                auto witness=*it;
                ++it;
                forgetSpan(witness.second,witness.first);
            }
        }
        erase(gap);
        add(begin,start);
        add(start+length,end);
        pipes.push_back({start,length});std::cout<<digs<<' '<<start<<'\n'<<std::flush;
    }
}
