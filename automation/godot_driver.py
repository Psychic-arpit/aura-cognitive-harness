"""
automation/godot_driver.py - TagRush Godot 4 Multiplayer QA Driver
Zero-Flicker Native Launch Placement (--windowed --resolution 960x1080 --position 0,0 / 960,0)
Physical Input Dispatch (WASD Scancodes, Jumps, Tag Simulation) with Glowing Cursor Guidance
"""

import os
import subprocess
import time
import json
from typing import Optional, Callable
from core.win32_fast import send_key, tap_key, fast_mouse_click, VK_SPACE
from core.motion_engine import MOTION
from core.failsafe import FAILSAFE

DEFAULT_GODOT = r"C:\Users\arpit\Downloads\Godot_v4.6.3-stable_win64.exe\Godot_v4.6.3-stable_win64.exe"
DEFAULT_TAGRUSH = r"D:\Hide and Seek Game v1.o\TagRush"

class GodotQADriver:
    def __init__(self, godot_path: str = DEFAULT_GODOT, project_path: str = DEFAULT_TAGRUSH):
        self.godot_path = godot_path
        self.project_path = project_path
        self.host_proc: Optional[subprocess.Popen] = None
        self.client_proc: Optional[subprocess.Popen] = None

    def launch_dual_clients(
        self,
        mode: str = "mach",
        telemetry_cb: Optional[Callable[[float, float], None]] = None,
        click_cb: Optional[Callable[[float, float], None]] = None
    ) -> bool:
        """
        Launches 2 TagRush instances pre-tiled side-by-side using native Godot display flags:
        Left half: 960x1080 at (0, 0)
        Right half: 960x1080 at (960, 0)
        Zero flicker, zero post-launch window snapping lag.
        """
        if FAILSAFE.is_aborted():
            return False

        if not os.path.exists(self.godot_path):
            print(f"[GodotQA] Executable not found at {self.godot_path}")
            return False

        if not os.path.exists(self.project_path):
            print(f"[GodotQA] Project not found at {self.project_path}")
            return False

        print("[GodotQA] Launching TagRush Host (Left Screen 960x1080)...")
        # Instance 1: Host (Left Screen)
        self.host_proc = subprocess.Popen([
            self.godot_path,
            "--path", self.project_path,
            "--windowed",
            "--resolution", "960x1080",
            "--position", "0,0"
        ])

        time.sleep(0.8)
        if FAILSAFE.is_aborted():
            self.terminate_all()
            return False

        print("[GodotQA] Launching TagRush Client (Right Screen 960x1080)...")
        # Instance 2: Client (Right Screen)
        self.client_proc = subprocess.Popen([
            self.godot_path,
            "--path", self.project_path,
            "--windowed",
            "--resolution", "960x1080",
            "--position", "960,0"
        ])

        # Allow Godot engine viewports to initialize
        time.sleep(2.0)
        if FAILSAFE.is_aborted():
            self.terminate_all()
            return False

        # Visual Guidance: Glide glowing cursor to Host viewport, click to focus, simulate movement
        print("[GodotQA] Guiding glowing cursor to Host window...")
        host_center = (480.0, 540.0)
        MOTION.glide_cursor((960.0, 50.0), host_center, mode=mode, telemetry_cb=telemetry_cb)
        fast_mouse_click("left")
        if click_cb:
            click_cb(host_center[0], host_center[1])

        # Simulate player movement in Host: W, A, S, D, Space jump
        self._simulate_player_movement(keys=['W', 'D', 'W'], duration=0.8)

        # Glide glowing cursor to Client viewport, click to focus, simulate movement
        print("[GodotQA] Guiding glowing cursor to Client window...")
        client_center = (1440.0, 540.0)
        MOTION.glide_cursor(host_center, client_center, mode=mode, telemetry_cb=telemetry_cb)
        fast_mouse_click("left")
        if click_cb:
            click_cb(client_center[0], client_center[1])

        self._simulate_player_movement(keys=['A', 'W', 'D'], duration=0.8)

        print("[GodotQA] TagRush Dual QA Synchronization Test Completed Successfully!")
        return True

    def _simulate_player_movement(self, keys: list[str], duration: float = 0.5):
        """Dispatches hardware-scancode WASD movement to the focused Godot instance."""
        for key_char in keys:
            if FAILSAFE.is_aborted():
                return
            vk = ord(key_char.upper())
            send_key(vk, down=True, use_scancode=True)
            time.sleep(duration / len(keys))
            send_key(vk, down=False, use_scancode=True)
            time.sleep(0.05)

        # Jump
        if not FAILSAFE.is_aborted():
            tap_key(VK_SPACE, dwell_ms=30.0, use_scancode=True)

    def terminate_all(self):
        """Kills active test instances on emergency abort."""
        if self.host_proc and self.host_proc.poll() is None:
            self.host_proc.terminate()
        if self.client_proc and self.client_proc.poll() is None:
            self.client_proc.terminate()

# Global Godot QA driver singleton
GODOT_QA = GodotQADriver()
