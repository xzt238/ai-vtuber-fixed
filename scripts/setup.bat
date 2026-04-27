@echo off
title GuguGaga Setup
pushd "%~dp0.."
if exist "python\python.exe" (
    "python\python.exe" scripts\setup.py %*
) else (
    py -3.11 scripts\setup.py %* 2>nul || python scripts\setup.py %*
)
pause
popd
