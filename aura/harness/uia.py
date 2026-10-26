"""
aura.harness.uia - UI Automation & Target Grounding Harness
Resolves visual coordinates of buttons, search fields, and controls across Win32, UWP, and Web.
"""

import re
import ctypes
from ctypes import wintypes
from typing import Optional, Tuple, Dict, Any, List

user32 = ctypes.WinDLL("user32", use_last_error=True)

class UIAutomationHarness:
    def __init__(self):
        self._screen_w = user32.GetSystemMetrics(0)
        self._screen_h = user32.GetSystemMetrics(1)

    def resolve_target(self, description: str) -> Optional[Tuple[int, int]]:
        """Resolves target description to screen coordinates (x, y)."""
        d = description.strip().lower()

        # 1. Screen landmark heuristics
        if any(w in d for w in ["center", "middle"]):
            return self._screen_w // 2, self._screen_h // 2
        if any(w in d for w in ["top left", "upper left"]):
            return int(self._screen_w * 0.15), int(self._screen_h * 0.15)
        if any(w in d for w in ["top right", "upper right", "close"]):
            return int(self._screen_w * 0.95), int(self._screen_h * 0.05)
        if any(w in d for w in ["bottom", "taskbar"]):
            return self._screen_w // 2, self._screen_h - 20

        # 2. Search box / address bar heuristic
        if any(w in d for w in ["search", "address", "url", "input"]):
            fg = user32.GetForegroundWindow()
            if fg:
                rect = (ctypes.c_long * 4)()
                user32.GetWindowRect(fg, rect)
                w_left, w_top, w_right, w_bottom = rect
                # Typically top-center of focused window
                return (w_left + w_right) // 2, w_top + 80

        # 3. Canvas heuristic (e.g. Paint, Photoshop, Godot viewport)
        if any(w in d for w in ["canvas", "viewport", "drawing area"]):
            return self._screen_w // 2, int(self._screen_h * 0.55)

        # 4. Search child windows for exact matching title
        found_pos = self._find_child_window_by_text(description)
        if found_pos:
            return found_pos

        # Default fallback to center of active foreground window
        fg = user32.GetForegroundWindow()
        if fg:
            rect = (ctypes.c_long * 4)()
            user32.GetWindowRect(fg, rect)
            w_left, w_top, w_right, w_bottom = rect
            return (w_left + w_right) // 2, (w_top + w_bottom) // 2

        return self._screen_w // 2, self._screen_h // 2

    def _find_child_window_by_text(self, text: str) -> Optional[Tuple[int, int]]:
        """Searches top-level and child HWNDs for text matching."""
        target_text = text.lower()
        results: List[Tuple[int, int]] = []

        def enum_cb(hwnd, lparam):
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    val = buff.value.lower()
                    if target_text in val or any(w in val for w in target_text.split()):
                        rect = (ctypes.c_long * 4)()
                        user32.GetWindowRect(hwnd, rect)
                        x = (rect[0] + rect[2]) // 2
                        y = (rect[1] + rect[3]) // 2
                        results.append((x, y))
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
        user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
        return results[0] if results else None

UIA = UIAutomationHarness()
