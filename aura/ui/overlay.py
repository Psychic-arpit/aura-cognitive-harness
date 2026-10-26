"""
aura.ui.overlay - Stream-Invisible Ghost Visual Telemetry Overlay
Renders real-time subtle glass cursor trails, target lock crosshairs, and click ripples at 60 FPS.
Passes through all mouse input (WA_TransparentForMouseEvents) and shielded via WDA_EXCLUDEFROMCAPTURE.
"""

import time
from collections import deque
from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush
from PyQt6.QtWidgets import QWidget, QApplication
from aura.harness.stealth import STEALTH

class AuraOverlayWindow(QWidget):
    def __init__(self, mode: str = "mach"):
        super().__init__()
        self.mode = mode
        self.trail = deque(maxlen=20)
        self.click_ripples = []
        self.target_crosshair = None

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

    def update_telemetry(self, x: float, y: float):
        self.trail.append((x, y, time.time()))

    def trigger_click(self, x: float, y: float):
        self.click_ripples.append({"x": x, "y": y, "radius": 4.0, "alpha": 200})

    def lock_target(self, x: float, y: float):
        self.target_crosshair = (x, y)

    def clear_overlay(self):
        self.trail.clear()
        self.click_ripples.clear()
        self.target_crosshair = None

    def _tick(self):
        now = time.time()
        while self.trail and (now - self.trail[0][2]) > 0.35:
            self.trail.popleft()

        active_ripples = []
        for r in self.click_ripples:
            r["radius"] += 3.0
            r["alpha"] -= 16
            if r["alpha"] > 0 and r["radius"] < 50:
                active_ripples.append(r)
        self.click_ripples = active_ripples

        if self.trail or self.click_ripples or self.target_crosshair:
            self.update()

    def paintEvent(self, event):
        if not self.trail and not self.click_ripples and not self.target_crosshair:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 1. Subtle frosted white glass trail
        if len(self.trail) > 1:
            pts = list(self.trail)
            for i in range(len(pts) - 1):
                x1, y1, _ = pts[i]
                x2, y2, _ = pts[i + 1]
                progress = (i + 1) / len(pts)
                alpha = int(140 * progress)
                color = QColor(255, 255, 255, alpha)
                pen = QPen(color, 2.0 + progress * 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
                painter.setPen(pen)
                painter.drawLine(int(x1), int(y1), int(x2), int(y2))

        # 2. Subtle frosted glass ripples
        for r in self.click_ripples:
            color = QColor(255, 255, 255, int(r["alpha"]))
            painter.setPen(QPen(color, 1.5))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            rad = r["radius"]
            painter.drawEllipse(QRectF(r["x"] - rad, r["y"] - rad, rad * 2, rad * 2))

        # 3. Minimalist crosshair
        if self.target_crosshair:
            tx, ty = self.target_crosshair
            pen = QPen(QColor(255, 255, 255, 180), 1.0)
            painter.setPen(pen)
            painter.drawEllipse(QRectF(tx - 10, ty - 10, 20, 20))
            painter.drawLine(int(tx - 14), int(ty), int(tx + 14), int(ty))
            painter.drawLine(int(tx), int(ty - 14), int(tx), int(ty + 14))

        painter.end()
