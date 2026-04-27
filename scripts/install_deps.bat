@echo off
title GuguGaga - Install Dependencies
pushd "%~dp0.."
if exist "python\python.exe" (
    "python\python.exe" scripts\setup.py --deps %*
) else (
    py -3.11 scripts\setup.py --deps %* 2>nul || python scripts\setup.py --deps %*
)
pause
popd
