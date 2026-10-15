# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Recolectar datos y recursos de customtkinter
ctk_datas = collect_data_files('customtkinter')

added_datas = [
    ('icon.ico', '.'),
    ('icon.png', '.'),
    ('sync_logic.py', '.'),
] + ctk_datas

hidden_imports = [
    'pystray',
    'pystray._win32',
    'watchdog',
    'watchdog.observers',
    'watchdog.observers.read_directory_changes',
    'watchdog.events',
    'PIL',
    'PIL.Image',
    'PIL.ImageDraw',
    'PIL._tkinter_finder',
    'customtkinter',
    'httpx',
    'sqlite3',
]

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=added_datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter.test', 'unittest'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='KognitoSync',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='KognitoSync',
)
