"""
Launch wrapper for Meeting Notes AI.
Save as .pyw so Windows runs it with pythonw.exe automatically.
All errors are caught and shown as message boxes instead of being silently lost.
"""
import sys
import traceback
from pathlib import Path

# Resolve project root from this file's location
ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"

# Ensure the source package is importable
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

def show_error(title: str, message: str) -> None:
    """Show an error dialog even if tkinter isn't fully working."""
    try:
        import tkinter as tk
        from tkinter import messagebox
        tmp = tk.Tk()
        tmp.withdraw()
        messagebox.showerror(title, message)
        tmp.destroy()
    except Exception:
        # Last resort: write to a log file on the desktop
        try:
            log = Path.home() / "Desktop" / "meeting_notes_ai_error.log"
            log.write_text(f"{title}\n\n{message}", encoding="utf-8")
        except Exception:
            pass

def main() -> None:
    try:
        # Import and run the real UI
        from ui import main as ui_main
        ui_main()
    except Exception:
        show_error(
            "Meeting Notes AI - Launch Error",
            f"The application failed to start.\n\n{traceback.format_exc()}"
        )
        sys.exit(1)

if __name__ == "__main__":
    main()
