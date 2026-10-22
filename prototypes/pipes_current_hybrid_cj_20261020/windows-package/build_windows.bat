@echo off
setlocal
cd /d "%~dp0"
rem Uses existing local compilers only.
where cjc >nul 2>nul
if errorlevel 1 (
  echo ERROR: initialize your existing Cangjie SDK environment first.
  exit /b 1
)
cjc --version
cjc -O2 online.cj -o online-cj.exe
if errorlevel 1 exit /b 1
cjc -O2 hybrid.cj -o hybrid-cj.exe
if errorlevel 1 exit /b 1
where clang++ >nul 2>nul
if not errorlevel 1 goto clang
where g++ >nul 2>nul
if not errorlevel 1 goto gcc
where cl >nul 2>nul
if not errorlevel 1 goto msvc
echo ERROR: existing clang++, g++ or cl is required for reference parity.
exit /b 1
:clang
clang++ -std=c++17 -O2 -DNDEBUG hybrid.cpp -o hybrid-cpp.exe
if errorlevel 1 exit /b 1
goto done
:gcc
g++ -std=c++17 -O2 -DNDEBUG hybrid.cpp -o hybrid-cpp.exe
if errorlevel 1 exit /b 1
goto done
:msvc
cl /nologo /std:c++17 /O2 /DNDEBUG /EHsc hybrid.cpp /Fe:hybrid-cpp.exe
if errorlevel 1 exit /b 1
:done
echo Built three frozen variants. To benchmark all inputs on one logical CPU:
echo py -3 windows_compare.py --out windows-results.json
exit /b 0
