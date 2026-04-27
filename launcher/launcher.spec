# -*- mode: python ; coding: utf-8 -*-
"""
GuguGaga AI-VTuber 启动器 PyInstaller 配置
=============================================

只打包 launcher.py（启动器），不打包主应用。
主应用使用嵌入式 Python (python/python.exe) 运行。

打包产物: GuguGaga.exe (~30MB)
依赖运行时: python/ 目录（嵌入式 Python + 所有依赖）

使用方法:
    pyinstaller launcher.spec
    或
    build_launcher.bat
"""

import sys
from pathlib import Path

# 项目路径
LAUNCHER_DIR = Path(SPECPATH)
PROJECT_ROOT = LAUNCHER_DIR.parent

a = Analysis(
    [str(LAUNCHER_DIR / 'launcher.py')],
    pathex=[str(LAUNCHER_DIR), str(PROJECT_ROOT / 'app')],
    binaries=[],
    datas=[
        # splash.html 打包到 EXE 内（作为 fallback）
        (str(LAUNCHER_DIR / 'splash.html'), '.'),
    ],
    hiddenimports=[
        # pywebview 后端
        'webview',
        'webview.platforms.winforms',
        # pystray 系统托盘
        'pystray',
        'pystray._win32',
        # Pillow（pystray 依赖）
        'PIL',
        'PIL.Image',
        'PIL.ImageDraw',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 排除不需要的大型模块（减小体积）
        'tkinter',
        'matplotlib',
        'numpy',
        'torch',
        'tensorflow',
        'cv2',
        'scipy',
        'pandas',
        'IPython',
        'notebook',
        'jupyter',
        'sphinx',
        'pytest',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='GuguGaga',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # 不显示控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,              # TODO: 添加图标 icon='assets/icon.ico'
)
