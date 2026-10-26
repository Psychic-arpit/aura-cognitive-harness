"""
core/failsafe.py - Esc Panic Kill-Switch & Physical Mouse Override Sentinel
Zero Antivirus Heuristic Flags (Replaces WH_KEYBOARD_LL with GetAsyncKeyState polling)
Atomic Thread Abort + Immediate Hardware Key/Mouse Release
"""

import ctypes
from ctypes import wintypes
import threading
import time
import math
from typing import Callable, Optional
from core.win32_fast import emergency_hardware_flush

user32 = ctypes.WinDLL("user32", use_last_error=True)
VK_ESCAPE = 0x1B

class FailsafeSentinel:
    """
    High-frequency (100Hz) background watchdog that monitors:
    1. Dedicated 'Esc' key tap -> Instant hard abort + hardware key release.
    2. Physical human mouse override -> If user physically moves mouse > 40px while AI moves, yields.
    """
    def __init__(self, check_interval_ms: float = 10.0):
        self.check_interval_s = check_interval_ms / 1000.0
        self._abort_event = threading.Event()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._callbacks: list[Callable[[], None]] = []

        # Automation task tracking
        self.is_active = False
        self.ai_controlling = False
        self.last_ai_pos = (0.0, 0.0)
        self.override_threshold_px = 45.0

    def start(self):
        """Spawns the failsafe watchdog thread."""
        if self._running:
            return
        self._running = True
        self._abort_event.clear()
        self._thread = threading.Thread(target=self._watchdog_loop, name="AuraFailsafeWatchdog", daemon=True)
        self._thread.start()

    def stop(self):
        """Stops the failsafe watchdog thread."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.2)

    def activate(self):
        """Arms the failsafe for an active automation routine."""
        self._abort_event.clear()
        self.is_active = True

    def deactivate(self):
        """Disarms the failsafe when routine finishes or yields."""
        self.is_active = False
        self.ai_controlling = False

    def register_abort_callback(self, callback: Callable[[], None]):
        """Registers a callback function to execute immediately on Esc panic."""
        self._callbacks.append(callback)

    def is_aborted(self) -> bool:
        """Returns True if Esc panic was triggered."""
        return self._abort_event.is_set()

    def reset(self):
        """Clears the abort flag for subsequent tasks."""
        self._abort_event.clear()
        self.is_active = True

    def trigger_abort(self):
        """Programmatically triggers the emergency abort."""
        if self.is_active and not self._abort_event.is_set():
            self._abort_event.set()
            self.is_active = False
            self.ai_controlling = False
            # 1. Immediately release all mouse buttons and keys at hardware level
            emergency_hardware_flush()
            # 2. Fire all registered abort listeners
            for cb in self._callbacks:
                try:
                    cb()
                except Exception as e:
                    print(f"[AuraFailsafe] Callback error: {e}")

    def notify_ai_pos(self, x: float, y: float):
        """Informs the sentinel of where the AI expects the cursor to be."""
        self.last_ai_pos = (x, y)
        self.ai_controlling = True

    def notify_ai_finished(self):
        """Informs the sentinel that the AI has yielded cursor control."""
        self.ai_controlling = False

    def _get_cursor_pos(self) -> tuple[int, int]:
        pt = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        return pt.x, pt.y

    def _watchdog_loop(self):
        """Continuous low-overhead 100Hz polling loop. Only intercepts when task is active."""
        while self._running:
            if self.is_active:
                # Check Esc key state (MSB set = currently pressed)
                key_state = user32.GetAsyncKeyState(VK_ESCAPE)
                if key_state & 0x8000:
                    self.trigger_abort()

                # Physical mouse movement override detection
                if self.ai_controlling and not self._abort_event.is_set():
                    cur_x, cur_y = self._get_cursor_pos()
                    dx = cur_x - self.last_ai_pos[0]
                    dy = cur_y - self.last_ai_pos[1]
                    physical_deviation = math.hypot(dx, dy)
                    if physical_deviation > self.override_threshold_px:
                        # User physically yanked the mouse away from the AI
                        self.trigger_abort()

            time.sleep(self.check_interval_s)

# Global singleton failsafe instance
FAILSAFE = FailsafeSentinel()

