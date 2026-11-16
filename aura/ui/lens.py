"""
aura.ui.lens - Floating Inline Cursor Lens (Cursor AI HUD)
Instant context palette summoned directly adjacent to mouse cursor (Alt+Q).
Inspects active editor selection, executes visual UI clicks, runs shell commands,
and streams AI responses without shifting user attention away from the cursor.
"""

import ctypes
from typing import Optional, Callable
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QWidget, QFrame, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QApplication, QTextBrowser, QGraphicsDropShadowEffect
)
from aura.agent.router import ROUTER
from aura.harness.perception import PERCEPTION
from aura.harness.stealth import STEALTH
from aura.harness.glass import GLASS

user32 = ctypes.WinDLL("user32", use_last_error=True)

class CursorLens(QWidget):
    command_submitted = pyqtSignal(str)
    dismissed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.previous_hwnd = None
        self._typewriter_timer = QTimer(self)
        self._typewriter_timer.timeout.connect(self._on_typewriter_tick)
        self._target_markdown = ""
        self._stream_index = 0

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self._init_ui()
        self._apply_stealth_and_glass()
        self._update_styles()

    def _apply_stealth_and_glass(self):
        try:
            hwnd = int(self.winId())
            STEALTH.apply_stream_invisibility(hwnd)
            GLASS.enable_aero_glass(hwnd, tint_rgba=(16, 20, 28, 175))
        except Exception:
            pass

    def showEvent(self, event):
        super().showEvent(event)
        self._apply_stealth_and_glass()

    def _init_ui(self):
        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(10, 10, 10, 10)
        self.root_layout.setSpacing(0)

        # Main Aero Glass Card
        self.card = QFrame(self)
        self.card.setObjectName("LensFrame")
        self.card_layout = QVBoxLayout(self.card)
        self.card_layout.setContentsMargins(12, 8, 12, 8)
        self.card_layout.setSpacing(6)

        # Ambient Drop Shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(0, 0, 0, 160))
        self.card.setGraphicsEffect(shadow)

        # Top Control Row
        self.top_row = QWidget(self.card)
        self.top_layout = QHBoxLayout(self.top_row)
        self.top_layout.setContentsMargins(0, 0, 0, 0)
        self.top_layout.setSpacing(8)

        # Status Dot
        self.dot = QLabel(self.top_row)
        self.dot.setObjectName("LensDot")
        self.dot.setFixedSize(6, 6)

        # Active App Context Badge
        self.badge = QLabel("Lens", self.top_row)
        self.badge.setObjectName("LensBadge")

        # Command Input
        self.input = QLineEdit(self.top_row)
        self.input.setObjectName("LensInput")
        self.input.setPlaceholderText("Ask or execute at cursor... (Esc to dismiss)")
        self.input.returnPressed.connect(self._on_submit)

        # Keycap
        self.keycap = QLabel("Esc", self.top_row)
        self.keycap.setObjectName("LensKeycap")

        self.top_layout.addWidget(self.dot)
        self.top_layout.addWidget(self.badge)
        self.top_layout.addWidget(self.input, 1)
        self.top_layout.addWidget(self.keycap)

        # Action Chips Row
        self.chips_row = QWidget(self.card)
        self.chips_layout = QHBoxLayout(self.chips_row)
        self.chips_layout.setContentsMargins(14, 0, 0, 2)
        self.chips_layout.setSpacing(6)

        self.chip_explain = self._create_chip("Explain", "explain this")
        self.chip_fix = self._create_chip("Fix / Code", "help me fix this error")
        self.chip_click = self._create_chip("Click Target", "click target")
        self.chip_shell = self._create_chip("Shell", "> git status")

        self.chips_layout.addWidget(self.chip_explain)
        self.chips_layout.addWidget(self.chip_fix)
        self.chips_layout.addWidget(self.chip_click)
        self.chips_layout.addWidget(self.chip_shell)
        self.chips_layout.addStretch()

        # Inline AI Response Box
        self.resp_box = QFrame(self.card)
        self.resp_box.setObjectName("LensResponseCard")
        self.resp_layout = QVBoxLayout(self.resp_box)
        self.resp_layout.setContentsMargins(10, 8, 10, 8)
        self.resp_layout.setSpacing(4)

        self.resp_text = QTextBrowser(self.resp_box)
        self.resp_text.setObjectName("LensResponseText")
        self.resp_text.setOpenExternalLinks(True)
        self.resp_layout.addWidget(self.resp_text)
        self.resp_box.hide()

        self.card_layout.addWidget(self.top_row)
        self.card_layout.addWidget(self.chips_row)
        self.card_layout.addWidget(self.resp_box)
        self.root_layout.addWidget(self.card)

        self.resize(420, 80)

    def _create_chip(self, label: str, cmd: str) -> QPushButton:
        btn = QPushButton(label, self.chips_row)
        btn.setObjectName("LensChip")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(lambda: self._on_chip_clicked(cmd))
        return btn

    def _on_chip_clicked(self, cmd: str):
        self.dismiss_lens()
        self.command_submitted.emit(cmd)

    def _on_submit(self):
        text = self.input.text().strip()
        if text:
            self.dismiss_lens()
            self.command_submitted.emit(text)

    def _update_styles(self):
        self.card.setStyleSheet("""
            QFrame#LensFrame {
                background-color: rgba(18, 22, 30, 0.72);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-top: 1px solid rgba(255, 255, 255, 0.30);
                border-radius: 12px;
            }
            QLabel#LensDot {
                background-color: #22C55E;
                border-radius: 3px;
            }
            QLabel#LensBadge {
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.14);
                border-radius: 4px;
                color: rgba(255, 255, 255, 0.90);
                font-family: -apple-system, 'Segoe UI', Inter, sans-serif;
                font-size: 10px;
                font-weight: 500;
                padding: 1px 5px;
            }
            QLineEdit#LensInput {
                background: transparent;
                border: none;
                color: #FFFFFF;
                font-family: -apple-system, 'Segoe UI Variable Display', 'Segoe UI', Inter, sans-serif;
                font-size: 12.5px;
                padding: 0px 2px;
                selection-background-color: rgba(255, 255, 255, 0.20);
                selection-color: #FFFFFF;
            }
            QLabel#LensKeycap {
                background-color: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.10);
                border-radius: 4px;
                color: rgba(255, 255, 255, 0.45);
                font-family: -apple-system, 'Segoe UI', monospace;
                font-size: 9.5px;
                padding: 1px 5px;
            }
            QPushButton#LensChip {
                background-color: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.09);
                border-top: 1px solid rgba(255, 255, 255, 0.16);
                border-radius: 5px;
                color: rgba(255, 255, 255, 0.70);
                font-family: -apple-system, 'Segoe UI', Inter, sans-serif;
                font-size: 10.5px;
                padding: 3px 8px;
            }
            QPushButton#LensChip:hover {
                background-color: rgba(255, 255, 255, 0.12);
                border-color: rgba(255, 255, 255, 0.22);
                color: #FFFFFF;
            }
            QFrame#LensResponseCard {
                background-color: rgba(14, 18, 24, 0.75);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
            }
            QTextBrowser#LensResponseText {
                background: transparent;
                border: none;
                color: #F1F5F9;
                font-family: -apple-system, 'Segoe UI Variable Text', 'Segoe UI', Inter, sans-serif;
                font-size: 12px;
                line-height: 1.5;
            }
        """)

    def summon_at_cursor(self):
        """Spawns the Lens adjacent to current cursor with smart screen edge clamping."""
        self.previous_hwnd = user32.GetForegroundWindow()

        pt = (ctypes.c_long * 2)()
        user32.GetCursorPos(pt)
        cx, cy = pt[0], pt[1]

        # Ingest active foreground context
        fg = PERCEPTION.get_foreground_window()
        proc = fg["process"]
        if proc not in ["explorer.exe", "system", "unknown"]:
            self.badge.setText(proc.replace(".exe", "")[:10])
        else:
            self.badge.setText("Lens")

        # Reposition with screen edge clamping
        screen = QApplication.primaryScreen().geometry()
        w = self.width()
        h = self.height()

        x = cx + 18
        y = cy + 18

        # Clamp right edge
        if x + w > screen.width() - 16:
            x = cx - w - 12
        # Clamp bottom edge
        if y + h > screen.height() - 48:
            y = cy - h - 12

        self.move(int(x), int(y))
        self.show()
        self.activateWindow()
        self.input.clear()
        self.input.setFocus()

    def dismiss_lens(self):
        self._typewriter_timer.stop()
        self.resp_box.hide()
        self.input.clear()
        self.hide()
        self.dismissed.emit()

        if self.previous_hwnd:
            try:
                if user32.IsWindow(self.previous_hwnd):
                    user32.SetForegroundWindow(self.previous_hwnd)
            except Exception:
                pass
            self.previous_hwnd = None

    def show_inline_answer(self, answer: str):
        self.resp_text.clear()
        self.resp_box.show()
        self.resize(460, 240)
        self._target_markdown = answer
        self._stream_index = 0
        self._typewriter_timer.start(10)

    def _on_typewriter_tick(self):
        chunk_size = max(6, len(self._target_markdown) // 30)
        self._stream_index = min(len(self._target_markdown), self._stream_index + chunk_size)
        curr = self._target_markdown[:self._stream_index]
        self.resp_text.setMarkdown(curr)

        if self._stream_index >= len(self._target_markdown):
            self._typewriter_timer.stop()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.dismiss_lens()
        else:
            super().keyPressEvent(event)
