"""
automation/youtube_driver.py - YouTube Desktop Autopilot
Autonomous Navigation, Shorts Targeting, Kinetic Vector Movement, and Physical Mouse Clicks
Delivers Pixel-Perfect Visual Feedback with Glowing Cyber Cursor Guidance
"""

import os
import time
import urllib.parse
import ctypes
from ctypes import wintypes
from typing import Optional, Callable
import webbrowser

from core.win32_fast import (
    get_cursor_pos, fast_mouse_click, tap_key, force_focus_window,
    VK_SPACE, VK_DOWN
)
from core.motion_engine import MOTION
from core.failsafe import FAILSAFE
from automation.browser_cdp import CDP

user32 = ctypes.WinDLL("user32", use_last_error=True)

class YouTubeDriver:
    def __init__(self):
        pass

    def _find_browser_hwnd(self) -> Optional[int]:
        """Finds active browser window (Chrome, Edge, Firefox, Brave)."""
        target_hwnd = None

        def enum_windows_callback(hwnd, extra):
            nonlocal target_hwnd
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    title = buff.value.lower()
                    if any(b in title for b in ["youtube", "chrome", "edge", "firefox", "brave", "opera"]):
                        rect = wintypes.RECT()
                        user32.GetWindowRect(hwnd, ctypes.byref(rect))
                        w = rect.right - rect.left
                        h = rect.bottom - rect.top
                        if w > 400 and h > 400:
                            target_hwnd = hwnd
                            return False
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        user32.EnumWindows(WNDENUMPROC(enum_windows_callback), 0)
        return target_hwnd

    def focus_browser(self):
        """Brings the active browser window into the foreground."""
        hwnd = self._find_browser_hwnd()
        if hwnd:
            force_focus_window(hwnd)

    def play_shorts(
        self,
        mode: str = "mach",
        telemetry_cb: Optional[Callable[[float, float], None]] = None,
        click_cb: Optional[Callable[[float, float], None]] = None
    ) -> bool:
        """
        1. Navigates to YouTube Shorts in the browser.
        2. Focuses the browser window.
        3. Glides the glowing cursor across the screen to the Shorts navigation icon and video.
        4. Physically clicks on the Shorts video by mouse with expanding sonar ripples.
        5. Begins playback!
        """
        if FAILSAFE.is_aborted():
            return False

        print("[YouTubeDriver] Launching YouTube Shorts...")
        shorts_url = "https://www.youtube.com/shorts"
        try:
            os.startfile(shorts_url)
        except Exception:
            webbrowser.open(shorts_url)

        # Allow browser window to open and render content
        for _ in range(16):
            if FAILSAFE.is_aborted():
                return False
            time.sleep(0.1)

        self.focus_browser()
        time.sleep(0.3)

        if FAILSAFE.is_aborted():
            return False

        # Get active display dimensions
        sw = user32.GetSystemMetrics(0)
        sh = user32.GetSystemMetrics(1)
        cur_x, cur_y = get_cursor_pos()

        # Step 1: Smoothly glide cursor to Shorts navigation indicator
        sidebar_x = int(sw * 0.08)
        sidebar_y = int(sh * 0.22)
        print(f"[YouTubeDriver] Gliding cursor to Shorts tab ({sidebar_x}, {sidebar_y})...")
        ok = MOTION.glide_cursor(
            (cur_x, cur_y),
            (sidebar_x, sidebar_y),
            mode=mode,
            telemetry_cb=telemetry_cb
        )
        if not ok or FAILSAFE.is_aborted():
            return False

        if click_cb:
            click_cb(sidebar_x, sidebar_y)
        time.sleep(0.2)

        # Step 2: Query CDP for exact DOM bounding box or fallback to layout math
        cdp_coords = CDP.find_youtube_shorts_coords()
        if cdp_coords:
            video_x, video_y = cdp_coords
            print(f"[YouTubeDriver] CDP DOM element locked at exact coordinates: ({video_x}, {video_y})")
        else:
            video_x = sw // 2
            video_y = int(sh * 0.48)
            print(f"[YouTubeDriver] Targeting Shorts Video Player via layout heuristics ({video_x}, {video_y})...")

        ok = MOTION.glide_cursor(
            (sidebar_x, sidebar_y),
            (video_x, video_y),
            mode=mode,
            telemetry_cb=telemetry_cb
        )
        if not ok or FAILSAFE.is_aborted():
            return False

        # Step 3: Trigger glowing click ripple and physically click by mouse!
        if click_cb:
            click_cb(video_x, video_y)
        fast_mouse_click("left")
        print("[YouTubeDriver] Clicked Shorts Video! Playback started.")

        # Ensure audio/video plays smoothly
        time.sleep(0.3)
        if not FAILSAFE.is_aborted():
            # Tap space / k to ensure playback toggle if initially paused
            tap_key(VK_SPACE)

        return True

    def search_and_play(
        self,
        query: str,
        mode: str = "mach",
        telemetry_cb: Optional[Callable[[float, float], None]] = None,
        click_cb: Optional[Callable[[float, float], None]] = None
    ) -> bool:
        """
        1. Navigates to YouTube search results for query.
        2. Glides the glowing cursor to the first video thumbnail.
        3. Physically clicks the video to play.
        """
        if FAILSAFE.is_aborted():
            return False

        print(f"[YouTubeDriver] Searching YouTube for '{query}'...")
        search_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
        try:
            os.startfile(search_url)
        except Exception:
            webbrowser.open(search_url)

        for _ in range(18):
            if FAILSAFE.is_aborted():
                return False
            time.sleep(0.1)

        self.focus_browser()
        time.sleep(0.3)

        if FAILSAFE.is_aborted():
            return False

        sw = user32.GetSystemMetrics(0)
        sh = user32.GetSystemMetrics(1)
        cur_x, cur_y = get_cursor_pos()

        # Target first video title / thumbnail via CDP or layout heuristics
        cdp_coords = CDP.find_youtube_first_video_coords()
        if cdp_coords:
            target_x, target_y = cdp_coords
            print(f"[YouTubeDriver] CDP DOM video element locked at: ({target_x}, {target_y})")
        else:
            target_x = int(sw * 0.32)
            target_y = int(sh * 0.30)
            print(f"[YouTubeDriver] Gliding cursor to top video result ({target_x}, {target_y})...")
        ok = MOTION.glide_cursor(
            (cur_x, cur_y),
            (target_x, target_y),
            mode=mode,
            telemetry_cb=telemetry_cb
        )
        if not ok or FAILSAFE.is_aborted():
            return False

        if click_cb:
            click_cb(target_x, target_y)
        fast_mouse_click("left")
        print(f"[YouTubeDriver] Clicked video '{query}'! Playback initiated.")
        return True

    def next_short(self) -> bool:
        """Scrolls to next Short via down arrow."""
        self.focus_browser()
        tap_key(VK_DOWN)
        return True

# Global YouTube driver singleton
YOUTUBE = YouTubeDriver()
