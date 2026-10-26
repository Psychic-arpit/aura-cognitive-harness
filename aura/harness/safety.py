"""
aura.harness.safety - Real-Time Execution Watchdog & Failsafe Circuit Breaker
Intercepts runaway agent actions, enforces physical mouse-shake interrupts, and monitors Esc kill-switch.
"""

import time
import ctypes
import threading
from typing import Callable, List, Optional

user32 = ctypes.WinDLL("user32", use_last_error=True)
VK_ESCAPE = 0x1B

class SafetyHarness:
    def __init__(self):
        self._is_active = False
        self._abort_flag = False
        self._thread: Optional[threading.Thread] = None
        self._callbacks: List[Callable[[], None]] = []
        self._step_budget = 10
        self._current_step = 0

    def register_abort_callback(self, cb: Callable[[], None]):
        self._callbacks.append(cb)

    def start_watchdog(self):
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._watchdog_loop, name="AuraSafetyWatchdog", daemon=True)
        self._thread.start()

    def activate(self, step_budget: int = 10):
        self._abort_flag = False
        self._step_budget = step_budget
        self._current_step = 0
        self._is_active = True

    def deactivate(self):
        self._is_active = False
        self._abort_flag = False

    def is_aborted(self) -> bool:
        return self._abort_flag

    def record_step(self) -> bool:
        """Increments step count. Returns False if budget exceeded."""
        self._current_step += 1
        if self._current_step > self._step_budget:
            self.trigger_abort("Action step budget exceeded")
            return False
        return True

    def trigger_abort(self, reason: str = "User interrupt"):
        if self._abort_flag:
            return
        self._abort_flag = True
        self._is_active = False
        print(f"\n[AURA SAFETY] Abort Triggered: {reason}")
        for cb in self._callbacks:
            try:
                cb()
            except Exception as e:
                print(f"[AURA SAFETY] Callback error: {e}")

    def _watchdog_loop(self):
        while True:
            if self._is_active:
                # 1. Esc Key check
                if user32.GetAsyncKeyState(VK_ESCAPE) & 0x8000:
                    self.trigger_abort("Emergency Esc key pressed")
                    time.sleep(0.5)

                # 2. Mouse corner panic check (top-left 5x5 px)
                pt = (ctypes.c_long * 2)()
                user32.GetCursorPos(pt)
                if pt[0] <= 5 and pt[1] <= 5:
                    self.trigger_abort("Mouse flicked to top-left corner")
                    time.sleep(0.5)

            time.sleep(0.016)  # 60Hz polling

SAFETY = SafetyHarness()
SAFETY.start_watchdog()
