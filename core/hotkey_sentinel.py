"""
core/hotkey_sentinel.py - OS-Sanctioned Win32 RegisterHotKey Monitor
Zero Antivirus Heuristic Flags (Replaces WH_KEYBOARD_LL with RegisterHotKey)
Handles Global Capsule Summoning (Ctrl+Space / Alt+Space) without IDE Conflicts
"""

import ctypes
from ctypes import wintypes
import threading
from typing import Callable, Optional

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

# Modifier keys for RegisterHotKey
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

VK_SPACE = 0x20
WM_HOTKEY = 0x0312
WM_QUIT = 0x0012

class HotkeySentinel:
    """
    Spawns an invisible message pump thread listening exclusively for WM_HOTKEY.
    Does not install global hooks and cannot be flagged as keylogger.
    """
    def __init__(self):
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._thread_id: Optional[int] = None
        self._hotkeys: dict[int, tuple[int, int, Callable[[], None]]] = {}
        self._next_id = 100

    def register_hotkey(self, modifiers: int, vk_code: int, callback: Callable[[], None]) -> int:
        """Registers a global hotkey combination."""
        hk_id = self._next_id
        self._next_id += 1
        self._hotkeys[hk_id] = (modifiers, vk_code, callback)
        return hk_id

    def start(self):
        """Starts the background message pump for registered hotkeys."""
        if self._running:
            return
        self._running = True
        self._ready_event = threading.Event()
        self._thread = threading.Thread(target=self._message_pump, name="AuraHotkeyPump", daemon=True)
        self._thread.start()
        self._ready_event.wait(timeout=1.0)

    def stop(self):
        """Unregisters hotkeys and terminates message pump."""
        self._running = False
        if self._thread_id:
            user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)

    def _message_pump(self):
        self._thread_id = kernel32.GetCurrentThreadId()
        msg = wintypes.MSG()
        
        # Register all hotkeys on current thread
        for hk_id, (mods, vk, cb) in self._hotkeys.items():
            user32.RegisterHotKey(None, hk_id, mods | MOD_NOREPEAT, vk)

        self._ready_event.set()

        while self._running:
            b_ret = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if b_ret == 0 or b_ret == -1:
                break
            if msg.message == WM_HOTKEY:
                hk_id = msg.wParam
                handler_tuple = self._hotkeys.get(hk_id)
                if handler_tuple:
                    _, _, handler = handler_tuple
                    handler()
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        # Cleanup
        for hk_id in self._hotkeys.keys():
            user32.UnregisterHotKey(None, hk_id)

# Global hotkey sentinel singleton
HOTKEYS = HotkeySentinel()
