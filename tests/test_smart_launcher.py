"""
tests/test_smart_launcher.py - Unit Tests for Zero-Error Smart App & Protocol Launcher
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aura.harness.smart_launcher import SMART_LAUNCHER

def test_spotify_resolution():
    res = SMART_LAUNCHER.resolve_app("spotify")
    assert res is not None, "Spotify resolution failed!"
    assert "spotify" in res.lower(), f"Unexpected resolution: {res}"
    print(f"  [PASS] Spotify Resolved: {res}")

def test_discord_resolution():
    res = SMART_LAUNCHER.resolve_app("discord")
    assert res is not None, "Discord resolution failed!"
    assert "discord" in res.lower(), f"Unexpected resolution: {res}"
    print(f"  [PASS] Discord Resolved: {res}")

def test_core_apps():
    apps = [("calc", "calc"), ("paint", "mspaint"), ("notepad", "notepad"), ("taskmgr", "taskmgr")]
    for name, expected in apps:
        res = SMART_LAUNCHER.resolve_app(name)
        assert res == expected, f"Expected {expected} for {name}, got {res}"
        print(f"  [PASS] Core App: '{name}' -> '{res}'")

def test_dynamic_protocol_fallback():
    res = SMART_LAUNCHER.resolve_app("customprotocol")
    assert res == "customprotocol:", f"Expected protocol fallback, got {res}"
    print(f"  [PASS] Protocol Fallback: 'customprotocol' -> '{res}'")

if __name__ == "__main__":
    print("Running Zero-Error Smart Launcher Tests...")
    test_spotify_resolution()
    test_discord_resolution()
    test_core_apps()
    test_dynamic_protocol_fallback()
    print("ALL SMART LAUNCHER TESTS PASSED [100%]\n")
