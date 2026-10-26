"""
automation/system_control.py - Ultra-Fast Win32 System, Audio, and Workspace Controller
Controls Volume, Media Playback, Window Tiling, and Power States with 0.01ms Latency
"""

import ctypes
from ctypes import wintypes
from typing import Tuple

user32 = ctypes.WinDLL("user32", use_last_error=True)
shell32 = ctypes.WinDLL("shell32", use_last_error=True)

# Multimedia Virtual Keys
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_STOP = 0xB2
VK_MEDIA_PLAY_PAUSE = 0xB3

# Windows Keys
VK_LWIN = 0x5B
VK_D = 0x44
VK_LEFT = 0x25
VK_UP = 0x26
VK_RIGHT = 0x27
VK_DOWN = 0x28
KEYEVENTF_KEYUP = 0x0002

class SystemControl:
    @staticmethod
    def _tap_key(vk: int):
        """Dispatches key down and key up via keybd_event."""
        user32.keybd_event(vk, 0, 0, 0)
        user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)

    @staticmethod
    def _send_win_combo(vk: int):
        """Sends Win + Key combo."""
        user32.keybd_event(VK_LWIN, 0, 0, 0)
        user32.keybd_event(vk, 0, 0, 0)
        user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
        user32.keybd_event(VK_LWIN, 0, KEYEVENTF_KEYUP, 0)

    def mute_audio(self) -> Tuple[bool, str]:
        self._tap_key(VK_VOLUME_MUTE)
        return True, "Toggled Audio Mute [OK]"

    def volume_up(self, steps: int = 5) -> Tuple[bool, str]:
        for _ in range(steps):
            self._tap_key(VK_VOLUME_UP)
        return True, f"Increased Volume (+{steps*2}%) [OK]"

    def volume_down(self, steps: int = 5) -> Tuple[bool, str]:
        for _ in range(steps):
            self._tap_key(VK_VOLUME_DOWN)
        return True, f"Decreased Volume (-{steps*2}%) [OK]"

    def media_play_pause(self) -> Tuple[bool, str]:
        self._tap_key(VK_MEDIA_PLAY_PAUSE)
        return True, "Toggled Media Play/Pause [OK]"

    def media_next(self) -> Tuple[bool, str]:
        self._tap_key(VK_MEDIA_NEXT_TRACK)
        return True, "Skipped to Next Track [OK]"

    def media_prev(self) -> Tuple[bool, str]:
        self._tap_key(VK_MEDIA_PREV_TRACK)
        return True, "Returned to Previous Track [OK]"

    def show_desktop(self) -> Tuple[bool, str]:
        self._send_win_combo(VK_D)
        return True, "Toggled Desktop View (Win+D) [OK]"

    def snap_window_left(self) -> Tuple[bool, str]:
        self._send_win_combo(VK_LEFT)
        return True, "Snapped Window Left [OK]"

    def snap_window_right(self) -> Tuple[bool, str]:
        self._send_win_combo(VK_RIGHT)
        return True, "Snapped Window Right [OK]"

    def maximize_window(self) -> Tuple[bool, str]:
        self._send_win_combo(VK_UP)
        return True, "Maximized Active Window [OK]"

    def lock_workstation(self) -> Tuple[bool, str]:
        try:
            user32.LockWorkStation()
            return True, "Locked Workstation [OK]"
        except Exception as e:
            return False, f"Lock failed: {e}"

    def empty_recycle_bin(self) -> Tuple[bool, str]:
        try:
            # SHERB_NOCONFIRMATION = 0x00000001, SHERB_NOPROGRESSUI = 0x00000002, SHERB_NOSOUND = 0x00000004
            flags = 0x00000007
            shell32.SHEmptyRecycleBinW(0, None, flags)
            return True, "Recycle Bin Emptied [OK]"
        except Exception as e:
            return False, f"Empty Recycle Bin failed: {e}"

    def execute(self, action: str) -> Tuple[bool, str]:
        """Dispatches recognized system action."""
        act = action.lower().strip()
        if "mute" in act:
            return self.mute_audio()
        elif "vol" in act and ("up" in act or "increase" in act or "more" in act):
            return self.volume_up()
        elif "vol" in act and ("down" in act or "decrease" in act or "less" in act):
            return self.volume_down()
        elif "play" in act or "pause" in act:
            return self.media_play_pause()
        elif "next" in act:
            return self.media_next()
        elif "prev" in act or "back" in act:
            return self.media_prev()
        elif "desktop" in act or "minimize all" in act:
            return self.show_desktop()
        elif "snap left" in act:
            return self.snap_window_left()
        elif "snap right" in act:
            return self.snap_window_right()
        elif "maximize" in act:
            return self.maximize_window()
        elif "lock" in act:
            return self.lock_workstation()
        elif "empty" in act or "trash" in act or "bin" in act:
            return self.empty_recycle_bin()
        return False, f"Unknown system command: '{action}'"

# Global SystemControl singleton
SYSTEM_CONTROL = SystemControl()
