#define PIPES_WINAPI_TEST
#define main solverMain
#include "solution.cpp"
#undef main

static int scenario,calls;
static unsigned totalWritten,outputLength;
static char outputBytes[32];
static NativeIOStatus* pendingIO;
static void* pendingData;
static unsigned pendingCount;
static LONG pendingStatus;
static bool pendingHasWriteData;
void (*shimWaitHook)()=nullptr;
static void completePending(){
 if(!pendingIO)return;
 pendingIO->information=pendingCount;
 pendingIO->status=pendingStatus;
 if(pendingHasWriteData&&pendingStatus==0&&pendingCount){memcpy(outputBytes+outputLength,pendingData,pendingCount);outputLength+=pendingCount;totalWritten+=pendingCount;}
 pendingIO=nullptr;
}
static LONG fakeRead(HANDLE,HANDLE,void*,void*,NativeIOStatus*r,void*,ULONG,void*,void*){
 ++calls;
 if(scenario==1){r->information=2;r->status=0;return 0;}
 if(scenario==2){r->information=2;r->status=static_cast<LONG>(0x80000005u);return static_cast<LONG>(0x80000005u);}
 if(scenario==3){r->status=static_cast<LONG>(0xc0000011u);return r->status;}
 if(scenario==4||scenario==6){pendingIO=r;pendingCount=scenario==4?2:0;pendingStatus=scenario==4?0:static_cast<LONG>(0xc0000022u);pendingHasWriteData=false;return 0x103;}
 return static_cast<LONG>(0xc0000022u); // generic error: IOSB.Information deliberately untouched
}
static LONG fakeWrite(HANDLE,HANDLE,void*,void*,NativeIOStatus*r,void*data,ULONG length,void*,void*){
 ++calls;
 if(scenario==14)return static_cast<LONG>(0xc0000022u); // no IOSB writes on hard error
 const unsigned n=scenario==10?length:(scenario==13?0:(length>2?2:length));
 if(scenario==12){pendingIO=r;pendingData=data;pendingCount=n;pendingStatus=0;pendingHasWriteData=true;return 0x103;}
 r->status=0;r->information=n;
 if(n){memcpy(outputBytes+outputLength,data,n);outputLength+=n;totalWritten+=n;}
 return 0;
}
int main(int argc,char**argv){
 if(argc!=2)return 10;
 scenario=atoi(argv[1]);nativeWait=shimNativeWait;nativeRead=fakeRead;nativeWrite=fakeWrite;inputHandle=0;outputHandle=1;shimWaitHook=completePending;
 if(scenario<10){char data[8];const unsigned n=readNativePipe(data,sizeof(data));
  if(scenario==3)return calls==1&&n==0?0:20;
  if(scenario==5||scenario==6)return 21; // these should have failed before returning
  return calls==1&&n==2?0:22;
 }
 writeNativePipe("1234567",7);
 const unsigned expectedCalls=scenario==10?1:4;
 return calls!=static_cast<int>(expectedCalls)||totalWritten!=7||outputLength!=7||memcmp(outputBytes,"1234567",7)!=0;
}
