@echo off
cl /nologo /O2 /std:c++17 /EHsc solution.cpp /Fe:solution.exe
if errorlevel 1 exit /b 1
