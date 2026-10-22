#include <algorithm>
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
        if(command<0){auto p=pipes.at(static_cast<std::size_t>(-command));std::cout<<p.first<<'\n'<<std::flush;add(p.first,p.first+p.second);continue;}
        I length=command,digs=0,start=0;
        auto best=sizes.lower_bound({length,-1});
        if(best==sizes.end()){
            I tail=trench;
            if(!gaps.empty()&&std::prev(gaps.end())->second==trench)tail=std::prev(gaps.end())->first;
            digs=(length-(trench-tail)+19)/20;
            I old=trench;trench+=digs*20;add(old,trench);best=sizes.lower_bound({length,-1});
        }
        auto gap=gaps.find(best->second);start=gap->first;I end=gap->second;erase(gap);add(start+length,end);
        pipes.push_back({start,length});std::cout<<digs<<' '<<start<<'\n'<<std::flush;
    }
}
