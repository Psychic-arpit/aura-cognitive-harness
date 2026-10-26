"""
core/shaders.py - Purpose-Driven Sci-Fi Cyber Vector Rendering
Compliant with Open Design and UI/UX Pro Max standards.
Zero decorative noise. Renders Tapered Directional Vector Wakes & 1px Reticles.
"""

from collections import deque
from dataclasses import dataclass
import time
from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QPainter, QColor, QRadialGradient, QPen, QBrush
from config.tokens import TOKENS

@dataclass
class ClickRipple:
    pos: QPointF
    start_time: float
    duration: float = 0.140  # 140ms fast shockwave
    max_radius: float = 24.0

class AuraShaderEngine:
    def __init__(self, history_size: int = 12):
        # Rolling position buffer for kinetic wake
        self.trail = deque(maxlen=history_size)
        self.ripples: list[ClickRipple] = []

    def push_position(self, x: float, y: float):
        """Records position and timestamp for momentum trail."""
        self.trail.append((QPointF(x, y), time.time()))

    def prune_expired(self):
        """Removes momentum trail points older than 180ms."""
        now = time.time()
        while self.trail and (now - self.trail[0][1] > 0.180):
            self.trail.popleft()

    def trigger_click_ripple(self, x: float, y: float):
        """Spawns an expanding 1px click shockwave."""
        self.ripples.append(ClickRipple(pos=QPointF(x, y), start_time=time.time()))

    def render(self, painter: QPainter, current_pos: QPointF, mode: str = "mach"):
        """
        Renders the vector wake, cursor aura, and click ripples within the dirty clip area.
        """
        now = time.time()
        self.prune_expired()
        is_mach = (mode == "mach")

        # Color configurations
        if is_mach:
            core_color = QColor(TOKENS.ACCENT_MACH)
            trail_rgb = (0, 240, 255)
            halo_radius = 28.0
        else:
            core_color = QColor(TOKENS.ACCENT_BIO)
            trail_rgb = (168, 85, 247)
            halo_radius = 22.0

        # 1. Render Tapered Directional Vector Wake
        trail_pts = list(self.trail)
        n = len(trail_pts)
        if n >= 2:
            for i in range(n - 1):
                pt_a, t_a = trail_pts[i]
                pt_b, t_b = trail_pts[i + 1]
                age = now - t_a
                if age > 0.180:  # Expire trail after 180ms
                    continue

                alpha = int(180 * (i / float(n)) * max(0.0, 1.0 - (age / 0.180)))
                stroke_width = max(1.0, 3.5 * (i / float(n)))

                pen = QPen(QColor(trail_rgb[0], trail_rgb[1], trail_rgb[2], alpha), stroke_width)
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                painter.setPen(pen)
                painter.drawLine(pt_a, pt_b)

        # 2. Render Concentric Glowing Halo (Strictly when active on screen)
        if current_pos.x() >= 0 and current_pos.y() >= 0:
            gradient = QRadialGradient(current_pos, halo_radius)
            gradient.setColorAt(0.0, QColor(255, 255, 255, 230))  # Arc White core
            gradient.setColorAt(0.25, QColor(trail_rgb[0], trail_rgb[1], trail_rgb[2], 160))
            gradient.setColorAt(0.65, QColor(trail_rgb[0], trail_rgb[1], trail_rgb[2], 30))
            gradient.setColorAt(1.0, QColor(0, 0, 0, 0))

            painter.setBrush(QBrush(gradient))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(current_pos, halo_radius, halo_radius)

            # 3. Render 1px Precision Crosshair Reticle
            reticle_pen = QPen(QColor(255, 255, 255, 220), 1.0)
            painter.setPen(reticle_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(current_pos, 7.0, 7.0)

        # 4. Render Active Click Shockwaves
        active_ripples = []
        for ripple in self.ripples:
            elapsed = now - ripple.start_time
            if elapsed < ripple.duration:
                progress = elapsed / ripple.duration
                radius = 4.0 + (ripple.max_radius - 4.0) * progress
                alpha = int(220 * (1.0 - progress))
                rip_pen = QPen(QColor(trail_rgb[0], trail_rgb[1], trail_rgb[2], alpha), 1.2)
                painter.setPen(rip_pen)
                painter.drawEllipse(ripple.pos, radius, radius)
                active_ripples.append(ripple)
        self.ripples = active_ripples
