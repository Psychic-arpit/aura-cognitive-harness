"""
tests/test_cursor_ai.py - Unit & Integration Tests for Luminescent Cursor AI, Inline Lens & Vision Grounding
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
from PyQt6.QtWidgets import QApplication
from aura.agent.router import ROUTER
from aura.harness.uia import UIA
from aura.ui.overlay import AuraOverlayWindow
from aura.ui.lens import CursorLens

def test_context_decorators():
    # 1. @screen
    i_screen = ROUTER.route("@screen analyze this UI error")
    assert i_screen.type == "context_ai"
    assert i_screen.extra.get("force_visual") is True
    print("  [PASS] Context Decorator: '@screen' -> force_visual=True")

    # 2. @clip
    i_clip = ROUTER.route("@clip explain this code")
    assert i_clip.type == "context_ai"
    assert i_clip.extra.get("force_clipboard") is True
    print("  [PASS] Context Decorator: '@clip' -> force_clipboard=True")

    # 3. @git
    i_git = ROUTER.route("@git")
    assert i_git.type == "git_status"
    print("  [PASS] Context Decorator: '@git' -> git_status")

def test_cursor_overlay_and_companion():
    app = QApplication.instance() or QApplication(sys.argv)
    overlay = AuraOverlayWindow()
    assert overlay.companion_enabled is True

    # Test telemetry feed & physical cursor anchor
    overlay.update_telemetry(450.0, 320.0)
    assert len(overlay.trail) > 0
    assert overlay.curr_x == 450.0 and overlay.curr_y == 320.0
    assert overlay.trail[-1][0] == 450.0 and overlay.trail[-1][1] == 320.0
    print("  [PASS] Cursor Telemetry Feed: Point appended to kinetic wake & anchored directly to cursor")

    # Test tactical reticle lock
    overlay.lock_target(600.0, 400.0, "Submit Button")
    assert overlay.target_crosshair == (600.0, 400.0, "Submit Button")
    print("  [PASS] Tactical Reticle: Target lock coordinates verified")

    # Test shockwave ripple & stardust particle generation
    overlay.trigger_click(600.0, 400.0)
    assert len(overlay.click_ripples) == 2
    assert len(overlay.particles) >= 6
    print("  [PASS] Concentric Shockwave: 2 ripple rings & 6 micro-sparks spawned on click")

    # Test Holographic Ghost Co-Pilot
    overlay.set_ghost_co_pilot(800.0, 450.0, "Test Autopilot Navigation")
    assert overlay.ghost_enabled is True
    assert overlay.ghost_x == 800.0 and overlay.ghost_y == 450.0
    assert overlay.ghost_label == "Test Autopilot Navigation"
    overlay.clear_ghost_co_pilot()
    assert overlay.ghost_enabled is False
    print("  [PASS] Holographic Ghost Co-Pilot: Telemetry vector & HUD state verified")

    # Test AI state toggle
    overlay.set_ai_state("thinking")
    assert overlay.ai_state == "thinking"
    overlay._tick()
    assert overlay.orbit_phase > 0.0
    print("  [PASS] Orbiting Thinking Beads: Phase progression verified")

    overlay.clear_overlay()
    assert len(overlay.click_ripples) == 0
    assert overlay.target_crosshair is None
    print("  [PASS] Overlay Reset: Clean state verified")

def test_inline_cursor_lens():
    app = QApplication.instance() or QApplication(sys.argv)
    lens = CursorLens()
    lens.summon_at_cursor()
    assert lens.isVisible()
    print(f"  [PASS] Floating Cursor Lens: Summoned at ({lens.x()}, {lens.y()})")

    # Test inline answer & action buttons
    lens.show_inline_answer("Inline reasoning stream active.")
    assert lens.resp_box.isVisible()
    assert lens.latest_answer_raw == "Inline reasoning stream active."
    lens._copy_answer_to_clipboard()
    assert app.clipboard().text() == "Inline reasoning stream active."
    print("  [PASS] Inline Answer Viewport & 1-Click Clipboard: Verified cleanly")

    lens.dismiss_lens()
    assert not lens.isVisible()
    print("  [PASS] Lens Dismiss: Hidden cleanly")

def test_uia_visual_grounding_heuristics():
    # Landmark coordinates
    pos = UIA.resolve_target("center of screen")
    assert pos is not None and len(pos) == 2
    print(f"  [PASS] UIA Landmark Grounding: Center resolved to {pos}")

if __name__ == "__main__":
    print("Running Luminescent Cursor AI & Inline Lens Tests...")
    test_context_decorators()
    test_cursor_overlay_and_companion()
    test_inline_cursor_lens()
    test_uia_visual_grounding_heuristics()
    print("ALL CURSOR AI TESTS PASSED [100%]\n")
