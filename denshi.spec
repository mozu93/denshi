# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller設定ファイル - 電子帳簿保存システム
このファイルはbuild.pyから自動的に使用されます。
"""

import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, collect_all

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

# numpy と pandas のすべてを収集
numpy_datas, numpy_binaries, numpy_hiddenimports = collect_all('numpy')
pandas_datas, pandas_binaries, pandas_hiddenimports = collect_all('pandas')

datas += numpy_datas
datas += pandas_datas

# 隠れたインポートの明示的な指定
hiddenimports = [
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'PyQt6.sip',
    'pytesseract',
    'fitz',
    'pandas',
    'pandas._libs',
    'pandas._libs.tslibs',
    'pandas._libs.tslibs.base',
    'pandas._libs.tslibs.np_datetime',
    'pandas._libs.tslibs.timedeltas',
    'pandas._libs.tslibs.timestamps',
    'numpy',
    'numpy.core',
    'numpy.core._multiarray_umath',
    'jaconv',
    'send2trash',
    'filelock',
]

# PyQt6の全サブモジュールを収集
hiddenimports += collect_submodules('PyQt6')

a = Analysis(
    ['main.py'],
    pathex=[spec_root],
    binaries=numpy_binaries + pandas_binaries,
    datas=datas,
    hiddenimports=hiddenimports + numpy_hiddenimports + pandas_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
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
