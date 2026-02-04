# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Api.exe
Uses absolute paths based on SPECPATH for reliable builds.
"""
from PyInstaller.utils.hooks import collect_all, collect_submodules
import os

# SPECPATH is set by PyInstaller to the directory containing this spec file
# Project root is parent of installer/ (where this spec file is)
# Note: SPECPATH is available as a global variable when running via PyInstaller
try:
    spec_dir = SPECPATH
except NameError:
    spec_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(spec_dir)
block_cipher = None

# Collect all submodules from local packages
hiddenimports = []
hiddenimports += collect_submodules('app')
hiddenimports += collect_submodules('storage')
hiddenimports += collect_submodules('billing')
hiddenimports += collect_submodules('watcher')

# Add external dependencies
hiddenimports += [
    'uvicorn', 'uvicorn.logging', 'uvicorn.loops', 'uvicorn.loops.auto',
    'uvicorn.protocols', 'uvicorn.protocols.http', 'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets', 'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan', 'uvicorn.lifespan.on',
    'fastapi', 'starlette', 'pydantic', 'openai', 'httpx',
    'pdf2image', 'openpyxl', 'gspread', 'PIL',
]

# Collect data files for external packages
datas = []
binaries = []

# Collect uvicorn, fastapi, starlette completely
for pkg in ['uvicorn', 'fastapi', 'starlette']:
    try:
        pkg_datas, pkg_binaries, pkg_hiddenimports = collect_all(pkg)
        datas += pkg_datas
        binaries += pkg_binaries
        hiddenimports += pkg_hiddenimports
    except:
        pass

a = Analysis(
    [os.path.join(project_root, 'run.py')],  # Absolute path to run.py
    pathex=[project_root],   # Add project root to path
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Api',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
)
