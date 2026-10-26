"""
aura.harness.perception - Sensory Perception Engine
Continuously samples active window telemetry, screen visual states, and clipboard data in < 3ms.
"""

import sys
import ctypes
from ctypes import wintypes
from typing import Optional, Dict, Any

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

class PerceptionHarness:
    def __init__(self):
        self._categories = {
            "code": ["code.exe", "devenv.exe", "pycharm64.exe", "sublime_text.exe", "cursor.exe", "windsurf.exe"],
            "terminal": ["windowsterminal.exe", "cmd.exe", "powershell.exe", "pwsh.exe", "bash.exe"],
            "browser": ["chrome.exe", "msedge.exe", "firefox.exe", "brave.exe", "opera.exe"],
            "engine": ["godot.exe", "unity.exe", "unreal.exe", "blender.exe"],
            "chat": ["slack.exe", "discord.exe", "teams.exe", "whatsapp.exe"]
        }

    def get_foreground_window(self) -> Dict[str, Any]:
        """Returns metadata of active foreground window in < 0.5ms."""
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return {"hwnd": 0, "title": "Desktop", "process": "explorer.exe", "category": "system"}

        length = user32.GetWindowTextLengthW(hwnd)
        buff = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buff, length + 1)
        title = buff.value.strip() or "Untitled"

        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        
        proc_name = self._resolve_process_name(pid.value)
        category = self._categorize(proc_name)

        return {
            "hwnd": hwnd,
            "title": title,
            "process": proc_name,
            "category": category,
            "pid": pid.value
        }

    def _resolve_process_name(self, pid: int) -> str:
        """Resolves process executable name via Win32 QueryFullProcessImageName."""
        if pid == 0:
            return "system"
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        h_proc = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not h_proc:
            return "unknown"
        try:
            buff = ctypes.create_unicode_buffer(512)
            size = wintypes.DWORD(512)
            if kernel32.QueryFullProcessImageNameW(h_proc, 0, buff, ctypes.byref(size)):
                full_path = buff.value
                return full_path.split("\\")[-1].lower()
        finally:
            kernel32.CloseHandle(h_proc)
        return "unknown"

    def _categorize(self, proc_name: str) -> str:
        name = proc_name.lower()
        for cat, procs in self._categories.items():
            if any(p in name for p in procs):
                return cat
        return "general"

    def get_clipboard_text(self) -> Optional[str]:
        """Safely extracts text from the system clipboard."""
        try:
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                clip = app.clipboard().text()
                return clip.strip() if clip else None
        except Exception:
            pass

        # Win32 clipboard fallback
        CF_UNICODETEXT = 13
        if not user32.OpenClipboard(None):
            return None
        try:
            h_data = user32.GetClipboardData(CF_UNICODETEXT)
            if not h_data:
                return None
            kernel32.GlobalLock.restype = ctypes.c_wchar_p
            ptr = kernel32.GlobalLock(h_data)
            if ptr:
                text = str(ptr)
                kernel32.GlobalUnlock(h_data)
                return text.strip() if text else None
        finally:
            user32.CloseClipboard()
        return None

    def capture_screen_bytes(self) -> Optional[bytes]:
        """Captures primary display to PNG bytes in memory (< 5ms)."""
        # Primary: PyQt6 in-memory buffer (reliable in all DPI / virtual sessions)
        try:
            from PyQt6.QtWidgets import QApplication
            from PyQt6.QtCore import QBuffer, QIODevice
            app = QApplication.instance()
            if app:
                screen = app.primaryScreen()
                if screen:
                    pix = screen.grabWindow(0)
                    buf = QBuffer()
                    buf.open(QIODevice.OpenModeFlag.WriteOnly)
                    pix.save(buf, "PNG")
                    return bytes(buf.data())
        except Exception:
            pass

        # Fallback: MSS GDI memory blit
        try:
            import mss
            import mss.tools
            with mss.mss() as sct:
                mon = sct.monitors[1]
                shot = sct.grab(mon)
                return mss.tools.to_png(shot.rgb, shot.size)
        except Exception:
            return None

    def get_context_snapshot(self) -> Dict[str, Any]:
        """Provides a complete perception snapshot for the cognitive agent."""
        fg = self.get_foreground_window()
        clip = self.get_clipboard_text()
        return {
            "window": fg,
            "clipboard": clip[:600] if clip else "",
            "is_code": bool(clip and any(k in clip for k in ["def ", "class ", "import ", "function ", "func ", "return ", "{", "};"])),
            "is_error": bool(clip and any(k in clip.lower() for k in ["traceback", "exception", "error", "failed", "nullpointer", "stack"]))
        }

PERCEPTION = PerceptionHarness()
