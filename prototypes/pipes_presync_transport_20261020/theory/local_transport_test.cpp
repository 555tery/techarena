#include "local_transport.hpp"
#include <cassert>
#include <map>
#include <iostream>

struct MinimalAllocator {
    int T = 0;
    std::map<int,int> g;
    std::vector<std::pair<int,int>> pipes{{0,0}};
    bool fits(int x, int n) const {
        if (x < 0 || x + n > 100000000) return false;
        for (std::size_t i=1; i<pipes.size(); ++i) {
            const auto p=pipes[i];
            if (p.second && x<p.first+p.second && p.first<x+n) return false;
        }
        return true;
    }
};

int main() {
    using P=std::pair<int,int>;
    using V=std::vector<P>;
    MinimalAllocator a;
    a.T=20; a.pipes={{0,0},{0,3}};
    auto r=local_transport::choose(a,a.pipes,3,20,2);
    assert(r.certificate && r.x==3 && r.differing==0);

    // Exterior pipe at 80 is identity; global reflection would reject it.
    a.T=100; a.pipes={{0,0},{0,3},{3,2},{80,10}};
    V p={{0,0},{0,3},{30,2},{80,10}};
    r=local_transport::choose(a,p,5,100,10);
    assert(r.certificate && r.x==20 && r.centerSum==35);
    assert(r.hullLeft==3 && r.hullRight==32 && r.differing==2);
    r=local_transport::choose(a,p,40,100,10);
    assert(r.certificate && r.x==40 && r.differing==1);

    // A boundary may expand through empty space, retaining the same center.
    a.T=20; a.pipes={{0,0},{3,2}}; p={{0,0},{30,2}};
    r=local_transport::choose(a,p,1,40,5);
    assert(r.certificate && r.x==29 && r.hullLeft==1 && r.hullRight==34);

    // A fixed centered pipe is invariant under the local reflection.
    a.T=40; a.pipes={{0,0},{3,2},{16,3}}; p={{0,0},{30,2},{16,3}};
    r=local_transport::choose(a,p,10,40,3);
    assert(r.certificate && r.x==22);

    // An off-center fixed pipe inside the hull invalidates the certificate.
    a.pipes[2]={10,2}; p[2]={10,2};
    assert(!local_transport::choose(a,p,35,40,2).certificate);

    // Different displaced pipes require the same reflection center.
    a.pipes={{0,0},{3,2},{5,2}}; p={{0,0},{30,2},{27,2}};
    assert(!local_transport::choose(a,p,35,40,2).certificate);

    // Historical dead PIDs require an explicit complete live-PID list.
    a.pipes.assign(10000,{0,0}); p=a.pipes;
    a.pipes[9999]={3,2}; p[9999]={30,2};
    assert(!local_transport::choose(a,p,5,40,10).certificate);
    std::vector<int> ids{9999};
    r=local_transport::choose(a,p,5,40,10,&ids);
    assert(r.certificate && r.x==20);
    ids.push_back(9999);
    assert(!local_transport::choose(a,p,5,40,10,&ids).certificate);

    // A valid current reflection is not a guarantee for every future suffix:
    // after deleting a boundary blocker, a parent pipe may cross that boundary.
    a.T=40; a.pipes={{0,0},{0,0},{3,2},{32,8}};
    p={{0,0},{0,0},{30,2},{32,8}};
    assert(!local_transport::choose(a,p,0,40,30).certificate);
    std::cout << "local_transport: 11 invariant cases passed\n";
}
