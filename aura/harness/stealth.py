"""
aura.harness.stealth - Stream Stealth, Hotkey Sentinel & System Tray Harness
Enforces WDA_EXCLUDEFROMCAPTURE (0x11) to eliminate capture by OBS, Discord, and Zoom.
Registers non-conflicting OS hotkeys without low-level hook keylogger flags.
"""

import ctypes
from ctypes import wintypes
import threading
from typing import Callable, Optional, Dict, Tuple

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

# OS Display Affinity (Screen recording invisibility)
WDA_NONE = 0x00000000
WDA_MONITOR = 0x00000001
WDA_EXCLUDEFROMCAPTURE = 0x00000011

# RegisterHotKey Modifiers
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000
WM_HOTKEY = 0x0312
WM_QUIT = 0x0012

class StealthHarness:
    def __init__(self):
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._thread_id: Optional[int] = None
        self._hotkeys: Dict[int, Tuple[int, int, Callable[[], None]]] = {}
        self._next_id = 200

    def apply_stream_invisibility(self, hwnd: int) -> bool:
        """Excludes window from all OS display captures (OBS, Discord, Zoom, Screenshot tools)."""
        if not hwnd:
            return False
        try:
            if hasattr(user32, "SetWindowDisplayAffinity"):
                res = user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)
                return bool(res)
        except Exception:
            pass
        return False

    def register_hotkey(self, modifiers: int, vk_code: int, callback: Callable[[], None]) -> int:
        hk_id = self._next_id
        self._next_id += 1
        self._hotkeys[hk_id] = (modifiers, vk_code, callback)
        return hk_id

    def start_hotkey_sentinel(self):
        if self._running:
            return
        self._running = True
        self._ready_event = threading.Event()
        self._thread = threading.Thread(target=self._pump_loop, name="AuraHotkeySentinel", daemon=True)
        self._thread.start()
        self._ready_event.wait(timeout=1.0)

    def stop_hotkey_sentinel(self):
        self._running = False
        if self._thread_id:
            user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)

    def _pump_loop(self):
        self._thread_id = kernel32.GetCurrentThreadId()
        msg = wintypes.MSG()

        # Register hotkeys on thread
        for hk_id, (mods, vk, cb) in self._hotkeys.items():
            user32.RegisterHotKey(None, hk_id, mods | MOD_NOREPEAT, vk)

        self._ready_event.set()

        while self._running:
            b_ret = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if b_ret in (0, -1):
                break
            if msg.message == WM_HOTKEY:
                hk_id = msg.wParam
                entry = self._hotkeys.get(hk_id)
                if entry:
                    _, _, handler = entry
                    handler()
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        for hk_id in self._hotkeys.keys():
            user32.UnregisterHotKey(None, hk_id)

STEALTH = StealthHarness()
