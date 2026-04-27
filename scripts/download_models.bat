@echo off
title GuguGaga - Download Models
pushd "%~dp0.."
if exist "python\python.exe" (
    "python\python.exe" scripts\setup.py --models %*
) else (
    py -3.11 scripts\setup.py --models %* 2>nul || python scripts\setup.py --models %*
)
pause
popd
