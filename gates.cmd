@echo off
REM ============================================================
REM  Quality gate entry point (Windows)
REM  NOTE: this file is intentionally ASCII-only.
REM        cmd.exe reads .cmd in the OEM code page, so non-ASCII
REM        comments break execution. All human-readable output
REM        comes from Python, which handles UTF-8 itself.
REM ============================================================
REM  Usage:
REM    gates.cmd                 run Gate 0
REM    gates.cmd all             run all gates
REM    gates.cmd list            list checks
REM    gates.cmd snapshot        take a snapshot (tag + manifest)
REM    gates.cmd commit -m "..." commit WITH gate enforcement
REM ============================================================
setlocal
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"

if "%~1"==""          goto :gate0
if /i "%~1"=="0"      goto :gate0
if /i "%~1"=="all"    goto :gateall
if /i "%~1"=="list"   goto :list
if /i "%~1"=="snapshot" goto :snapshot
if /i "%~1"=="commit" goto :commit
goto :gate0

:gate0
python tools\gates.py --gate 0
goto :done

:gateall
python tools\gates.py --gate all
goto :done

:list
python tools\gates.py --list
goto :done

:snapshot
python tools\snapshot.py
goto :done

:commit
shift
python tools\gate_commit.py %1 %2 %3 %4 %5 %6 %7 %8 %9
goto :done

:done
exit /b %ERRORLEVEL%