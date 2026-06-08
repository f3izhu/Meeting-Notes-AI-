# Packaging

This folder contains packaging helpers for local Windows builds.

## Cost Notes

- PyInstaller can build local `.exe` files without licensing cost for this project.
- pystray and Pillow are free/open-source dependencies used for tray behavior and icons.
- `MeetingNotesAI.iss` is an optional Inno Setup installer script. Inno Setup is free for non-commercial use; commercial users are requested by Inno Setup's publisher to buy a commercial license.
- Trusted Windows code signing usually costs money because certificates are issued by certificate authorities.

Unsigned builds are fine for local testing and portfolio demos, but Windows SmartScreen may warn users until the app is signed and/or has reputation.

## Build

```powershell
cd C:\Users\mites\OneDrive\Desktop\Codex\meeting-notes-ai
.venv\Scripts\Activate.ps1
python scripts\create_icon.py
python scripts\build_windows.py
```

The executable will be created under `dist\MeetingNotesAI`.

## Optional Installer

If Inno Setup is installed, open `packaging\MeetingNotesAI.iss` in the Inno Setup compiler after the PyInstaller build completes. The installer output is written to `dist\installer`.

The installer is user-level (`PrivilegesRequired=lowest`) and installs under `%LOCALAPPDATA%\Programs\Meeting Notes AI` by default, so it does not need admin rights.

## Desktop Shortcut

To create a local desktop shortcut with the project icon:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\create_shortcut.ps1
```

The shortcut prefers `dist\MeetingNotesAI\MeetingNotesAI.exe` when available and falls back to `launch.pyw` for source-development use.
