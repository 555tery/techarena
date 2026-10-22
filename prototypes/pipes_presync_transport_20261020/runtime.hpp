// Lazy physical state: the original algorithm remains the virtual reference.
// Physical maps exist only while a changed public placement is still relevant.
struct PhysicalFollower {
 unique_ptr<Allocator> actual;
 int T=0, differing=0;
 unsigned activated=0, certificates=0, excessIdentity=0, localAccepted=0, bfSteps=0, identitySteps=0;
 int policy=2;
 explicit PhysicalFollower(int p):policy(p){}
 static int nextT(int t,int x,int n){return max(t,20*((x+n+19)/20));}
 void start(const Allocator& reference){
  actual=make_unique<Allocator>();actual->emit=false;actual->T=T;actual->pipes=reference.pipes;
  for(auto [l,r]:reference.g)if(l<T)actual->add(l,min(r,T));
  for(size_t id=1;id<actual->pipes.size();++id){auto [x,n]=actual->pipes[id];if(n&&x+n>T)throw runtime_error("lazy physical extent");}
  ++activated;
 }
 void releaseIfIdentical(int parentT){
  if(actual&&!differing){
   if(T<=parentT)++certificates;else ++excessIdentity;
   actual.reset();
  }
 }
 void place(const Allocator& referenceBefore,int n,int refx,int parentT,bool replaying,int planned=-1){
  if(planned<0)planned=refx;
  if(replaying&&planned!=refx&&!actual)start(referenceBefore);
  int x=refx;
  if(actual){
   if(replaying)x=planned;
   else if(differing){
    const int bx=actual->bf(n);x=bx;bool accepted=false;
    if(policy>=2){
     auto q=local_transport::choose(*actual,referenceBefore.pipes,refx,parentT,n);
     if(q.certificate){x=q.x;accepted=true;++localAccepted;}
    }
    if(!accepted&&(policy==1||policy==3||policy==4)&&actual->fits(refx,n)&&nextT(T,refx,n)<=(policy==4?parentT:nextT(T,bx,n))){x=refx;accepted=true;++identitySteps;}
    if(!accepted)++bfSteps;
   }
   if(!actual->fits(x,n))throw runtime_error("physical placement collision");
   actual->place(n,x);differing+=x!=refx;
  }
  const int updated=nextT(T,x,n);printf("%d %d\n",(updated-T)/20,x);T=updated;
  if(actual&&actual->T!=T)throw runtime_error("physical trench mismatch");
  releaseIfIdentical(parentT);
 }
 void remove(int id,int refx,int parentT){
  int x=refx;
  if(actual){
   x=actual->pipes.at(id).first;
   if(x!=refx){if(!differing)throw runtime_error("physical PID count");--differing;}
   actual->remove(id);
  }
  printf("%d\n",x);releaseIfIdentical(parentT);
 }
 void report(int parentT)const{
  fprintf(stderr,"LAZY_TRANSPORT activated=%u certificates=%u excess_identity=%u local_accepted=%u bf_steps=%u identity_steps=%u differing=%d physical_T=%d parent_T=%d\n",activated,certificates,excessIdentity,localAccepted,bfSteps,identitySteps,differing,T,parentT);
 }
};
