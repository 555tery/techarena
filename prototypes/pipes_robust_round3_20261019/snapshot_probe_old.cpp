// Independent handoff regression: internal reservations must remain reusable
// when their owning policy is abandoned. No real pipe occupies [30,70).
#define main embedded_solver_main
#include "candidate/solution.cpp"
#undef main
int main(){
 fallback_online::Allocator source;
 source.trenchLength=100;
 source.pipes.push_back(fallback_online::Pipe{20,10,true,0});
 source.pipes.push_back(fallback_online::Pipe{70,10,true,1});
 source.activePipeCount=2;
 // The policy omitted the reserved but still unoccupied [50,70) interval.
 source.addFreeGap(0,20,-1);source.addFreeGap(30,50,-1);source.addFreeGap(80,100,-1);
 Allocator destination;adoptOnline(destination,source);
 if(destination.bf(40)!=30)return 1;
 for(int x=0;x<100;++x)for(int length=1;length<=40;++length){
  bool occupied=(x<30&&x+length>20)||(x<80&&x+length>70);
  bool expected=x+length<=100&&!occupied;
  // fits() permits extending a terminal gap beyond T; restrict to in-trench.
  if(x+length<=100&&destination.fits(x,length)!=expected)return 2;
 }
 return 0;
}
