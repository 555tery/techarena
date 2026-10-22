// Independent differential check against the physical map allocator. Includes
// old-root reuse, merging at the tail, and both continuation policies.
#define main participant_main
#include "candidate/solution.cpp"
#undef main
int main(){
    robust_search::Arena arena;
    Allocator real;real.emit=false;
    robust_search::Layout tree{&arena,0,0,0};
    vector<int> live;uint32_t random=123456789;
    auto next=[&](){random^=random<<13;random^=random>>17;random^=random<<5;return random;};
    for(int k=0;k<10000;++k){
        if(!live.empty()&&(live.size()>200||next()%100<48)){
            size_t idx=next()%live.size();int id=live[idx];auto [x,n]=real.pipes[id];
            auto old=tree;size_t mark=arena.a.size();tree.release(x,x+n);
            // A sibling from the old persistent root must remain independent.
            auto sibling=old;int sx=sibling.bf(7);sibling.place(7,sx);
            (void)mark;
            real.remove(id);live[idx]=live.back();live.pop_back();
        }else{
            int n=1+next()%40;int x=real.bf(n);assert(tree.bf(n)==x);
            // Exercise high-side placement as well as the BF continuation.
            if(next()%3==0){auto g=real.sizes.lower_bound({n,-1});if(g!=real.sizes.end())x=g->second+g->first-n;}
            tree.place(n,x);real.place(n,x);live.push_back(int(real.pipes.size())-1);
        }
        assert(tree.T==real.T);
        for(int n=1;n<=40;++n){
            assert(tree.bf(n)==real.bf(n));
            auto it=find_if(real.g.begin(),real.g.end(),[&](auto p){return p.second-p.first>=n;});
            int first=it==real.g.end()?real.bf(n):it->first;
            assert(tree.bf(n,1)==first);
        }
    }
    fprintf(stderr,"persistent tree: 10000 differential operations OK; nodes=%zu\n",arena.a.size());
}
