# Local Meeting Notes AI (Free + Offline-first)

This project gives you a local meeting assistant focused on speed and ease of use:

- real-time listening from microphone (face-to-face) or loopback input (online meetings),
- local transcription via `faster-whisper`,
- live status telemetry (audio level + transcription latency + real-time factor),
- live notes snapshots (key points, decisions, action items),
- structured action items (`task`, `owner`, `due`) in final output,
- crash-safe autosave snapshots during recording,
- guided first-run setup and persistent defaults.

No paid API is required.

## Why this stack

- `faster-whisper`: strong accuracy/speed tradeoff for local transcription.
- `SoundCard`: simple access to mic and Windows WASAPI loopback devices.
- Optional `Ollama`: better final summary quality with a small local model (`gemma3:1b` by default).

## Requirements

- Windows 10/11
- Python 3.10+
- A microphone (for in-person meetings)
- Optional: Ollama installed locally for better summaries

## Install

```powershell
cd C:\Users\mites\OneDrive\Desktop\Codex\meeting-notes-ai
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Usage

### Launch Desktop UI (recommended)

```powershell
cd C:\Users\mites\OneDrive\Desktop\Codex\meeting-notes-ai
.venv\Scripts\Activate.ps1
python ui.py
```

The UI gives you:
- dashboard for today's tasks, reminders, latest meetings, quick capture, and Ollama status,
- start/stop buttons,
- microphone or loopback source selection,
- audio device picker,
- profile/model controls,
- inference device control (`cpu` recommended default),
- editable output folder path,
- simulation mode for quick end-to-end testing,
- live logs,
- daily todo/history tab with priorities, due dates, carry-over tasks, and calendar date selection,
- one-click import from meeting action items into today's task list,
- search across meeting outputs and todos,
- manual transcript correction tools,
- local Markdown/HTML todo export,
- optional passphrase encryption for daily todo storage,
- real system tray minimize support when tray dependencies are installed,
- optional user-level Windows startup controls,
- one-click open for output/config folders.

Daily todos are stored locally at:

`C:\Users\<you>\.meeting-notes-ai\daily_todos.json`

When the app opens, the Daily Todo tab always starts on today's date. Use the calendar, month selector, year field, Prev/Today/Next buttons, or marked calendar days to browse previous notes.

Daily todo tasks can be checked off when done. Completed tasks stay on the day where they were created. Unfinished tasks automatically appear on later days under `Previous Tasks` until they are checked off.

Use `Import Meeting Actions` to pull action items from the latest meeting summary into today's task list. Search, exports, dashboard reminders, and quick-capture notes all use the same local todo/history file.

Use `Encrypt Todos` if you want daily todos protected with a passphrase. This creates `daily_todos.enc` and removes the plaintext todo JSON file. Keep the passphrase safe; encrypted todos cannot be recovered without it.

## Packaging

Local Windows packaging helpers are in `packaging/` and `scripts/`.

```powershell
python scripts\create_icon.py
python scripts\build_windows.py
```

This creates a PyInstaller build under `dist\MeetingNotesAI`. Trusted code signing is not included because real Windows signing certificates usually cost money. Unsigned local builds are fine for testing and portfolio demos, but Windows SmartScreen may warn users.

To create a local desktop shortcut with the custom icon:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\create_shortcut.ps1
```

If you later want a traditional Windows installer, compile `packaging\MeetingNotesAI.iss` with Inno Setup after running the PyInstaller build. For a personal/open-source portfolio project, the current PyInstaller flow has no required packaging fee. Commercial installer distribution and trusted code signing can introduce costs.

The startup buttons create or remove a small command file in your user Startup folder. This does not require admin permission and can be disabled from the app at any time.

### Health check (recommended before first real run)

```powershell
python run.py --doctor
```

### 1) Run guided setup (recommended first run)

```powershell
python run.py --setup
```

This saves defaults to:

`C:\Users\<you>\.meeting-notes-ai\config.json`

### 2) See active defaults

```powershell
python run.py --show-config
```

### 3) See available input devices

```powershell
python run.py --list-devices
```

### 4) Face-to-face meeting (default microphone)

```powershell
python run.py
```

### 5) Online meeting capture (prefer loopback)

```powershell
python run.py --loopback
```

If your loopback device name is specific, pass:

```powershell
python run.py --device "Speakers"
```

### 6) Disable Ollama (fallback summary only)

```powershell
python run.py --no-ollama
```

### 6b) Force CPU inference (recommended if CUDA DLL errors appear)

```powershell
python run.py --inference-device cpu
```

### 7) Add meeting title + auto-stop after N minutes

```powershell
python run.py --meeting-title "Weekly Product Sync" --max-minutes 45
```

### 8) End-to-end simulation (no mic / no model download)

```powershell
python run.py --simulate --simulate-duration 90 --meeting-title "E2E Demo"
```

### 9) Full pre-handoff automated test

```powershell
python scripts\e2e_handoff_test.py
```

### 10) Smoke test suite

```powershell
python -m pytest -q
```

## Output

Saved in `outputs/`:

- `meeting_YYYYMMDD_HHMMSS_transcript.txt`
- `meeting_YYYYMMDD_HHMMSS_summary.json`
- `meeting_YYYYMMDD_HHMMSS_notes.md`
- `meeting_YYYYMMDD_HHMMSS_notes.html`
- `meeting_YYYYMMDD_HHMMSS_autosave.json` (periodic crash-safe snapshots)

If no transcript is captured, the app still saves transcript, summary, Markdown, and HTML diagnostic files with troubleshooting tips. In the UI, this appears as a "Check audio" state so you know the run completed but the selected device did not provide usable speech.

For online meetings, play a short sample from the meeting app after pressing Start and watch the audio meter. If it stays near `-120 dB`, choose a different loopback device that matches your active speakers or headphones.

## Performance profiles

- `--profile fast`: lower latency, lighter model (`tiny.en`)
- `--profile balanced`: recommended default (`small.en`)
- `--profile accurate`: higher quality, heavier model (`medium.en`)
- `--profile auto`: picks based on local CPU

You can persist any run settings:

```powershell
python run.py --profile fast --loopback --save-preferences
```

## Optional: Improve summary quality with Ollama

1. Install Ollama (Windows installer).
2. Pull a small free model:

```powershell
ollama run gemma3:1b
```

Then run the app normally. It will call `http://localhost:11434/api/chat` automatically.

## Notes and limits

- This build optimizes practical UX and local operation, not perfect diarization.
- If you need per-speaker labels ("Alice said..."), add diarization in the next iteration.
- Audio permissions and loopback availability depend on device/driver support.

## Online resources used

- Faster-Whisper repo: <https://github.com/SYSTRAN/faster-whisper>
- SoundCard PyPI: <https://pypi.org/project/SoundCard/>
- Ollama docs: <https://docs.ollama.com/>
- Ollama API intro: <https://docs.ollama.com/api/introduction>
- Gemma 3 model page in Ollama library: <https://ollama.com/library/gemma3>
