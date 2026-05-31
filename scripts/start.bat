@echo off
cd /d "%~dp0.."
set HF_HOME=%cd%\.cache\huggingface
set HF_ENDPOINT=https://hf-mirror.com
set PYTHONIOENCODING=utf-8

if exist "%cd%\python\pythonw.exe" (
    start "" /B "%cd%\python\pythonw.exe" native\main.py %*
) else if exist "%cd%\python\python.exe" (
    start "" /B "%cd%\python\python.exe" native\main.py %*
) else (
    where pythonw >nul 2>&1 && start "" /B pythonw native\main.py %*
)
