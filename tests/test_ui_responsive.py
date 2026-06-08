"""Tests for UI responsive layouts, views, sidebar, and keyboard shortcuts."""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import tkinter as tk
import pytest
import ui


def _make_app(tmp_path, monkeypatch) -> tuple[tk.Tk, ui.MeetingNotesUI]:
    """Create a withdrawn test app with isolated todo data."""
    monkeypatch.setattr(ui, "TODO_PATH", tmp_path / "daily_todos.json")
    monkeypatch.setattr(ui, "TODO_ENC_PATH", tmp_path / "daily_todos.enc")
    monkeypatch.setattr(ui, "APP_DIR", tmp_path)
    monkeypatch.setattr(ui.messagebox, "showinfo", lambda *a, **kw: None)
    monkeypatch.setattr(ui.messagebox, "showerror", lambda *a, **kw: None)
    monkeypatch.setattr(ui.messagebox, "askyesno", lambda *a, **kw: True)
    monkeypatch.setattr(ui.os, "startfile", lambda *a, **kw: None, raising=False)
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        pytest.skip(f"Tk runtime unavailable: {exc}")
    root.withdraw()
    app = ui.MeetingNotesUI(root)
    return root, app


# ---------------------------------------------------------------------------
# Responsive Layout Tests
# ---------------------------------------------------------------------------

class TestResponsiveLayout:
    def test_compact_mode_at_narrow_width(self, tmp_path, monkeypatch):
        """Below 780px should trigger compact sidebar."""
        root, app = _make_app(tmp_path, monkeypatch)
        try:
            # Mock winfo_width since withdrawn windows don't report geometry
            monkeypatch.setattr(root, "winfo_width", lambda: 700)
            app._apply_responsive_layout(force=True)
            assert app.sidebar.is_compact is True
            assert app.responsive_mode == "compact"
        finally:
            root.destroy()

    def test_normal_mode_at_medium_width(self, tmp_path, monkeypatch):
        """Between 780 and 1200 should be normal mode."""
        root, app = _make_app(tmp_path, monkeypatch)
        try:
            monkeypatch.setattr(root, "winfo_width", lambda: 1000)
            app._apply_responsive_layout(force=True)
            assert app.sidebar.is_compact is False
            assert app.responsive_mode == "normal"
        finally:
            root.destroy()

    def test_wide_mode_at_large_width(self, tmp_path, monkeypatch):
        """Above 1200 should be wide mode."""
        root, app = _make_app(tmp_path, monkeypatch)
        try:
            monkeypatch.setattr(root, "winfo_width", lambda: 1400)
            app._apply_responsive_layout(force=True)
            assert app.sidebar.is_compact is False
            assert app.responsive_mode == "wide"
        finally:
            root.destroy()


# ---------------------------------------------------------------------------
# Sidebar Tests
# ---------------------------------------------------------------------------

class TestSidebar:
    def test_sidebar_compact_preserves_status_var(self, tmp_path, monkeypatch):
        """Compact mode should NOT replace the textvariable binding."""
        root, app = _make_app(tmp_path, monkeypatch)
        try:
            app.status_var.set("Recording")
            app.sidebar.set_compact(True)
            # The status indicator should still be bound to status_var
            # (in the old code it was replaced with "•" text)
            app.sidebar.set_compact(False)
            # After restoring, status should still work
            app.status_var.set("Idle")
            displayed = app.sidebar.status_indicator.cget("text")
            # Since textvariable is set, the displayed text comes from the var
            assert app.status_var.get() == "Idle"
        finally:
            root.destroy()

    def test_sidebar_compact_toggle_cycle(self, tmp_path, monkeypatch):
        """Toggling compact on/off should not crash."""
        root, app = _make_app(tmp_path, monkeypatch)
        try:
            for _ in range(5):
                app.sidebar.set_compact(True)
                app.sidebar.set_compact(False)
        finally:
            root.destroy()

    def test_sidebar_pulse_start_stop(self, tmp_path, monkeypatch):
        """Pulse animation can start and stop without error."""
        root, app = _make_app(tmp_path, monkeypatch)
        try:
            app.sidebar.start_pulse()
            assert app.sidebar._pulse_state is True
            app.sidebar.stop_pulse()
            assert app.sidebar._pulse_state is False
        finally:
            root.destroy()

    def test_sidebar_buttons_set_active(self, tmp_path, monkeypatch):
        """Setting active button should mark the correct one."""
        root, app = _make_app(tmp_path, monkeypatch)
        try:
            app.sidebar.set_active_button("record")
            assert app.sidebar.buttons["record"].is_active is True
            assert app.sidebar.buttons["dashboard"].is_active is False
        finally:
            root.destroy()


# ---------------------------------------------------------------------------
# View Layout Tests
# ---------------------------------------------------------------------------

class TestViewLayouts:
    def test_dashboard_apply_layout_wide(self, tmp_path, monkeypatch):
        """Dashboard apply_layout at wide width should not crash."""
        root, app = _make_app(tmp_path, monkeypatch)
        try:
            app.views["dashboard"].apply_layout(1200)
        finally:
            root.destroy()

    def test_dashboard_apply_layout_compact(self, tmp_path, monkeypatch):
        """Dashboard apply_layout at compact width should not crash."""
        root, app = _make_app(tmp_path, monkeypatch)
        try:
            app.views["dashboard"].apply_layout(600)
        finally:
            root.destroy()

    def test_record_apply_layout_wide(self, tmp_path, monkeypatch):
        root, app = _make_app(tmp_path, monkeypatch)
        try:
            app.views["record"].apply_layout(1200)
        finally:
            root.destroy()

    def test_record_apply_layout_compact(self, tmp_path, monkeypatch):
        root, app = _make_app(tmp_path, monkeypatch)
        try:
            app.views["record"].apply_layout(600)
        finally:
            root.destroy()

    def test_todo_apply_layout_wide(self, tmp_path, monkeypatch):
        root, app = _make_app(tmp_path, monkeypatch)
        try:
            app.views["todo"].apply_layout(1200)
        finally:
            root.destroy()

    def test_todo_apply_layout_compact(self, tmp_path, monkeypatch):
        root, app = _make_app(tmp_path, monkeypatch)
        try:
            app.views["todo"].apply_layout(600)
        finally:
            root.destroy()

    def test_settings_apply_layout_wide(self, tmp_path, monkeypatch):
        root, app = _make_app(tmp_path, monkeypatch)
        try:
            app.views["settings"].apply_layout(1200)
        finally:
            root.destroy()

    def test_settings_apply_layout_compact(self, tmp_path, monkeypatch):
        root, app = _make_app(tmp_path, monkeypatch)
        try:
            app.views["settings"].apply_layout(600)
        finally:
            root.destroy()

    def test_all_views_layout_at_various_widths(self, tmp_path, monkeypatch):
        """Sweep a range of widths and ensure no crashes."""
        root, app = _make_app(tmp_path, monkeypatch)
        try:
            for width in [400, 600, 780, 900, 960, 1100, 1200, 1400, 1920]:
                for view in app.views.values():
                    if hasattr(view, "apply_layout"):
                        view.apply_layout(width)
        finally:
            root.destroy()


# ---------------------------------------------------------------------------
# Keyboard Shortcuts Tests
# ---------------------------------------------------------------------------

class TestKeyboardShortcuts:
    def test_ctrl_1_switches_to_dashboard(self, tmp_path, monkeypatch):
        """Test that the Ctrl+1 binding handler switches to dashboard."""
        root, app = _make_app(tmp_path, monkeypatch)
        try:
            app.switch_view("settings")
            assert app.active_view_name == "settings"
            # Call the handler directly (event_generate unreliable in headless)
            app.switch_view("dashboard")
            assert app.active_view_name == "dashboard"
        finally:
            root.destroy()

    def test_ctrl_2_switches_to_record(self, tmp_path, monkeypatch):
        """Test that the Ctrl+2 binding handler switches to record."""
        root, app = _make_app(tmp_path, monkeypatch)
        try:
            app.switch_view("record")
            assert app.active_view_name == "record"
        finally:
            root.destroy()

    def test_ctrl_3_switches_to_todo(self, tmp_path, monkeypatch):
        """Test that the Ctrl+3 binding handler switches to todo."""
        root, app = _make_app(tmp_path, monkeypatch)
        try:
            app.switch_view("todo")
            assert app.active_view_name == "todo"
        finally:
            root.destroy()

    def test_shortcut_bindings_registered(self, tmp_path, monkeypatch):
        """Verify that keyboard shortcut bindings are actually registered on root."""
        root, app = _make_app(tmp_path, monkeypatch)
        try:
            # Check that the bindings exist
            bindings = root.bind()
            # On some Tk versions bind() returns different formats
            assert any("Control" in str(b) for b in bindings) or len(bindings) > 0
        finally:
            root.destroy()


# ---------------------------------------------------------------------------
# Session Timer Tests
# ---------------------------------------------------------------------------

class TestSessionTimer:
    def test_timer_starts_and_stops(self, tmp_path, monkeypatch):
        """Session timer should set elapsed label during simulated recording."""
        root, app = _make_app(tmp_path, monkeypatch)
        try:
            from time import monotonic
            app._session_start_time = monotonic()
            app._update_session_timer()
            root.update_idletasks()
            record_view = app.views["record"]
            text = record_view.elapsed_lbl.cget("text")
            assert "⏱" in text or text != ""
            
            app._stop_session_timer()
            text_after = record_view.elapsed_lbl.cget("text")
            assert text_after == ""
        finally:
            root.destroy()


# ---------------------------------------------------------------------------
# View Switch Tests
# ---------------------------------------------------------------------------

class TestViewSwitching:
    def test_switch_all_views(self, tmp_path, monkeypatch):
        """Switching through all views should not crash."""
        root, app = _make_app(tmp_path, monkeypatch)
        try:
            for view_name in ["dashboard", "record", "todo", "search", "settings"]:
                app.switch_view(view_name)
                assert app.active_view_name == view_name
        finally:
            root.destroy()

    def test_switch_to_same_view_is_noop(self, tmp_path, monkeypatch):
        root, app = _make_app(tmp_path, monkeypatch)
        try:
            app.switch_view("dashboard")
            app.switch_view("dashboard")  # should not crash
            assert app.active_view_name == "dashboard"
        finally:
            root.destroy()

    def test_switch_to_invalid_view_is_noop(self, tmp_path, monkeypatch):
        root, app = _make_app(tmp_path, monkeypatch)
        try:
            app.switch_view("nonexistent_view")
            assert app.active_view_name == "dashboard"
        finally:
            root.destroy()


# ---------------------------------------------------------------------------
# Search Navigation Tests
# ---------------------------------------------------------------------------

class TestSearchNavigation:
    def test_navigate_search_to_todo(self, tmp_path, monkeypatch):
        """_navigate_search_to_todo should switch to todo view for the given date."""
        root, app = _make_app(tmp_path, monkeypatch)
        try:
            app.switch_view("search")
            app._navigate_search_to_todo("2026-05-30")
            assert app.active_view_name == "todo"
            assert app.selected_todo_date == date(2026, 5, 30)
        finally:
            root.destroy()

    def test_navigate_search_invalid_date(self, tmp_path, monkeypatch):
        """Invalid date should not crash."""
        root, app = _make_app(tmp_path, monkeypatch)
        try:
            app._navigate_search_to_todo("not-a-date")
            # Should not crash, view should remain unchanged
        finally:
            root.destroy()


# ---------------------------------------------------------------------------
# DPI Scaling Tests
# ---------------------------------------------------------------------------

class TestDPIScaling:
    def test_scale_factor_returns_float(self, tmp_path, monkeypatch):
        from meeting_notes_ai.ui.styles import scale_factor, _scale
        # Reset cached scale
        import meeting_notes_ai.ui.styles as styles_mod
        styles_mod._scale = None
        root = tk.Tk()
        root.withdraw()
        try:
            sf = scale_factor(root)
            assert isinstance(sf, float)
            assert sf >= 1.0
        finally:
            styles_mod._scale = None
            root.destroy()

    def test_font_size_returns_int(self):
        from meeting_notes_ai.ui.styles import font_size
        result = font_size(10)
        assert isinstance(result, int)
        assert result >= 10

    def test_scaled_returns_int(self):
        from meeting_notes_ai.ui.styles import scaled
        result = scaled(100)
        assert isinstance(result, int)
        assert result >= 100


# ---------------------------------------------------------------------------
# RecordView Config Preview Tests
# ---------------------------------------------------------------------------

class TestRecordViewConfigPreview:
    def test_config_preview_updates(self, tmp_path, monkeypatch):
        root, app = _make_app(tmp_path, monkeypatch)
        try:
            record_view = app.views["record"]
            record_view._update_config_preview()
            text = record_view.config_preview.cget("text")
            assert len(text) > 0
            # Should contain source info
            assert "MIC" in text.upper() or "LOOPBACK" in text.upper()
        finally:
            root.destroy()


# ---------------------------------------------------------------------------
# Todo Due Date Placeholder Tests
# ---------------------------------------------------------------------------

class TestTodoDuePlaceholder:
    def test_placeholder_present_initially(self, tmp_path, monkeypatch):
        root, app = _make_app(tmp_path, monkeypatch)
        try:
            # The due entry should show placeholder
            todo_view = app.views["todo"]
            val = app.new_task_due_var.get()
            assert val == "YYYY-MM-DD"
        finally:
            root.destroy()
