"""
config/tokens.py - Dark Obsidian Design System Tokens
Strict compliance with UI/UX Pro Max and Anti-Slop principles.
Zero decorative noise. 100% purpose-driven visual hierarchy.
"""

from dataclasses import dataclass

@dataclass(frozen=True)
class AuraTheme:
    # Surface & Glass Materials
    BG_CANVAS: str = "#07090E"
    BG_CAPSULE: str = "rgba(11, 15, 23, 0.84)"
    BG_CAPSULE_HOVER: str = "rgba(16, 22, 34, 0.92)"
    BG_SURFACE_SUBTLE: str = "rgba(255, 255, 255, 0.04)"
    BG_INPUT: str = "rgba(255, 255, 255, 0.03)"

    # Hairline Borders & Edge Highlights
    BORDER_HAIRLINE: str = "rgba(255, 255, 255, 0.08)"
    BORDER_HIGHLIGHT: str = "rgba(255, 255, 255, 0.16)"
    BORDER_ACTIVE: str = "rgba(0, 240, 255, 0.40)"
    BLUR_RADIUS: int = 20

    # Functional State Accents (Single-Role High Contrast)
    ACCENT_MACH: str = "#00F0FF"          # Mach Speed (Sharp Electric Cyan)
    ACCENT_BIO: str = "#A855F7"           # Biomimetic Mode (Deep Amethyst)
    ACCENT_DANGER: str = "#EF4444"        # Esc Panic / Stop (Crimson)
    ACCENT_SUCCESS: str = "#10B981"       # Action Verified / Ready (Emerald)
    ACCENT_WARN: str = "#F59E0B"          # Thinking / Verifying (Amber)

    # Typography
    FONT_UI: str = "Segoe UI, Inter, -apple-system, sans-serif"
    FONT_MONO: str = "Cascadia Code, JetBrains Mono, Consolas, monospace"
    TEXT_PRIMARY: str = "#F8FAFC"         # High legibility white
    TEXT_SECONDARY: str = "#94A3B8"       # Functional metadata slate
    TEXT_MUTED: str = "#475569"           # Inactive cues & placeholders

    # Physical Dimensions
    CAPSULE_IDLE_WIDTH: int = 152
    CAPSULE_IDLE_HEIGHT: int = 28
    CAPSULE_ACTIVE_WIDTH: int = 540
    CAPSULE_ACTIVE_HEIGHT: int = 48
    CAPSULE_RADIUS: int = 14

TOKENS = AuraTheme()
