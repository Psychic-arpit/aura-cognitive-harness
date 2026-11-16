"""
aura.ui.overlay - Luminescent Ethereal Cursor Companion & Ghost Telemetry Overlay
Renders real-time kinetic comet trails, ambient plasma aura, orbiting AI state beads,
and tactical target-lock reticles at locked 60 FPS.
Passes through all mouse input (WA_TransparentForMouseEvents) and shielded via WDA_EXCLUDEFROMCAPTURE (0x11).
"""

import time
import math
import ctypes
from ctypes import wintypes
from collections import deque
from typing import Optional, Tuple, List, Dict, Any
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QRadialGradient, QLinearGradient
from PyQt6.QtWidgets import QWidget, QApplication
from aura.harness.stealth import STEALTH

user32 = ctypes.WinDLL("user32", use_last_error=True)

class AuraOverlayWindow(QWidget):
    def __init__(self, mode: str = "mach"):
        super().__init__()
        self.mode = mode

        # Cursor Companion State
        self.companion_enabled = True
        self.ai_state = "idle"  # 'idle', 'thinking', 'navigating', 'actuating'
        self.curr_x = 0.0
        self.curr_y = 0.0
        self.smooth_x = 0.0
        self.smooth_y = 0.0
        self.velocity = 0.0
        self.breath_phase = 0.0
        self.orbit_phase = 0.0

        # Telemetry collections
        self.trail = deque(maxlen=28)
        self.click_ripples: List[Dict[str, Any]] = []
        self.target_crosshair: Optional[Tuple[float, float, str]] = None
        self.target_reticle_scale = 1.0

        # Initialize cursor position
        pt = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        self.curr_x = float(pt.x)
        self.curr_y = float(pt.y)
        self.smooth_x = self.curr_x
        self.smooth_y = self.curr_y

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)

        self._apply_stealth()

        # 60 FPS High-precision compositor timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(16)

    def _apply_stealth(self):
        try:
            hwnd = int(self.winId())
            STEALTH.apply_stream_invisibility(hwnd)
        except Exception:
            pass

    def showEvent(self, event):
        super().showEvent(event)
        self._apply_stealth()

    def set_ai_state(self, state: str):
        """Sets agent telemetry state: 'idle', 'thinking', 'navigating', 'actuating'."""
        self.ai_state = state

    def toggle_companion(self):
        self.companion_enabled = not self.companion_enabled

    def update_telemetry(self, x: float, y: float):
        """Called during agent cursor glide trajectory."""
        self.curr_x = x
        self.curr_y = y
        self.smooth_x = x
        self.smooth_y = y
        self.trail.append((x, y, time.time(), 14.0))

    def trigger_click(self, x: float, y: float):
        """Spawns concentric luminescent shockwave ripples on click."""
        self.click_ripples.append({"x": x, "y": y, "radius": 4.0, "alpha": 220, "max_radius": 44})
        self.click_ripples.append({"x": x, "y": y, "radius": 1.0, "alpha": 180, "max_radius": 28})

    def lock_target(self, x: float, y: float, label: str = ""):
        """Locks laser reticle onto UI target."""
        self.target_crosshair = (x, y, label)
        self.target_reticle_scale = 1.4

    def clear_target(self):
        self.target_crosshair = None

    def clear_overlay(self):
        self.trail.clear()
        self.click_ripples.clear()
        self.target_crosshair = None
        self.ai_state = "idle"

    def _tick(self):
        # Sample physical mouse position directly
        pt = wintypes.POINT()
        if user32.GetCursorPos(ctypes.byref(pt)):
            nx = float(pt.x)
            ny = float(pt.y)
            dx = nx - self.curr_x
            dy = ny - self.curr_y
            inst_v = math.hypot(dx, dy)
            # Smooth velocity filter for responsive kinetic line-width scaling without spatial lag
            self.velocity = (self.velocity * 0.6) + (inst_v * 0.4)
            self.curr_x = nx
            self.curr_y = ny
            self.smooth_x = nx
            self.smooth_y = ny

        # Update harmonic phases
        self.breath_phase = (self.breath_phase + 0.05) % (2 * math.pi)
        self.orbit_phase = (self.orbit_phase + 0.14) % (2 * math.pi)

        now = time.time()
        # Record comet wake directly anchored to cursor
        if self.velocity > 1.2 and self.companion_enabled:
            if not self.trail or math.hypot(self.curr_x - self.trail[-1][0], self.curr_y - self.trail[-1][1]) >= 2.0:
                self.trail.append((self.curr_x, self.curr_y, now, self.velocity))

        # Evict old trail points (> 280ms)
        while self.trail and (now - self.trail[0][2]) > 0.28:
            self.trail.popleft()

        # Update shockwaves
        active_ripples = []
        for r in self.click_ripples:
            r["radius"] += 2.8
            r["alpha"] -= 14
            if r["alpha"] > 0 and r["radius"] < r["max_radius"]:
                active_ripples.append(r)
        self.click_ripples = active_ripples

        # Smooth reticle scale snap
        if self.target_reticle_scale > 1.0:
            self.target_reticle_scale = max(1.0, self.target_reticle_scale - 0.05)

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        now = time.time()

        # 1. Kinetic Comet Tail (Anchored directly to physical cursor with 0 gap)
        if self.companion_enabled and len(self.trail) > 0:
            pts = list(self.trail)
            # Seamlessly attach the head of the trail to the current physical cursor coordinates
            if pts[-1][0] != self.curr_x or pts[-1][1] != self.curr_y:
                pts.append((self.curr_x, self.curr_y, now, max(self.velocity, 6.0)))

            if len(pts) >= 2:
                for i in range(len(pts) - 1):
                    x1, y1, t1, v1 = pts[i]
                    x2, y2, t2, v2 = pts[i + 1]
                    age_ratio = 1.0 - min(1.0, (now - t1) / 0.28)
                    alpha = int(160 * (age_ratio ** 1.4))
                    width = 1.8 + (v1 / 18.0) * age_ratio * 4.0

                    color = QColor(255, 255, 255, alpha)
                    pen = QPen(color, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
                    painter.setPen(pen)
                    painter.drawLine(int(x1), int(y1), int(x2), int(y2))

        # 2. Click Shockwave Ripples
        for r in self.click_ripples:
            color = QColor(255, 255, 255, int(r["alpha"]))
            painter.setPen(QPen(color, 1.6))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            rad = r["radius"]
            painter.drawEllipse(QRectF(r["x"] - rad, r["y"] - rad, rad * 2, rad * 2))

        # 3. Tactical Target-Lock Reticle & Laser Trace
        if self.target_crosshair:
            tx, ty, label = self.target_crosshair
            # Thin translucent laser guide beam anchored directly to cursor
            guide_pen = QPen(QColor(255, 255, 255, 70), 1.0, Qt.PenStyle.DashLine)
            painter.setPen(guide_pen)
            painter.drawLine(int(self.curr_x), int(self.curr_y), int(tx), int(ty))

            # Reticle Box with Corner Brackets
            reticle_size = 18.0 * self.target_reticle_scale
            h_sz = reticle_size / 2.0
            corner_len = 5.0

            bracket_pen = QPen(QColor(255, 255, 255, 200), 1.6)
            painter.setPen(bracket_pen)

            # Top-Left [
            painter.drawLine(int(tx - h_sz), int(ty - h_sz), int(tx - h_sz + corner_len), int(ty - h_sz))
            painter.drawLine(int(tx - h_sz), int(ty - h_sz), int(tx - h_sz), int(ty - h_sz + corner_len))
            # Top-Right ]
            painter.drawLine(int(tx + h_sz), int(ty - h_sz), int(tx + h_sz - corner_len), int(ty - h_sz))
            painter.drawLine(int(tx + h_sz), int(ty - h_sz), int(tx + h_sz), int(ty - h_sz + corner_len))
            # Bottom-Left [
            painter.drawLine(int(tx - h_sz), int(ty + h_sz), int(tx - h_sz + corner_len), int(ty + h_sz))
            painter.drawLine(int(tx - h_sz), int(ty + h_sz), int(tx - h_sz), int(ty + h_sz - corner_len))
            # Bottom-Right ]
            painter.drawLine(int(tx + h_sz), int(ty + h_sz), int(tx + h_sz - corner_len), int(ty + h_sz))
            painter.drawLine(int(tx + h_sz), int(ty + h_sz), int(tx + h_sz), int(ty + h_sz - corner_len))

            # Target Center Dot
            painter.setBrush(QBrush(QColor(255, 255, 255, 220)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QRectF(tx - 2, ty - 2, 4, 4))

        # 4. Luminescent Ethereal Cursor Companion Halo (Anchored directly to cursor)
        if self.companion_enabled:
            cx = self.curr_x
            cy = self.curr_y

            # Ambient breathing oscillation
            breath = math.sin(self.breath_phase) * 1.5
            core_rad = 9.0 + breath

            # Outer diffuse glow aura
            glow_rad = 28.0 + breath * 2.0
            grad = QRadialGradient(QPointF(cx, cy), glow_rad)
            grad.setColorAt(0.0, QColor(255, 255, 255, 55))
            grad.setColorAt(0.4, QColor(255, 255, 255, 22))
            grad.setColorAt(1.0, QColor(255, 255, 255, 0))

            painter.setBrush(QBrush(grad))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QRectF(cx - glow_rad, cy - glow_rad, glow_rad * 2, glow_rad * 2))

            # Inner frosted glass halo ring
            ring_pen = QPen(QColor(255, 255, 255, 140), 1.2)
            painter.setPen(ring_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QRectF(cx - core_rad, cy - core_rad, core_rad * 2, core_rad * 2))

            # Subtle center focus point
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(255, 255, 255, 190)))
            painter.drawEllipse(QRectF(cx - 2, cy - 2, 4, 4))

            # 5. Orbiting AI State Beads (active when thinking or actuating)
            if self.ai_state in ("thinking", "actuating", "navigating"):
                orbit_rad = 14.0
                # Bead 1
                bx1 = cx + math.cos(self.orbit_phase) * orbit_rad
                by1 = cy + math.sin(self.orbit_phase) * orbit_rad
                # Bead 2 (Opposite)
                bx2 = cx + math.cos(self.orbit_phase + math.pi) * orbit_rad
                by2 = cy + math.sin(self.orbit_phase + math.pi) * orbit_rad

                painter.setBrush(QBrush(QColor(255, 255, 255, 240)))
                painter.drawEllipse(QRectF(bx1 - 2.0, by1 - 2.0, 4.0, 4.0))
                painter.drawEllipse(QRectF(bx2 - 2.0, by2 - 2.0, 4.0, 4.0))

        painter.end()
