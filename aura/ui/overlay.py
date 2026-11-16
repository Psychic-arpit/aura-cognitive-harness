"""
aura.ui.overlay - Celestial Plasma Cursor AI Companion & Ghost Co-Pilot Hologram
60 FPS hardware compositor rendering kinetic comet tails, celestial stardust embers,
ambient multi-spectral plasma auras, orbiting AI photon beads, and holographic ghost execution vectors.
Shielded via OS-level WDA_EXCLUDEFROMCAPTURE (0x11) for zero screen-recorder footprint.
"""

import time
import math
import random
import ctypes
from ctypes import wintypes
from collections import deque
from typing import Optional, Tuple, List, Dict, Any
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QRadialGradient, QLinearGradient, QFont
from PyQt6.QtWidgets import QWidget, QApplication
from aura.harness.stealth import STEALTH

user32 = ctypes.WinDLL("user32", use_last_error=True)

class StardustParticle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "size", "r", "g", "b")

    def __init__(self, x: float, y: float, vx: float, vy: float, max_life: float = 0.38, size: float = 2.4, color: Tuple[int, int, int] = (56, 189, 248)):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = max_life
        self.max_life = max_life
        self.size = size
        self.r, self.g, self.b = color

    def update(self, dt: float) -> bool:
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vx *= 0.92
        self.vy *= 0.92
        self.life -= dt
        return self.life > 0.0

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

        # Celestial Stardust Particles
        self.particles: List[StardustParticle] = []

        # Holographic Ghost Co-Pilot (for agent autonomous execution)
        self.ghost_enabled = False
        self.ghost_x = 0.0
        self.ghost_y = 0.0
        self.ghost_label = ""
        self.ghost_phase = 0.0

        # Telemetry collections
        self.trail = deque(maxlen=32)
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

        # 60 FPS High-precision compositor timer (16ms)
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

    def set_mode(self, mode: str):
        self.mode = mode

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
        self.trail.append((x, y, time.time(), 16.0))

    def set_ghost_co_pilot(self, x: float, y: float, label: str = ""):
        """Positions the Holographic Ghost Co-Pilot for autonomous execution."""
        self.ghost_enabled = True
        self.ghost_x = x
        self.ghost_y = y
        self.ghost_label = label

    def clear_ghost_co_pilot(self):
        self.ghost_enabled = False
        self.ghost_label = ""

    def trigger_click(self, x: float, y: float):
        """Spawns iridescent shockwaves and diamond sparks on click."""
        self.click_ripples.append({"x": x, "y": y, "radius": 4.0, "alpha": 240, "max_radius": 48})
        self.click_ripples.append({"x": x, "y": y, "radius": 1.0, "alpha": 190, "max_radius": 32})
        # Micro-spark bursts at click point
        for _ in range(6):
            ang = random.uniform(0, 2 * math.pi)
            spd = random.uniform(40, 110)
            self.particles.append(StardustParticle(
                x, y,
                math.cos(ang) * spd,
                math.sin(ang) * spd,
                max_life=0.28,
                size=random.uniform(2.0, 3.8),
                color=(255, 255, 255)
            ))

    def lock_target(self, x: float, y: float, label: str = ""):
        """Locks laser reticle onto UI target."""
        self.target_crosshair = (x, y, label)
        self.target_reticle_scale = 1.4

    def clear_target(self):
        self.target_crosshair = None

    def clear_overlay(self):
        self.trail.clear()
        self.particles.clear()
        self.click_ripples.clear()
        self.target_crosshair = None
        self.ghost_enabled = False
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
            self.velocity = (self.velocity * 0.6) + (inst_v * 0.4)
            self.curr_x = nx
            self.curr_y = ny
            self.smooth_x = nx
            self.smooth_y = ny

            # Spawn celestial stardust particles along velocity vector
            if self.velocity > 2.8 and self.companion_enabled:
                if len(self.particles) < 48:
                    speed = min(self.velocity, 40.0)
                    angle = math.atan2(dy, dx) + math.pi + random.uniform(-0.5, 0.5)
                    p_spd = random.uniform(10, 35) + speed * 0.4
                    # Chromatic palette: Sky Cyan or Electric Violet
                    col = (56, 189, 248) if random.random() > 0.4 else (192, 132, 252)
                    self.particles.append(StardustParticle(
                        self.curr_x, self.curr_y,
                        math.cos(angle) * p_spd,
                        math.sin(angle) * p_spd,
                        max_life=random.uniform(0.24, 0.40),
                        size=random.uniform(1.8, 3.2),
                        color=col
                    ))

        # Update harmonic phases
        speed_factor = 1.0 + min(self.velocity / 15.0, 2.5)
        self.breath_phase = (self.breath_phase + 0.05) % (2 * math.pi)
        orbit_speed = 0.28 if self.ai_state in ("thinking", "actuating") else 0.12
        self.orbit_phase = (self.orbit_phase + orbit_speed * speed_factor) % (2 * math.pi)
        self.ghost_phase = (self.ghost_phase + 0.08) % (2 * math.pi)

        now = time.time()
        # Record comet wake directly anchored to cursor
        if self.velocity > 1.2 and self.companion_enabled:
            if not self.trail or math.hypot(self.curr_x - self.trail[-1][0], self.curr_y - self.trail[-1][1]) >= 2.0:
                self.trail.append((self.curr_x, self.curr_y, now, self.velocity))

        # Evict old trail points (> 280ms)
        while self.trail and (now - self.trail[0][2]) > 0.28:
            self.trail.popleft()

        # Update particles (0.016s)
        self.particles = [p for p in self.particles if p.update(0.016)]

        # Update shockwaves
        active_ripples = []
        for r in self.click_ripples:
            r["radius"] += 3.2
            r["alpha"] -= 16
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

        # 1. Celestial Stardust Particles
        for p in self.particles:
            ratio = max(0.0, p.life / p.max_life)
            alpha = int(220 * (ratio ** 1.2))
            sz = p.size * (0.6 + 0.4 * ratio)

            # Soft glowing ember
            grad = QRadialGradient(QPointF(p.x, p.y), sz * 2.0)
            grad.setColorAt(0.0, QColor(p.r, p.g, p.b, alpha))
            grad.setColorAt(0.5, QColor(p.r, p.g, p.b, int(alpha * 0.4)))
            grad.setColorAt(1.0, QColor(p.r, p.g, p.b, 0))

            painter.setBrush(QBrush(grad))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QRectF(p.x - sz * 2, p.y - sz * 2, sz * 4, sz * 4))

        # 2. Kinetic Comet Tail (Dual-Pass Celestial Plasma & Laser Core)
        if self.companion_enabled and len(self.trail) > 0:
            pts = list(self.trail)
            if pts[-1][0] != self.curr_x or pts[-1][1] != self.curr_y:
                pts.append((self.curr_x, self.curr_y, now, max(self.velocity, 6.0)))

            if len(pts) >= 2:
                # Pass 1: Outer Plasma Dispersion Glow
                for i in range(len(pts) - 1):
                    x1, y1, t1, v1 = pts[i]
                    x2, y2, t2, v2 = pts[i + 1]
                    age_ratio = 1.0 - min(1.0, (now - t1) / 0.28)
                    plasma_alpha = int(95 * (age_ratio ** 1.3))
                    plasma_width = 3.5 + (v1 / 14.0) * age_ratio * 6.0

                    color = QColor(56, 189, 248, plasma_alpha)  # Sky Cyan plasma
                    pen = QPen(color, plasma_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
                    painter.setPen(pen)
                    painter.drawLine(int(x1), int(y1), int(x2), int(y2))

                # Pass 2: Inner Hyper-Bright Laser Core
                for i in range(len(pts) - 1):
                    x1, y1, t1, v1 = pts[i]
                    x2, y2, t2, v2 = pts[i + 1]
                    age_ratio = 1.0 - min(1.0, (now - t1) / 0.28)
                    core_alpha = int(185 * (age_ratio ** 1.5))
                    core_width = 1.6 + (v1 / 22.0) * age_ratio * 3.0

                    color = QColor(255, 255, 255, core_alpha)
                    pen = QPen(color, core_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
                    painter.setPen(pen)
                    painter.drawLine(int(x1), int(y1), int(x2), int(y2))

        # 3. Click Shockwave Ripples (Iridescent Double-Rings)
        for r in self.click_ripples:
            alpha = int(r["alpha"])
            color_outer = QColor(56, 189, 248, alpha)
            color_inner = QColor(255, 255, 255, int(alpha * 0.8))

            painter.setBrush(Qt.BrushStyle.NoBrush)
            rad = r["radius"]

            painter.setPen(QPen(color_outer, 2.0))
            painter.drawEllipse(QRectF(r["x"] - rad, r["y"] - rad, rad * 2, rad * 2))

            painter.setPen(QPen(color_inner, 1.0))
            painter.drawEllipse(QRectF(r["x"] - rad * 0.65, r["y"] - rad * 0.65, rad * 1.3, rad * 1.3))

        # 4. Tactical Target-Lock Reticle & Laser Trace
        if self.target_crosshair:
            tx, ty, label = self.target_crosshair
            guide_pen = QPen(QColor(56, 189, 248, 120), 1.2, Qt.PenStyle.DashLine)
            painter.setPen(guide_pen)
            painter.drawLine(int(self.curr_x), int(self.curr_y), int(tx), int(ty))

            reticle_size = 20.0 * self.target_reticle_scale
            h_sz = reticle_size / 2.0
            corner_len = 6.0

            bracket_pen = QPen(QColor(56, 189, 248, 230), 1.8)
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

            painter.setBrush(QBrush(QColor(255, 255, 255, 240)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QRectF(tx - 2.5, ty - 2.5, 5, 5))

        # 5. Holographic Ghost Co-Pilot (Autonomous Agent Visualizer)
        if self.ghost_enabled:
            gx, gy = self.ghost_x, self.ghost_y
            pulse = math.sin(self.ghost_phase) * 2.0

            # Dynamic holographic vector to physical cursor
            holo_beam = QPen(QColor(168, 85, 247, 140), 1.2, Qt.PenStyle.DotLine)
            painter.setPen(holo_beam)
            painter.drawLine(int(self.curr_x), int(self.curr_y), int(gx), int(gy))

            # Ghost Reticle Diamond
            sz = 14.0 + pulse
            poly_pen = QPen(QColor(192, 132, 252, 230), 1.6)
            painter.setPen(poly_pen)
            painter.setBrush(QBrush(QColor(168, 85, 247, 45)))
            pts_diamond = [
                QPointF(gx, gy - sz),
                QPointF(gx + sz, gy),
                QPointF(gx, gy + sz),
                QPointF(gx - sz, gy)
            ]
            painter.drawPolygon(*pts_diamond)

            # Center Quantum Bead
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(255, 255, 255, 240)))
            painter.drawEllipse(QRectF(gx - 2.5, gy - 2.5, 5.0, 5.0))

            # Aerospace Floating Badge
            if self.ghost_label:
                badge_text = f"CO-PILOT: {self.ghost_label[:28]}"
                painter.setFont(QFont("Segoe UI Variable Display", 8, QFont.Weight.DemiBold))
                fm = painter.fontMetrics()
                bw = fm.horizontalAdvance(badge_text) + 14
                bh = 18

                bx = gx - (bw / 2)
                by = gy - sz - 26

                painter.setBrush(QBrush(QColor(15, 23, 42, 210)))
                painter.setPen(QPen(QColor(192, 132, 252, 160), 1.0))
                painter.drawRoundedRect(QRectF(bx, by, bw, bh), 4.0, 4.0)

                painter.setPen(QColor(241, 245, 249, 230))
                painter.drawText(QRectF(bx, by, bw, bh), Qt.AlignmentFlag.AlignCenter, badge_text)

        # 6. Luminescent Celestial Plasma Cursor Companion Halo (Anchored directly to cursor)
        if self.companion_enabled:
            cx = self.curr_x
            cy = self.curr_y

            # Dynamic velocity flaring
            v_flare = min(self.velocity / 20.0, 1.8)
            breath = math.sin(self.breath_phase) * 1.4

            # Outer diffuse multi-spectral plasma aura (Cyan to Violet)
            glow_rad = 28.0 + breath * 2.0 + v_flare * 8.0
            grad = QRadialGradient(QPointF(cx, cy), glow_rad)
            grad.setColorAt(0.0, QColor(56, 189, 248, int(60 + v_flare * 35)))
            grad.setColorAt(0.45, QColor(168, 85, 247, int(26 + v_flare * 18)))
            grad.setColorAt(1.0, QColor(168, 85, 247, 0))

            painter.setBrush(QBrush(grad))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QRectF(cx - glow_rad, cy - glow_rad, glow_rad * 2, glow_rad * 2))

            # Inner frosted glass halo ring
            core_rad = 9.0 + breath + v_flare * 2.0
            ring_pen = QPen(QColor(255, 255, 255, 160), 1.2)
            painter.setPen(ring_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QRectF(cx - core_rad, cy - core_rad, core_rad * 2, core_rad * 2))

            # Subtle celestial center focus dot
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(255, 255, 255, 220)))
            painter.drawEllipse(QRectF(cx - 2, cy - 2, 4, 4))

            # 7. Orbiting AI Quantum Beads (Reactive during thinking/actuating)
            if self.ai_state in ("thinking", "actuating", "navigating") or self.ghost_enabled:
                orbit_rad = 15.0 + v_flare * 2.0
                bx1 = cx + math.cos(self.orbit_phase) * orbit_rad
                by1 = cy + math.sin(self.orbit_phase) * orbit_rad
                bx2 = cx + math.cos(self.orbit_phase + math.pi) * orbit_rad
                by2 = cy + math.sin(self.orbit_phase + math.pi) * orbit_rad

                # Primary Quantum Bead (Cyan)
                painter.setBrush(QBrush(QColor(56, 189, 248, 250)))
                painter.drawEllipse(QRectF(bx1 - 2.5, by1 - 2.5, 5.0, 5.0))

                # Secondary Quantum Bead (Violet)
                painter.setBrush(QBrush(QColor(192, 132, 252, 250)))
                painter.drawEllipse(QRectF(bx2 - 2.5, by2 - 2.5, 5.0, 5.0))

        painter.end()
