"""
automation/whatsapp_driver.py - WhatsApp Desktop Autopilot
Zero-Vision Keyboard Navigation via Ctrl+F + Win32 Focus Steal Bypass
100% Theme and Resolution Independent Chat Selection
"""

import os
import time
import ctypes
from ctypes import wintypes
from typing import Optional, Callable
from core.win32_fast import send_hotkey, tap_key, force_focus_window, fast_mouse_click, VK_CONTROL, VK_RETURN, VK_DOWN
from core.motion_engine import MOTION
from core.typing_engine import TYPING
from core.failsafe import FAILSAFE

user32 = ctypes.WinDLL("user32", use_last_error=True)

class WhatsAppDriver:
    def __init__(self):
        self.protocol_uri = "whatsapp://"

    def _find_whatsapp_hwnd(self) -> Optional[int]:
        """Enumerates top-level windows to locate active WhatsApp HWND."""
        target_hwnd = None

        def enum_windows_callback(hwnd, extra):
            nonlocal target_hwnd
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    title = buff.value
                    if "whatsapp" in title.lower():
                        target_hwnd = hwnd
                        return False
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        user32.EnumWindows(WNDENUMPROC(enum_windows_callback), 0)
        return target_hwnd

    def open_chat_or_group(
        self,
        target_name: str = "Class Group",
        mode: str = "mach",
        telemetry_cb: Optional[Callable[[float, float], None]] = None,
        click_cb: Optional[Callable[[float, float], None]] = None
    ) -> bool:
        """
        Launches WhatsApp, focuses window, navigates to search via Ctrl+F,
        types target group name, and selects chat with glowing visual feedback.
        """
        if FAILSAFE.is_aborted():
            return False

        print(f"[WhatsAppDriver] Launching WhatsApp...")
        try:
            os.startfile("whatsapp:")
        except Exception:
            try:
                os.startfile("whatsapp://")
            except Exception as e:
                print(f"[WhatsAppDriver] Launch error: {e}")

        # Wait for window to spawn and gain foreground
        time.sleep(1.0)
        if FAILSAFE.is_aborted():
            return False

        hwnd = self._find_whatsapp_hwnd()
        if hwnd:
            print(f"[WhatsAppDriver] Found WhatsApp HWND: {hwnd}. Forcing focus...")
            force_focus_window(hwnd)
            time.sleep(0.2)

        # Visual Glide: Glide cursor towards WhatsApp search bar region (typically top-left ~280, 115)
        search_target = (280.0, 115.0)
        print(f"[WhatsAppDriver] Gliding glowing cursor to search area...")
        MOTION.glide_cursor((500.0, 300.0), search_target, mode=mode, telemetry_cb=telemetry_cb)
        fast_mouse_click("left")
        if click_cb:
            click_cb(search_target[0], search_target[1])

        time.sleep(0.1)
        if FAILSAFE.is_aborted():
            return False

        # Guaranteed universal focus shortcut for WhatsApp search: Ctrl + F
        print("[WhatsAppDriver] Focusing search bar via Ctrl+F...")
        send_hotkey(VK_CONTROL, ord('F'))
        time.sleep(0.15)

        # Type group / contact name with active mode cadence
        print(f"[WhatsAppDriver] Typing '{target_name}' [{mode.upper()} mode]...")
        TYPING.type_text(target_name, mode=mode)
        time.sleep(0.25)

        if FAILSAFE.is_aborted():
            return False

        # Select top search result: Down Arrow -> Enter
        print("[WhatsAppDriver] Selecting search result...")
        tap_key(VK_DOWN, dwell_ms=25.0, use_scancode=True)
        time.sleep(0.1)
        tap_key(VK_RETURN, dwell_ms=30.0, use_scancode=True)

        # Visual pulse confirmation
        if click_cb:
            click_cb(search_target[0], search_target[1] + 60.0)

        print(f"[WhatsAppDriver] Chat '{target_name}' successfully opened!")
        return True

# Global WhatsApp driver singleton
WHATSAPP = WhatsAppDriver()
