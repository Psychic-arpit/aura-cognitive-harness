"""
tests/test_perception.py - Unit Tests for Sensory Perception & Context Ingestion
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
from aura.harness.perception import PERCEPTION
from aura.agent.client import anonymize_text

def test_foreground_perception():
    t0 = time.perf_counter()
    fg = PERCEPTION.get_foreground_window()
    elapsed_ms = (time.perf_counter() - t0) * 1000
    assert "hwnd" in fg
    assert "title" in fg
    assert "process" in fg
    assert "category" in fg
    print(f"  [PASS] Foreground: {fg['process']} ('{fg['title'][:30]}') in {elapsed_ms:.2f}ms")

def test_context_snapshot():
    # Warm run
    _ = PERCEPTION.get_context_snapshot()
    t0 = time.perf_counter()
    ctx = PERCEPTION.get_context_snapshot()
    elapsed_ms = (time.perf_counter() - t0) * 1000
    assert "window" in ctx
    assert "clipboard" in ctx
    print(f"  [PASS] Context Snapshot generated in {elapsed_ms:.2f}ms")

def test_pii_anonymization():
    raw_prompt = "User file at C:\\Users\\arpit\\secret.txt on IP 192.168.1.50 with token AIzaSyD1234567890123456789012345678901"
    clean = anonymize_text(raw_prompt)
    assert "arpit" not in clean, "Username not stripped!"
    assert "C:\\Users\\" not in clean, "Windows path not converted to ~!"
    assert "192.168.1.50" not in clean, "IP not masked!"
    assert "AIzaSy" not in clean, "Token not masked!"
    print(f"  [PASS] PII Anonymization: Cleaned successfully -> {clean}")

if __name__ == "__main__":
    print("Running Perception & Privacy Harness Tests...")
    test_foreground_perception()
    test_context_snapshot()
    test_pii_anonymization()
    print("ALL PERCEPTION TESTS PASSED [100%]\n")
