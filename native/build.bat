@echo off
REM ======================================
REM  GuguGaga Native - Build Script
REM  Must run with Python 3.11
REM ======================================

echo ========================================
echo  Building GuguGagaNative v1.9.82
echo ========================================

REM Check Python 3.11
py -3.11 --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python 3.11 not found!
    echo Please install Python 3.11 from python.org
    pause
    exit /b 1
)

REM Check PyInstaller
py -3.11 -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    py -3.11 -m pip install pyinstaller
)

REM Check key dependencies
echo Checking dependencies...
py -3.11 -c "import PySide6; print('  PySide6:', PySide6.__version__)"
if errorlevel 1 (
    echo ERROR: PySide6 not installed for Python 3.11
    pause
    exit /b 1
)
py -3.11 -c "import live2d.v3; print('  live2d-py: OK')"
if errorlevel 1 (
    echo ERROR: live2d-py not installed for Python 3.11
    pause
    exit /b 1
)
py -3.11 -c "import qfluentwidgets; print('  qfluentwidgets: OK')"
if errorlevel 1 (
    echo ERROR: qfluentwidgets not installed for Python 3.11
    pause
    exit /b 1
)

echo.
echo Starting build...
echo.

REM Build with spec file
py -3.11 -m PyInstaller gugu.spec --clean --noconfirm

if errorlevel 1 (
    echo.
    echo ========================================
    echo  BUILD FAILED
    echo ========================================
    pause
    exit /b 1
)

echo.
echo ========================================
echo  BUILD SUCCESS
echo  Output: dist\GuguGagaNative\
echo ========================================

REM Show output size
for /f %%A in ('dir /s /a "dist\GuguGagaNative" ^| find "File(s)"') do set SIZE=%%A
echo Total size: %SIZE% bytes

pause
