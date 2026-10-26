"""
aura.harness.glass - Windows DWM Aero & Acrylic Glassmorphic Blur-Behind Engine
Enables hardware-accelerated desktop compositing blur (Acrylic / Aero BlurBehind) via DWM APIs.
"""

import ctypes
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)
dwmapi = ctypes.WinDLL("dwmapi", use_last_error=True)

class ACCENT_POLICY(ctypes.Structure):
    _fields_ = [
        ("AccentState", ctypes.c_int),
        ("AccentFlags", ctypes.c_int),
        ("GradientColor", ctypes.c_int),
        ("AnimationId", ctypes.c_int)
    ]

class WINCOMPATTRDATA(ctypes.Structure):
    _fields_ = [
        ("Attribute", ctypes.c_int),
        ("Data", ctypes.c_void_p),
        ("SizeOfData", ctypes.c_size_t)
    ]

# DWM Attribute constants
DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_SYSTEMBACKDROP_TYPE = 38
DWMWA_WINDOW_CORNER_PREFERENCE = 33

# Backdrop types (Windows 11 build 22000+)
BACKDROP_AUTO = 1
BACKDROP_MICA = 2
BACKDROP_ACRYLIC = 3
BACKDROP_MICA_ALT = 4

class GlassHarness:
    def enable_aero_glass(self, hwnd: int, tint_rgba: tuple = (10, 14, 24, 200)) -> bool:
        """Applies hardware DWM Acrylic / Aero blur-behind to the window."""
        if not hwnd:
            return False

        success = False

        # 1. Windows 11 DwmSetWindowAttribute (Acrylic Backdrop + Dark Mode)
        try:
            dark_mode = ctypes.c_int(1)
            dwmapi.DwmSetWindowAttribute(
                hwnd,
                DWMWA_USE_IMMERSIVE_DARK_MODE,
                ctypes.byref(dark_mode),
                ctypes.sizeof(dark_mode)
            )

            backdrop = ctypes.c_int(BACKDROP_ACRYLIC)
            res = dwmapi.DwmSetWindowAttribute(
                hwnd,
                DWMWA_SYSTEMBACKDROP_TYPE,
                ctypes.byref(backdrop),
                ctypes.sizeof(backdrop)
            )
            if res == 0:
                success = True
        except Exception:
            pass

        # 2. Windows 10/11 SetWindowCompositionAttribute Acrylic / BlurBehind
        try:
            r, g, b, a = tint_rgba
            # Color format: AABBGGRR
            gradient_color = (a << 24) | (b << 16) | (g << 8) | r

            accent = ACCENT_POLICY()
            accent.AccentState = 4  # ACCENT_ENABLE_ACRYLICBLURBEHIND
            accent.AccentFlags = 2
            accent.GradientColor = gradient_color

            data = WINCOMPATTRDATA()
            data.Attribute = 19  # WCA_ACCENT_POLICY
            data.Data = ctypes.cast(ctypes.byref(accent), ctypes.c_void_p)
            data.SizeOfData = ctypes.sizeof(accent)

            if hasattr(user32, "SetWindowCompositionAttribute"):
                res_accent = user32.SetWindowCompositionAttribute(hwnd, ctypes.byref(data))
                if res_accent:
                    success = True
        except Exception:
            pass

        return success

GLASS = GlassHarness()
