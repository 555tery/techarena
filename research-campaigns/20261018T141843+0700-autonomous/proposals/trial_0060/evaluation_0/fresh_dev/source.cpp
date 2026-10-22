#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <iostream>
#include <iterator>
#include <map>
#include <set>
#include <utility>
#include <vector>
using I=std::int64_t;
struct FitShadow{
    bool firstFit;
    I trench=0;
    std::map<I,I> gaps;
    std::set<std::pair<I,I>> sizes;
    std::array<std::set<I>,41> fronts;
    std::vector<std::pair<I,I>> pipes;

    explicit FitShadow(bool first):firstFit(first),pipes(1){}

    static int bucket(I length){
        return static_cast<int>(std::min<I>(length,40));
    }

    void erase(std::map<I,I>::iterator p){
        I length=p->second-p->first;
        if(firstFit)fronts[bucket(length)].erase(p->first);
        else sizes.erase({length,p->first});
        gaps.erase(p);
    }

    void add(I start,I end){
        if(start>=end)return;
        auto it=gaps.lower_bound(start);
        if(it!=gaps.begin()){
            auto prev=std::prev(it);
            if(prev->second==start){start=prev->first;erase(prev);}
        }
        it=gaps.lower_bound(start);
        if(it!=gaps.end()&&it->first==end){end=it->second;erase(it);}
        gaps[start]=end;
        if(firstFit)fronts[bucket(end-start)].insert(start);
        else sizes.insert({end-start,start});
    }

    std::map<I,I>::iterator choose(I length){
        if(!firstFit){
            auto it=sizes.lower_bound({length,-1});
            return it==sizes.end()?gaps.end():gaps.find(it->second);
        }
        I address=-1;
        for(int k=static_cast<int>(length);k<=40;++k){
            if(!fronts[k].empty()){
                I candidate=*fronts[k].begin();
                if(address<0||candidate<address)address=candidate;
            }
        }
        return address<0?gaps.end():gaps.find(address);
    }

    void allocate(I length){
        auto gap=choose(length);
        if(gap==gaps.end()){
            I tail=trench;
            if(!gaps.empty()&&std::prev(gaps.end())->second==trench)
                tail=std::prev(gaps.end())->first;
            I digs=(length-(trench-tail)+19)/20;
            I old=trench;
            trench+=digs*20;
            add(old,trench);
            gap=choose(length);
        }
        I start=gap->first,end=gap->second;
        erase(gap);
        add(start+length,end);
        pipes.push_back({start,length});
    }

    void release(std::size_t pid){
        auto p=pipes[pid];
        add(p.first,p.first+p.second);
    }
};
int main(){
    std::ios::sync_with_stdio(false);std::cin.tie(nullptr);
    std::map<I,I> gaps;
    std::set<std::pair<I,I>> sizes;
    std::vector<std::pair<I,I>> pipes(1);
    std::array<std::set<I>,41> fronts;
    FitShadow shadowBest(false),shadowFirst(true);
    I trench=0,command;
    auto erase=[&](std::map<I,I>::iterator p){
        I length=p->second-p->first;
        sizes.erase({length,p->first});
        fronts[FitShadow::bucket(length)].erase(p->first);
        gaps.erase(p);
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
        fronts[FitShadow::bucket(end-start)].insert(start);
    };
    auto choose=[&](I length,bool firstFit){
        auto best=sizes.lower_bound({length,-1});
        if(!firstFit||best==sizes.end())return best;
        I address=-1;
        for(int k=static_cast<int>(length);k<=40;++k){
            if(!fronts[k].empty()){
                I candidate=*fronts[k].begin();
                if(address<0||candidate<address)address=candidate;
            }
        }
        if(address<0)return best;
        auto gap=gaps.find(address);
        return sizes.find({gap->second-gap->first,address});
    };
    while(std::cin>>command&&command){
        if(command<0){
            auto pid=static_cast<std::size_t>(-command);
            auto p=pipes.at(pid);
            std::cout<<p.first<<'\n'<<std::flush;
            add(p.first,p.first+p.second);
            shadowBest.release(pid);
            shadowFirst.release(pid);
            continue;
        }
        I length=command,digs=0,start=0;
        shadowBest.allocate(length);
        shadowFirst.allocate(length);
        bool firstFit=shadowFirst.trench<shadowBest.trench;
        auto best=choose(length,firstFit);
        if(best==sizes.end()){
            I tail=trench;
            if(!gaps.empty()&&std::prev(gaps.end())->second==trench)tail=std::prev(gaps.end())->first;
            digs=(length-(trench-tail)+19)/20;
            I old=trench;trench+=digs*20;add(old,trench);best=choose(length,firstFit);
        }
        auto gap=gaps.find(best->second);start=gap->first;I end=gap->second;erase(gap);add(start+length,end);
        pipes.push_back({start,length});std::cout<<digs<<' '<<start<<'\n'<<std::flush;
    }
}
