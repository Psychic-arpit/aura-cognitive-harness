"""
aura.harness.actuation - Hardware-Level OS Actuation Engine
Ultra-precise Win32 SendInput synthesis for keystrokes, mouse physics, and clipboard pasting.
"""

import time
import math
import ctypes
from ctypes import wintypes
from typing import Tuple, Optional, Callable

user32 = ctypes.WinDLL("user32", use_last_error=True)

# Win32 Input Constants
INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_ABSOLUTE = 0x8000

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG))
    ]

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG))
    ]

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD)
    ]

class _INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT)
    ]

class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("union", _INPUT_UNION)
    ]

LPINPUT = ctypes.POINTER(INPUT)
user32.SendInput.argtypes = [wintypes.UINT, LPINPUT, ctypes.c_int]
user32.SendInput.restype = wintypes.UINT

VK_MAP = {
    "enter": 0x0D, "return": 0x0D,
    "tab": 0x09, "esc": 0x1B, "escape": 0x1B,
    "space": 0x20, "backspace": 0x08, "delete": 0x2E, "del": 0x2E,
    "up": 0x26, "down": 0x28, "left": 0x25, "right": 0x27,
    "home": 0x24, "end": 0x23, "pageup": 0x21, "pagedown": 0x22,
    "ctrl": 0x11, "shift": 0x10, "alt": 0x12, "win": 0x5B,
    "volumemute": 0xAD, "volumedown": 0xAE, "volumeup": 0xAF,
    "f1": 0x70, "f2": 0x71, "f3": 0x72, "f4": 0x73, "f5": 0x74, "f6": 0x75,
    "f7": 0x76, "f8": 0x77, "f9": 0x78, "f10": 0x79, "f11": 0x7A, "f12": 0x7B
}

class ActuationHarness:
    def get_cursor_pos(self) -> Tuple[int, int]:
        pt = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        return pt.x, pt.y

    def set_cursor_pos(self, x: int, y: int):
        user32.SetCursorPos(int(x), int(y))

    def click(self, x: Optional[int] = None, y: Optional[int] = None, button: str = "left"):
        if x is not None and y is not None:
            self.set_cursor_pos(x, y)
            time.sleep(0.01)

        down_flag = MOUSEEVENTF_LEFTDOWN if button == "left" else MOUSEEVENTF_RIGHTDOWN
        up_flag = MOUSEEVENTF_LEFTUP if button == "left" else MOUSEEVENTF_RIGHTUP

        inp_down = INPUT(type=INPUT_MOUSE)
        inp_down.union.mi.dwFlags = down_flag
        inp_up = INPUT(type=INPUT_MOUSE)
        inp_up.union.mi.dwFlags = up_flag

        user32.SendInput(1, ctypes.byref(inp_down), ctypes.sizeof(INPUT))
        time.sleep(0.03)
        user32.SendInput(1, ctypes.byref(inp_up), ctypes.sizeof(INPUT))

    def double_click(self, x: Optional[int] = None, y: Optional[int] = None):
        self.click(x, y, button="left")
        time.sleep(0.05)
        self.click(x, y, button="left")

    def right_click(self, x: Optional[int] = None, y: Optional[int] = None):
        self.click(x, y, button="right")

    def mouse_down(self, button: str = "left"):
        flag = MOUSEEVENTF_LEFTDOWN if button == "left" else MOUSEEVENTF_RIGHTDOWN
        inp = INPUT(type=INPUT_MOUSE)
        inp.union.mi.dwFlags = flag
        user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

    def mouse_up(self, button: str = "left"):
        flag = MOUSEEVENTF_LEFTUP if button == "left" else MOUSEEVENTF_RIGHTUP
        inp = INPUT(type=INPUT_MOUSE)
        inp.union.mi.dwFlags = flag
        user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

    def drag_cursor(self, start: Tuple[int, int], target: Tuple[int, int], duration: float = 0.45, button: str = "left", telemetry_cb: Optional[Callable[[float, float], None]] = None):
        """Drags mouse with active button pressed from start to target coordinates along smooth Bezier arc."""
        self.set_cursor_pos(start[0], start[1])
        time.sleep(0.05)
        self.mouse_down(button)
        time.sleep(0.05)
        self.glide_cursor(start, target, duration=duration, telemetry_cb=telemetry_cb)
        time.sleep(0.05)
        self.mouse_up(button)
        time.sleep(0.05)

    def glide_cursor(self, start: Tuple[int, int], target: Tuple[int, int], duration: float = 0.35, telemetry_cb: Optional[Callable[[float, float], None]] = None):
        """Glides cursor along a smooth cubic Bezier arc with human-like acceleration."""
        steps = max(int(duration * 60), 12)
        sx, sy = start
        tx, ty = target
        dx = tx - sx
        dy = ty - sy

        # Control points with slight natural curve
        ctrl_x = sx + dx * 0.45 - dy * 0.1
        ctrl_y = sy + dy * 0.45 + dx * 0.1

        for i in range(steps + 1):
            t = i / float(steps)
            # Smooth ease-in-out curve
            ease_t = 3 * (t ** 2) - 2 * (t ** 3)
            # Quadratic Bezier
            cx = (1 - ease_t) ** 2 * sx + 2 * (1 - ease_t) * ease_t * ctrl_x + (ease_t ** 2) * tx
            cy = (1 - ease_t) ** 2 * sy + 2 * (1 - ease_t) * ease_t * ctrl_y + (ease_t ** 2) * ty

            self.set_cursor_pos(int(cx), int(cy))
            if telemetry_cb:
                telemetry_cb(cx, cy)
            time.sleep(duration / steps)

        self.set_cursor_pos(tx, ty)

    def fast_press(self, key_combination: str):
        """Synthesizes key press or modifier combinations (e.g. 'enter', 'ctrl+c', 'alt+f4')."""
        tokens = [k.strip().lower() for k in key_combination.split("+")]
        vk_codes = [VK_MAP.get(k, ord(k.upper()) if len(k) == 1 else 0) for k in tokens]

        # Key downs in order
        for vk in vk_codes:
            if vk:
                inp = INPUT(type=INPUT_KEYBOARD)
                inp.union.ki.wVk = vk
                user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
                time.sleep(0.01)

        time.sleep(0.02)

        # Key ups in reverse
        for vk in reversed(vk_codes):
            if vk:
                inp = INPUT(type=INPUT_KEYBOARD)
                inp.union.ki.wVk = vk
                inp.union.ki.dwFlags = KEYEVENTF_KEYUP
                user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
                time.sleep(0.01)

    def fast_type(self, text: str):
        """Fast Unicode typing via Win32 SendInput KEYEVENTF_UNICODE."""
        for char in text:
            code = ord(char)
            # Down
            inp_down = INPUT(type=INPUT_KEYBOARD)
            inp_down.union.ki.wScan = code
            inp_down.union.ki.dwFlags = KEYEVENTF_UNICODE
            # Up
            inp_up = INPUT(type=INPUT_KEYBOARD)
            inp_up.union.ki.wScan = code
            inp_up.union.ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP

            inputs = (INPUT * 2)(inp_down, inp_up)
            user32.SendInput(2, inputs, ctypes.sizeof(INPUT))
            time.sleep(0.005)

    def scroll(self, clicks: int):
        inp = INPUT(type=INPUT_MOUSE)
        inp.union.mi.dwFlags = MOUSEEVENTF_WHEEL
        inp.union.mi.mouseData = clicks * 120
        user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

    def get_screen_size(self) -> Tuple[int, int]:
        return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)

    def move_resize_window(self, hwnd: int, x: int, y: int, w: int, h: int):
        """Moves and resizes a Win32 HWND safely."""
        try:
            if user32.IsWindow(hwnd):
                SWP_NOZORDER = 0x0004
                SWP_SHOWWINDOW = 0x0040
                user32.SetWindowPos(hwnd, 0, int(x), int(y), int(w), int(h), SWP_NOZORDER | SWP_SHOWWINDOW)
        except Exception:
            pass

    def tile_window(self, hwnd: int, side: str):
        """Tiles window to left half, right half, or maximized."""
        sw, sh = self.get_screen_size()
        # Leave 40px for bottom taskbar
        usable_h = max(sh - 48, 600)
        if side == "left":
            self.move_resize_window(hwnd, 0, 0, sw // 2, usable_h)
        elif side == "right":
            self.move_resize_window(hwnd, sw // 2, 0, sw // 2, usable_h)
        elif side == "maximize":
            user32.ShowWindow(hwnd, 3)  # SW_MAXIMIZE
        elif side == "restore":
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE

ACTUATION = ActuationHarness()
