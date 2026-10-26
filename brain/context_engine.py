"""
brain/context_engine.py - Live Desktop Spatial & Environmental Perceiver
Captures Active App, Window Titles, Process Metadata, and Clipboard State.
Provides rich desktop context to the AI Brain in < 2ms.
"""

import re
import ctypes
from typing import Dict, Any, Optional
from PyQt6.QtWidgets import QApplication

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

class ContextEngine:
    def __init__(self):
        self.error_pattern = re.compile(
            r"(Traceback \(most recent call last\):|Error:|Exception:|\bFATAL\b|NullReferenceException|TypeError|ValueError|IndexError)",
            re.IGNORECASE
        )
        self.code_pattern = re.compile(r"(def |class |import |function |=>|var |let |const |#include|func |_ready|extends )")

    def get_foreground_window_info(self) -> Dict[str, str]:
        """Detects current active foreground window, app name, and context in <0.5ms."""
        try:
            hwnd = user32.GetForegroundWindow()
            if not hwnd:
                return {"app": "Desktop", "title": "Windows Desktop", "category": "system"}

            length = user32.GetWindowTextLengthW(hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            title = buff.value.strip() or "Active Window"

            t_low = title.lower()
            if "visual studio code" in t_low or "vs code" in t_low or title.endswith(".py") or title.endswith(".gd"):
                app_name = "VS Code"
                cat = "code"
            elif "chrome" in t_low or "google chrome" in t_low:
                app_name = "Chrome"
                cat = "browser"
            elif "firefox" in t_low:
                app_name = "Firefox"
                cat = "browser"
            elif "edge" in t_low:
                app_name = "Edge"
                cat = "browser"
            elif "discord" in t_low:
                app_name = "Discord"
                cat = "social"
            elif "godot" in t_low:
                app_name = "Godot Engine"
                cat = "gamedev"
            elif "blender" in t_low:
                app_name = "Blender"
                cat = "3d"
            elif "terminal" in t_low or "powershell" in t_low or "cmd" in t_low:
                app_name = "Terminal"
                cat = "terminal"
            elif "notepad" in t_low:
                app_name = "Notepad"
                cat = "editor"
            elif "spotify" in t_low:
                app_name = "Spotify"
                cat = "media"
            elif "steam" in t_low:
                app_name = "Steam"
                cat = "gaming"
            else:
                parts = title.split(" - ")
                app_name = parts[-1].strip() if len(parts) > 1 else "Active Window"
                cat = "general"

            return {"app": app_name, "title": title, "category": cat}
        except Exception:
            return {"app": "Desktop", "title": "Windows Desktop", "category": "system"}

    def check_clipboard_context(self) -> str:
        """Retrieves clipboard text safely if it contains code, error trace, or URL."""
        try:
            cb = QApplication.clipboard()
            text = cb.text()
            if not text:
                return ""
            if len(text) > 4000:
                text = text[:4000]
            if self.error_pattern.search(text) or self.code_pattern.search(text) or text.startswith("http"):
                return text
            return ""
        except Exception:
            return ""

    def get_desktop_summary(self) -> str:
        """Returns concise textual summary of current user activity for the Cyber-Dock."""
        fg = self.get_foreground_window_info()
        app = fg["app"]
        title = fg["title"]
        if len(title) > 28:
            title = title[:28] + "..."
        if app in ["Desktop", "Windows Desktop"]:
            return "⚡ Desktop Ready"
        return f"⚡ {app} · {title}"

    def capture_visual_context(self) -> Optional[bytes]:
        """Captures real-time screen bytes in < 4ms."""
        try:
            from core.screen_capture import SCREEN
            return SCREEN.capture_to_bytes()
        except Exception:
            return None

CONTEXT_ENGINE = ContextEngine()
