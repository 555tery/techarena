#define PIPES_WINAPI_TEST
#define main candidateMain
#include "solution.cpp"
#undef main
void (*shimWaitHook)()=nullptr;
static LONG waitStatus; static LONG fakeWait(HANDLE,unsigned char a,void*t){if(a||t)return 99;return waitStatus;}
int main(int n,char**v){waitStatus=n>1?strtol(v[1],nullptr,0):0;NativeIOStatus r;r.status=0;r.information=1;nativeWait=fakeWait;return completeNativeIO(1,0x103,r);}
