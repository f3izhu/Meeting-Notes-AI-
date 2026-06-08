# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

ROOT = Path(SPECPATH).resolve().parent
ICON = ROOT / "assets" / "MeetingNotesAI.ico"

a = Analysis(
    [str(ROOT / "launch.pyw")],
    pathex=[str(ROOT), str(ROOT / "src")],
    binaries=[],
    datas=[(str(ROOT / "src"), "src"), (str(ROOT / "Launch.bat"), ".")],
    hiddenimports=[
        "soundcard",
        "faster_whisper",
        "ctranslate2",
        "pystray",
        "PIL",
        "cryptography",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "pytest",
        "_pytest",
        "tests",
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MeetingNotesAI",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=str(ICON) if ICON.exists() else None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="MeetingNotesAI",
)
