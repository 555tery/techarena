#define PIPES_WINAPI_TEST
#define main solverMain
#include "solution.cpp"
#undef main

static int scenario,calls;
static unsigned totalWritten;
static LONG fakeRead(HANDLE,HANDLE,void*,void*,NativeIOStatus*r,void*,ULONG capacity,void*,void*){
 ++calls;r->information=2;r->status=0;
 if(scenario==1)return 0;
 if(scenario==2)return static_cast<LONG>(0x80000005u); // partial message
 if(scenario==3){r->information=0;return static_cast<LONG>(0xc0000011u);}
 if(scenario==4)return 0x103; // pending, then completed with two bytes
 if(scenario==5){r->information=capacity+1;return 0;}
 if(scenario==6){r->status=static_cast<LONG>(0xc0000022u);return 0x103;}
 return static_cast<LONG>(0xc0000022u);
}
static LONG fakeWrite(HANDLE,HANDLE,void*,void*,NativeIOStatus*r,void*,ULONG length,void*,void*){
 ++calls;r->status=0;r->information=length>2?2:length;totalWritten+=r->information;
 return scenario==8?0x103:0;
}
int main(int argc,char**argv){
 if(argc!=2)return 10;scenario=atoi(argv[1]);nativeRead=fakeRead;nativeWrite=fakeWrite;inputHandle=0;outputHandle=1;
 if(scenario<7){char data[8];unsigned n=readNativePipe(data,sizeof(data));return calls!=1||n!=(scenario==3?0:2);}
 writeNativePipe("1234567",7);return totalWritten!=7||calls!=4;
}
