"""Premium styling and color configurations for Meeting Notes AI."""
from __future__ import annotations
import os
import sys
import tkinter as tk
from tkinter import ttk

# Catppuccin Mocha themed dark colors
BG_CRUST = "#11111b"     # Very dark for sidebar background
BG_MANTLE = "#181825"    # Slightly lighter for main app frame
BG_SURFACE = "#1e1e2e"   # Medium dark for cards and dialogs
BG_OVERLAY = "#313244"   # Contrast color for inputs, scrollbars, inactive buttons
TEXT_MAIN = "#cdd6f4"    # Bright text
TEXT_SUB = "#a6adc8"     # Secondary subtext
TEXT_MUTED = "#7f849c"   # Darker muted text

ACCENT_BLUE = "#89b4fa"  # Primary blue highlight
ACCENT_GREEN = "#a6e3a1" # Success status, active recording start
ACCENT_RED = "#f38ba8"   # Alert/stop status
ACCENT_YELLOW = "#f9e2af"# Warning status, diagnostic states

COLOR_ACTIVE_HOVER = "#45475a"
COLOR_RECORD_HOVER = "#406f5c"
COLOR_STOP_HOVER = "#e05f6e"

FONT_FAMILY = "Segoe UI"
FONT_MONO = "Consolas"

# DPI scaling cache
_scale: float | None = None


def enable_dpi_awareness() -> None:
    """Enable per-monitor DPI awareness on Windows. Must be called before Tk root creation."""
    if os.name != "nt":
        return
    try:
        import ctypes
        # Try per-monitor DPI awareness (Win 8.1+)
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            # Fall back to system DPI awareness
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(1)
            except Exception:
                ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def scale_factor(root: tk.Tk | None = None) -> float:
    """Return a DPI scale factor (1.0 = 96 DPI). Caches after first call."""
    global _scale
    if _scale is not None:
        return _scale
    _scale = 1.0
    if root is not None:
        try:
            dpi = root.winfo_fpixels("1i")
            _scale = max(1.0, dpi / 96.0)
        except Exception:
            pass
    return _scale


def scaled(value: int, root: tk.Tk | None = None) -> int:
    """Scale an integer value by the current DPI factor."""
    return int(value * scale_factor(root))


def font_size(base: int, root: tk.Tk | None = None) -> int:
    """Scale a font size by DPI, clamped to reasonable range."""
    sf = scale_factor(root)
    # Fonts on Windows already scale with DPI awareness; only scale if ratio > 1.5
    if sf > 1.5:
        return max(base, int(base * (sf / 1.5)))
    return base


def configure_styles(root: tk.Tk) -> None:
    """Configure option database and TTK style configurations."""
    # Initialize scale factor from root
    sf = scale_factor(root)
    
    root.configure(bg=BG_MANTLE)
    
    # Configure root option database for popups/dropdown listboxes
    root.option_add("*TCombobox*Listbox.background", BG_SURFACE)
    root.option_add("*TCombobox*Listbox.foreground", TEXT_MAIN)
    root.option_add("*TCombobox*Listbox.selectBackground", ACCENT_BLUE)
    root.option_add("*TCombobox*Listbox.selectForeground", BG_SURFACE)
    root.option_add("*TCombobox*Listbox.font", (FONT_FAMILY, font_size(10, root)))

    style = ttk.Style()
    style.theme_use("clam")

    fs10 = font_size(10, root)
    fs9 = font_size(9, root)
    fs8 = font_size(8, root)
    fs11 = font_size(11, root)
    fs12 = font_size(12, root)
    fs16 = font_size(16, root)

    # Frame configurations
    style.configure("TFrame", background=BG_MANTLE)
    style.configure("Sidebar.TFrame", background=BG_CRUST, relief="flat")
    style.configure("Card.TFrame", background=BG_SURFACE, relief="flat")
    
    # Label configurations
    style.configure("TLabel", background=BG_MANTLE, foreground=TEXT_MAIN, font=(FONT_FAMILY, fs10))
    style.configure("Muted.TLabel", background=BG_MANTLE, foreground=TEXT_MUTED, font=(FONT_FAMILY, fs9))
    style.configure("CardHeader.TLabel", background=BG_SURFACE, foreground=ACCENT_BLUE, font=(FONT_FAMILY, fs11, "bold"))
    style.configure("CardText.TLabel", background=BG_SURFACE, foreground=TEXT_MAIN, font=(FONT_FAMILY, fs10))
    style.configure("CardMuted.TLabel", background=BG_SURFACE, foreground=TEXT_MUTED, font=(FONT_FAMILY, fs9))
    style.configure("Title.TLabel", background=BG_MANTLE, foreground=ACCENT_BLUE, font=(FONT_FAMILY, fs16, "bold"))

    style.configure("SidebarHeader.TLabel", background=BG_CRUST, foreground=TEXT_MAIN, font=(FONT_FAMILY, fs12, "bold"))

    # Interactive elements
    style.configure("TRadiobutton", background=BG_SURFACE, foreground=TEXT_MAIN, font=(FONT_FAMILY, fs10))
    style.map("TRadiobutton", background=[("active", BG_SURFACE)], foreground=[("active", ACCENT_BLUE)])

    style.configure("TCheckbutton", background=BG_SURFACE, foreground=TEXT_MAIN, font=(FONT_FAMILY, fs10))
    style.map("TCheckbutton", background=[("active", BG_SURFACE)], foreground=[("active", ACCENT_BLUE)])

    style.configure("TNotebook", background=BG_MANTLE, borderwidth=0)
    style.configure("TNotebook.Tab", background=BG_SURFACE, foreground=TEXT_MUTED, font=(FONT_FAMILY, fs10, "bold"), padding=[14, 6])
    style.map("TNotebook.Tab", background=[("selected", BG_MANTLE)], foreground=[("selected", ACCENT_BLUE)])

    style.configure("TCombobox", 
                    fieldbackground=BG_SURFACE, 
                    background=BG_OVERLAY, 
                    foreground=TEXT_MAIN, 
                    font=(FONT_FAMILY, fs10), 
                    arrowcolor=TEXT_MAIN, 
                    bordercolor=BG_OVERLAY, 
                    lightcolor=BG_OVERLAY, 
                    darkcolor=BG_OVERLAY)
    style.map("TCombobox", fieldbackground=[("readonly", BG_SURFACE)], selectbackground=[("readonly", ACCENT_BLUE)])

    style.configure("TEntry", fieldbackground=BG_SURFACE, foreground=TEXT_MAIN, font=(FONT_FAMILY, fs10), bordercolor=BG_OVERLAY, lightcolor=BG_OVERLAY, darkcolor=BG_OVERLAY)
    
    style.configure("Vertical.TScrollbar", background=BG_OVERLAY, troughcolor=BG_MANTLE, bordercolor=BG_MANTLE, arrowcolor=TEXT_MAIN, relief="flat")
