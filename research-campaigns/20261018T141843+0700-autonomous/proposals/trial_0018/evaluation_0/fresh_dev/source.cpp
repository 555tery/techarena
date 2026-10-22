#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <iterator>
#include <cstdint>
#include <iostream>
#include <map>
#include <set>
#include <utility>
#include <vector>
using I=std::int64_t;
int main(){
    std::ios::sync_with_stdio(false);std::cin.tie(nullptr);
    std::map<I,I> gaps;
    std::set<std::pair<I,I>> sizes;
    std::vector<std::pair<I,I>> pipes(1);
    I trench=0,command;
    I step=0;
    std::map<I,std::size_t> live;
    std::vector<I> born(1);
    std::vector<unsigned char> alive(1);
    struct Evidence {
        std::uint64_t count=0;
        double sum=0.0,square=0.0;
    };
    std::array<Evidence,64*3*6> evidence{};
    struct Probe {
        I lo,hi,placed;
        std::size_t pid;
        unsigned cell;
        bool olderLeft;
    };
    std::array<std::vector<Probe>,40> pending;
    auto logBucket=[](I x){
        unsigned b=0;
        while(x>1){x>>=1;++b;}
        return b;
    };
    auto cellFor=[&](std::size_t left,std::size_t right,I residual,bool& olderLeft){
        olderLeft=born[left]<born[right];
        std::size_t older=olderLeft?left:right;
        std::size_t younger=olderLeft?right:left;
        unsigned contrast=logBucket(step-born[older])-logBucket(step-born[younger]);
        unsigned relation=1;
        if(pipes[older].second<pipes[younger].second)relation=0;
        else if(pipes[older].second>pipes[younger].second)relation=2;
        return (contrast*3+relation)*6+logBucket(residual);
    };
    auto covered=[&](I lo,I hi){
        auto it=gaps.upper_bound(lo);
        if(it==gaps.begin())return false;
        --it;
        return it->second>=hi;
    };
    // Resolve each probe at the first later insertion exceeding its remainder.
    auto observe=[&](I length){
        for(int r=1;r<40&&r<length;++r){
            for(const Probe& p:pending[r]){
                int delta=0;
                if(alive[p.pid]){
                    I pipeLength=pipes[p.pid].second;
                    I freeLo=p.placed==p.lo?p.placed+pipeLength:p.lo;
                    I freeHi=p.placed==p.lo?p.hi:p.placed;
                    if(covered(freeLo,freeHi)){
                        I leftFree=0,rightFree=0;
                        auto it=gaps.lower_bound(p.lo);
                        if(it!=gaps.begin()){
                            --it;
                            if(it->second>=p.lo)leftFree=p.lo-it->first;
                        }
                        it=gaps.upper_bound(p.hi);
                        if(it!=gaps.begin()){
                            --it;
                            if(it->second>p.hi)rightFree=it->second-p.hi;
                        }
                        int leftUseful=r+leftFree>=length?1:0;
                        int rightUseful=r+rightFree>=length?1:0;
                        delta=p.olderLeft?leftUseful-rightUseful:rightUseful-leftUseful;
                    }
                }
                Evidence& e=evidence[p.cell];
                ++e.count;
                e.sum+=delta;
                e.square+=delta*delta;
            }
            pending[r].clear();
        }
    };
    auto favorHigh=[&](unsigned cell,bool olderLeft){
        const Evidence& e=evidence[cell];
        if(e.count<2)return false;
        double n=static_cast<double>(e.count);
        double mean=e.sum/n;
        double variance=std::max(0.0,(e.square-e.sum*mean)/(n-1.0));
        // Empirical uncertainty guard; adaptive observations need not be IID.
        double guardLog=std::log(40.0);
        double margin=std::sqrt(2.0*variance*guardLog/n)
                     +14.0*guardLog/(3.0*(n-1.0));
        return (olderLeft?mean:-mean)>margin;
    };
    auto erase=[&](std::map<I,I>::iterator p){sizes.erase({p->second-p->first,p->first});gaps.erase(p);};
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
    };
    while(std::cin>>command&&command){
        ++step;
        if(command<0){
            std::size_t pid=static_cast<std::size_t>(-command);
            auto p=pipes.at(pid);
            std::cout<<p.first<<'\n'<<std::flush;
            live.erase(p.first);
            alive[pid]=0;
            add(p.first,p.first+p.second);
            continue;
        }
        I length=command,digs=0,start=0;
        observe(length);
        auto best=sizes.lower_bound({length,-1});
        if(best==sizes.end()){
            I tail=trench;
            if(!gaps.empty()&&std::prev(gaps.end())->second==trench)tail=std::prev(gaps.end())->first;
            digs=(length-(trench-tail)+19)/20;
            I old=trench;trench+=digs*20;add(old,trench);best=sizes.lower_bound({length,-1});
        }
        auto gap=gaps.find(best->second);
        I lo=gap->first,end=gap->second,residual=end-lo-length;
        bool high=false,track=false,olderLeft=false;
        unsigned cell=0;
        if(residual>0&&residual<40){
            auto right=live.lower_bound(lo);
            if(right!=live.end()&&right->first==end&&right!=live.begin()){
                auto left=std::prev(right);
                if(left->first+pipes[left->second].second==lo){
                    cell=cellFor(left->second,right->second,residual,olderLeft);
                    high=favorHigh(cell,olderLeft);
                    track=true;
                }
            }
        }
        start=high?end-length:lo;
        erase(gap);
        if(high)add(lo,start);
        else add(start+length,end);
        pipes.push_back({start,length});
        std::size_t pid=pipes.size()-1;
        born.push_back(step);
        alive.push_back(1);
        live.emplace(start,pid);
        if(track)pending[static_cast<std::size_t>(residual)].push_back({lo,end,start,pid,cell,olderLeft});
        std::cout<<digs<<' '<<start<<'\n'<<std::flush;
    }
}
