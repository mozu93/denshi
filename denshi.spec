# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller設定ファイル - 電子帳簿保存システム
このファイルはbuild.pyから自動的に使用されます。
"""

import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# VERSION.pyからバージョン情報を取得
spec_root = os.path.abspath(SPECPATH)
sys.path.insert(0, spec_root)
from VERSION import __version__, __build_date__, APP_NAME_EN

# データファイルの収集
datas = [
    ('config.ini', '.'),
    ('styles', 'styles'),
]

# PyMuPDFのデータファイルを含める
datas += collect_data_files('fitz')

# 隠れたインポートの明示的な指定
hiddenimports = [
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'PyQt6.sip',
    'pytesseract',
    'fitz',
    'pandas',
    'jaconv',
    'send2trash',
    'filelock',
]

# PyQt6の全サブモジュールを収集
hiddenimports += collect_submodules('PyQt6')

a = Analysis(
    ['main.py'],
    pathex=[spec_root],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'scipy',
        'tkinter',
        'unittest',
        'test',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher
)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME_EN,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # GUIアプリケーションなのでコンソールは非表示
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='installer/icon.ico' if os.path.exists('installer/icon.ico') else None,
    version='file_version_info.txt' if os.path.exists('file_version_info.txt') else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=APP_NAME_EN,
)
