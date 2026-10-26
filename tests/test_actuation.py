"""
tests/test_actuation.py - Unit Tests for Actuation, Safety Circuit & Stealth Shield
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
from aura.harness.actuation import ACTUATION
from aura.harness.safety import SAFETY
from aura.harness.stealth import STEALTH

def test_cursor_telemetry():
    t0 = time.perf_counter()
    x, y = ACTUATION.get_cursor_pos()
    elapsed_us = (time.perf_counter() - t0) * 1_000_000
    assert isinstance(x, int) and isinstance(y, int)
    print(f"  [PASS] Cursor Telemetry: ({x}, {y}) in {elapsed_us:.1f}us")

def test_safety_watchdog():
    SAFETY.activate(step_budget=3)
    assert not SAFETY.is_aborted()
    assert SAFETY.record_step()  # 1
    assert SAFETY.record_step()  # 2
    assert SAFETY.record_step()  # 3
    assert not SAFETY.record_step()  # 4 -> Budget exceeded
    assert SAFETY.is_aborted()
    SAFETY.deactivate()
    print("  [PASS] Safety Governor: Action step budget tripwire verified")

def test_stealth_display_affinity():
    res = STEALTH.apply_stream_invisibility(0)
    assert res is False
    print("  [PASS] Stealth Shield: Display affinity function safe and valid")

if __name__ == "__main__":
    print("Running Actuation & Safety Harness Tests...")
    test_cursor_telemetry()
    test_safety_watchdog()
    test_stealth_display_affinity()
    print("ALL ACTUATION & SAFETY TESTS PASSED [100%]\n")
