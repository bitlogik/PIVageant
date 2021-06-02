# -*- mode: python ; coding: utf-8 -*-

import os

pkgs_remove = [
    "sqlite3",
    "tcl85",
    "tk85",
    "_sqlite3",
    "_tkinter",
    "libopenblas",
    "libdgamln",
]

dataset = Analysis(
    ["../PIVageant.pyw"],
    binaries=[],
    datas=[("../res/pivageant.ico", "res/")],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        "_gtkagg",
        "_tkagg",
        "curses",
        "pywin.debugger",
        "pywin.debugger.dbgcon",
        "pywin.dialogs",
        "tcl",
        "Tkconstants",
        "Tkinter",
        "libopenblas",
        "libdgamln",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

for pkg in pkgs_remove:
    dataset.binaries = [x for x in dataset.binaries if not x[0].startswith(pkg)]

pyz = PYZ(dataset.pure, dataset.zipped_data, cipher=None)

exe = EXE(
    pyz,
    dataset.scripts,
    dataset.binaries,
    dataset.zipfiles,
    dataset.datas,
    [],
    name="PIVageant",
    debug=False,
    bootloader_ignore_signals=False,
    icon="../res/pivageant.ico",
    strip=False,
    upx=True,
    upx_exclude=[],
    console=False,
)
