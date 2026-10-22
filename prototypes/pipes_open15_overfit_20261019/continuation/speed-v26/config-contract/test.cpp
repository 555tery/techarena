#define PIPES_WINAPI_TEST
#define main candidateMain
#include "solution.cpp"
#undef main
int main(int argc,char**argv){configScenario=argc>1?atoi(argv[1]):0;outputHandle=1;configureOutputCompletion(GetModuleHandleW(L"ntdll.dll"));return configCalls==1?0:3;}
