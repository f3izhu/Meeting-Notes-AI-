"""Wrapper entry point for Meeting Notes AI UI."""
from __future__ import annotations

import os
from datetime import date
from tkinter import messagebox
from meeting_notes_ai.config import APP_DIR
from meeting_notes_ai.ui.todo_manager import TODO_PATH, TODO_ENC_PATH
from meeting_notes_ai.ui.app import MeetingNotesUI, main

__all__ = [
    "MeetingNotesUI",
    "TODO_PATH",
    "TODO_ENC_PATH",
    "APP_DIR",
    "date",
    "main",
    "messagebox",
    "os",
]
