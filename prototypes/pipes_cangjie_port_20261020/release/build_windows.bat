@echo off
setlocal
cd /d "%~dp0"
rem Uses only already available local tools. No installation or global changes.
rem Run from a Cangjie-enabled shell; for cl use a Visual Studio developer shell.
where cjc >nul 2>nul
if errorlevel 1 (
  echo ERROR: cjc is not available in this shell. Initialize your local SDK first.
  exit /b 1
)
if not exist solution.cj (
  echo ERROR: solution.cj is missing.
  exit /b 1
)
if not exist solution.cpp (
  echo ERROR: the frozen reference solution.cpp is missing.
  exit /b 1
)
cjc --version
cjc -O2 solution.cj -o solution-cj.exe
if errorlevel 1 exit /b 1
where clang++ >nul 2>nul
if not errorlevel 1 goto clang
where g++ >nul 2>nul
if not errorlevel 1 goto gcc
where cl >nul 2>nul
if not errorlevel 1 goto msvc
echo ERROR: no local clang++, g++, or cl compiler is available.
exit /b 1
:clang
clang++ --version
clang++ -std=c++17 -O2 -DNDEBUG solution.cpp -o solution-cpp.exe
if errorlevel 1 exit /b 1
goto done
:gcc
g++ --version
g++ -std=c++17 -O2 -DNDEBUG solution.cpp -o solution-cpp.exe
if errorlevel 1 exit /b 1
goto done
:msvc
cl /nologo /std:c++17 /O2 /DNDEBUG /EHsc solution.cpp /Fe:solution-cpp.exe
if errorlevel 1 exit /b 1
:done
echo Built solution-cj.exe and solution-cpp.exe. No benchmark has been run.
echo Run: py -3 windows_bench.py --cpp solution-cpp.exe --cj solution-cj.exe --tests tests --out windows-results.json
exit /b 0
