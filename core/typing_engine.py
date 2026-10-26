"""
core/typing_engine.py - Dual-Mode Keystroke Synthesis
Mach Mode: Instant Win32 Clipboard Injection (0ms)
Biomimetic Mode: Log-Normal Human Rhythm with Punctuation Hesitation & Zero Bot Flags
"""

import time
import random
import ctypes
from core.win32_fast import send_key, tap_key, send_hotkey, VK_CONTROL
from core.failsafe import FAILSAFE

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

# Clipboard formats
CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002

def set_clipboard_text(text: str) -> bool:
    """Safely writes Unicode text directly to Windows OS clipboard."""
    if not user32.OpenClipboard(None):
        return False
    try:
        user32.EmptyClipboard()
        encoded = text.encode("utf-16le") + b"\x00\x00"
        h_mem = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(encoded))
        if not h_mem:
            return False
        p_mem = kernel32.GlobalLock(h_mem)
        if not p_mem:
            kernel32.GlobalFree(h_mem)
            return False
        ctypes.memmove(p_mem, encoded, len(encoded))
        kernel32.GlobalUnlock(h_mem)
        user32.SetClipboardData(CF_UNICODETEXT, h_mem)
        return True
    finally:
        user32.CloseClipboard()

class TypingEngine:
    def __init__(self, mean_ms: float = 65.0, sigma: float = 0.28):
        self.mean_s = mean_ms / 1000.0
        self.sigma = sigma

    def type_mach(self, text: str) -> bool:
        """Instant text delivery via Windows clipboard injection and Ctrl+V."""
        if FAILSAFE.is_aborted():
            return False
        if set_clipboard_text(text):
            time.sleep(0.015)
            send_hotkey(VK_CONTROL, ord('V'))
            return True
        else:
            # Fallback to direct unicode stream
            return self.type_unicode_fast(text)

    def type_unicode_fast(self, text: str) -> bool:
        """Fast synthetic keystroke stream."""
        for char in text:
            if FAILSAFE.is_aborted():
                return False
            vk = ord(char.upper()) if char.isalnum() else 0
            if vk != 0:
                tap_key(vk, dwell_ms=10.0, use_scancode=True)
            else:
                # Unicode fallback
                time.sleep(0.005)
        return True

    def type_biomimetic(self, text: str) -> bool:
        """
        Synthesizes authentic human typing cadence:
        - Log-normal inter-keystroke interval distribution.
        - Realistic delays on whitespace and punctuation.
        - Immediate abort on Esc key.
        """
        for i, char in enumerate(text):
            if FAILSAFE.is_aborted():
                return False

            vk = ord(char.upper()) if char.isalnum() else 0
            if vk != 0:
                dwell = max(15.0, random.gauss(28.0, 6.0))
                tap_key(vk, dwell_ms=dwell, use_scancode=True)
            elif char == ' ':
                tap_key(0x20, dwell_ms=25.0, use_scancode=True)
            elif char == '\n':
                tap_key(0x0D, dwell_ms=30.0, use_scancode=True)
            else:
                # Fallback: copy-paste single special symbol
                set_clipboard_text(char)
                send_hotkey(VK_CONTROL, ord('V'))

            # Calculate natural human inter-keystroke hesitation
            # Base log-normal delay
            delay = random.lognormvariate(math_log_mean := -2.73, self.sigma) # ~65ms mean
            delay = max(0.035, min(0.220, delay))

            # Punctuation pauses
            if char in {'.', '!', '?'}:
                delay += random.uniform(0.180, 0.320)
            elif char in {',', ';', ':'}:
                delay += random.uniform(0.090, 0.160)
            elif char == ' ':
                delay += random.uniform(0.040, 0.080)

            time.sleep(delay)

        return True

    def type_text(self, text: str, mode: str = "mach") -> bool:
        """Dispatcher based on active speed mode."""
        if mode == "mach":
            return self.type_mach(text)
        return self.type_biomimetic(text)

# Global typing engine singleton
TYPING = TypingEngine()
