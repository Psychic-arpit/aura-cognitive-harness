"""
aura.ui.lens - Floating Inline Cursor Lens (Spatial Cursor AI HUD)
Spawns adjacent to mouse cursor (Alt+Q / Ctrl+Shift+Space) with dynamic context telepathy.
Inspects active window, provides intelligent context-adaptive action chips,
renders streaming markdown responses inline, and enables 1-click typing back to the active window.
"""

import ctypes
from typing import Optional, Callable, List, Tuple
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QRectF
from PyQt6.QtGui import QColor, QFont, QCursor
from PyQt6.QtWidgets import (
    QWidget, QFrame, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QApplication, QTextBrowser, QGraphicsDropShadowEffect
)
from aura.agent.router import ROUTER
from aura.harness.perception import PERCEPTION
from aura.harness.actuation import ACTUATION
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
        self.latest_answer_raw = ""

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
            GLASS.enable_aero_glass(hwnd, tint_rgba=(14, 18, 26, 185))
        except Exception:
            pass

    def showEvent(self, event):
        super().showEvent(event)
        self._apply_stealth_and_glass()

    def _init_ui(self):
        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(10, 10, 10, 10)
        self.root_layout.setSpacing(0)

        # Main Aero Glass Capsule
        self.card = QFrame(self)
        self.card.setObjectName("LensFrame")
        self.card_layout = QVBoxLayout(self.card)
        self.card_layout.setContentsMargins(14, 10, 14, 10)
        self.card_layout.setSpacing(8)

        # Ambient Aerospace Glow Shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 180))
        self.card.setGraphicsEffect(shadow)

        # Top Control Row
        self.top_row = QWidget(self.card)
        self.top_layout = QHBoxLayout(self.top_row)
        self.top_layout.setContentsMargins(0, 0, 0, 0)
        self.top_layout.setSpacing(8)

        # Live Status Pulse Dot
        self.dot = QLabel(self.top_row)
        self.dot.setObjectName("LensDot")
        self.dot.setFixedSize(7, 7)

        # Context Telepathy Badge
        self.badge = QLabel("Lens", self.top_row)
        self.badge.setObjectName("LensBadge")

        # Command Input
        self.input = QLineEdit(self.top_row)
        self.input.setObjectName("LensInput")
        self.input.setPlaceholderText("Ask or execute at cursor... (Esc to dismiss)")
        self.input.returnPressed.connect(self._on_submit)

        # Esc Keycap
        self.keycap = QLabel("Esc", self.top_row)
        self.keycap.setObjectName("LensKeycap")

        self.top_layout.addWidget(self.dot)
        self.top_layout.addWidget(self.badge)
        self.top_layout.addWidget(self.input, 1)
        self.top_layout.addWidget(self.keycap)

        # Dynamic Action Chips Row
        self.chips_row = QWidget(self.card)
        self.chips_layout = QHBoxLayout(self.chips_row)
        self.chips_layout.setContentsMargins(16, 0, 0, 0)
        self.chips_layout.setSpacing(6)
        self.chip_buttons: List[QPushButton] = []

        # Inline AI Response Box
        self.resp_box = QFrame(self.card)
        self.resp_box.setObjectName("LensResponseCard")
        self.resp_layout = QVBoxLayout(self.resp_box)
        self.resp_layout.setContentsMargins(12, 10, 12, 10)
        self.resp_layout.setSpacing(8)

        self.resp_text = QTextBrowser(self.resp_box)
        self.resp_text.setObjectName("LensResponseText")
        self.resp_text.setOpenExternalLinks(True)
        self.resp_layout.addWidget(self.resp_text)

        # Response Bottom Action Bar
        self.resp_action_row = QWidget(self.resp_box)
        self.resp_action_layout = QHBoxLayout(self.resp_action_row)
        self.resp_action_layout.setContentsMargins(0, 4, 0, 0)
        self.resp_action_layout.setSpacing(8)

        self.btn_copy = QPushButton("Copy Answer", self.resp_action_row)
        self.btn_copy.setObjectName("LensActionBtn")
        self.btn_copy.clicked.connect(self._copy_answer_to_clipboard)

        self.btn_type = QPushButton("Insert at Cursor", self.resp_action_row)
        self.btn_type.setObjectName("LensActionBtnPrimary")
        self.btn_type.clicked.connect(self._type_answer_at_cursor)

        self.btn_dismiss_resp = QPushButton("Close", self.resp_action_row)
        self.btn_dismiss_resp.setObjectName("LensActionBtn")
        self.btn_dismiss_resp.clicked.connect(self.dismiss_lens)

        self.telemetry_pill = QLabel("60 FPS Compositor • Gemini 3.5 Flash", self.resp_action_row)
        self.telemetry_pill.setObjectName("LensTelemetryPill")

        self.resp_action_layout.addWidget(self.btn_copy)
        self.resp_action_layout.addWidget(self.btn_type)
        self.resp_action_layout.addWidget(self.btn_dismiss_resp)
        self.resp_action_layout.addStretch()
        self.resp_action_layout.addWidget(self.telemetry_pill)

        self.resp_layout.addWidget(self.resp_action_row)
        self.resp_box.hide()

        self.card_layout.addWidget(self.top_row)
        self.card_layout.addWidget(self.chips_row)
        self.card_layout.addWidget(self.resp_box)
        self.root_layout.addWidget(self.card)

        self.resize(460, 85)

    def _clear_chips(self):
        for btn in self.chip_buttons:
            btn.deleteLater()
        self.chip_buttons.clear()

    def _set_chips(self, chips: List[Tuple[str, str]]):
        self._clear_chips()
        for label, cmd in chips:
            btn = QPushButton(label, self.chips_row)
            btn.setObjectName("LensChip")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, c=cmd: self._on_chip_clicked(c))
            self.chips_layout.addWidget(btn)
            self.chip_buttons.append(btn)
        self.chips_layout.addStretch()

    def _on_chip_clicked(self, cmd: str):
        self.input.setText(cmd)
        self._on_submit()

    def _on_submit(self):
        text = self.input.text().strip()
        if text:
            # Show inline loading state immediately
            self.resp_box.show()
            self.resp_text.clear()
            self.resp_text.setHtml("<span style='color: #38BDF8;'>⚡ Aura Intelligence processing at cursor...</span>")
            self.resize(480, 240)
            self.command_submitted.emit(text)

    def _copy_answer_to_clipboard(self):
        if self.latest_answer_raw:
            app = QApplication.instance()
            if app:
                app.clipboard().setText(self.latest_answer_raw)
                self.btn_copy.setText("Copied!")
                QTimer.singleShot(1500, lambda: self.btn_copy.setText("Copy Answer"))

    def _type_answer_at_cursor(self):
        """Dismisses the lens, restores focus to target window, and synthesizes hardware keystrokes."""
        if not self.latest_answer_raw:
            return
        content = self.latest_answer_raw
        self.dismiss_lens()

        # Brief delay to allow target window focus restoration
        def do_type():
            ACTUATION.fast_type(content)

        QTimer.singleShot(120, do_type)

    def _update_styles(self):
        self.card.setStyleSheet("""
            QFrame#LensFrame {
                background-color: rgba(14, 18, 26, 0.78);
                border: 1px solid rgba(255, 255, 255, 0.14);
                border-top: 1px solid rgba(255, 255, 255, 0.38);
                border-radius: 12px;
            }
            QLabel#LensDot {
                background-color: #38BDF8;
                border-radius: 3.5px;
            }
            QLabel#LensBadge {
                background-color: rgba(56, 189, 248, 0.12);
                border: 1px solid rgba(56, 189, 248, 0.30);
                border-radius: 4px;
                color: #38BDF8;
                font-family: -apple-system, 'Segoe UI Variable Display', 'Segoe UI', Inter, sans-serif;
                font-size: 10px;
                font-weight: 600;
                padding: 1px 6px;
                text-transform: uppercase;
            }
            QLineEdit#LensInput {
                background: transparent;
                border: none;
                color: #FFFFFF;
                font-family: -apple-system, 'Segoe UI Variable Display', 'Segoe UI', Inter, sans-serif;
                font-size: 13px;
                font-weight: 400;
                padding: 1px 4px;
                selection-background-color: rgba(56, 189, 248, 0.35);
                selection-color: #FFFFFF;
            }
            QLabel#LensKeycap {
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.14);
                border-radius: 4px;
                color: rgba(255, 255, 255, 0.55);
                font-family: -apple-system, 'Segoe UI', monospace;
                font-size: 9.5px;
                font-weight: 500;
                padding: 2px 5px;
            }
            QPushButton#LensChip {
                background-color: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.10);
                border-top: 1px solid rgba(255, 255, 255, 0.20);
                border-radius: 5px;
                color: rgba(255, 255, 255, 0.78);
                font-family: -apple-system, 'Segoe UI Variable Text', 'Segoe UI', Inter, sans-serif;
                font-size: 11px;
                padding: 3px 9px;
            }
            QPushButton#LensChip:hover {
                background-color: rgba(56, 189, 248, 0.18);
                border-color: rgba(56, 189, 248, 0.40);
                color: #FFFFFF;
            }
            QFrame#LensResponseCard {
                background-color: rgba(10, 14, 20, 0.82);
                border: 1px solid rgba(255, 255, 255, 0.10);
                border-radius: 8px;
            }
            QTextBrowser#LensResponseText {
                background: transparent;
                border: none;
                color: #F8FAFC;
                font-family: -apple-system, 'Segoe UI Variable Text', 'Segoe UI', Inter, sans-serif;
                font-size: 12px;
                line-height: 1.5;
            }
            QPushButton#LensActionBtn {
                background-color: rgba(255, 255, 255, 0.07);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 4px;
                color: rgba(255, 255, 255, 0.80);
                font-family: -apple-system, 'Segoe UI', Inter, sans-serif;
                font-size: 10.5px;
                padding: 3px 8px;
            }
            QPushButton#LensActionBtn:hover {
                background-color: rgba(255, 255, 255, 0.15);
                color: #FFFFFF;
            }
            QPushButton#LensActionBtnPrimary {
                background-color: rgba(56, 189, 248, 0.20);
                border: 1px solid rgba(56, 189, 248, 0.45);
                border-radius: 4px;
                color: #38BDF8;
                font-family: -apple-system, 'Segoe UI', Inter, sans-serif;
                font-size: 10.5px;
                font-weight: 600;
                padding: 3px 8px;
            }
            QPushButton#LensActionBtnPrimary:hover {
                background-color: rgba(56, 189, 248, 0.35);
                color: #FFFFFF;
            }
            QLabel#LensTelemetryPill {
                color: rgba(255, 255, 255, 0.35);
                font-family: -apple-system, 'Segoe UI', monospace;
                font-size: 9px;
            }
        """)

    def summon_at_cursor(self):
        """Spawns the Lens adjacent to current cursor with live context telepathy."""
        self.previous_hwnd = user32.GetForegroundWindow()

        pt = (ctypes.c_long * 2)()
        user32.GetCursorPos(pt)
        cx, cy = pt[0], pt[1]

        # 1. Inspect active foreground context
        fg = PERCEPTION.get_foreground_window()
        proc = fg.get("process", "unknown").lower()
        title = fg.get("title", "")
        category = fg.get("category", "general")

        # Context badge labeling
        if "code" in proc or "devenv" in proc:
            self.badge.setText("VS Code")
            chips = [
                ("Explain Code", "@clip explain this code"),
                ("Refactor & Clean", "@clip refactor and clean this"),
                ("Find Bugs", "@clip analyze edge cases and bugs"),
                ("Git Diff", "@git")
            ]
        elif "spotify" in proc or "spotify" in title.lower():
            self.badge.setText("Spotify")
            chips = [
                ("Play / Pause", "play"),
                ("Next Track", "next"),
                ("Volume +20%", "volume up"),
                ("Play Lo-Fi", "play lofi on spotify")
            ]
        elif any(b in proc for b in ("chrome", "msedge", "firefox", "brave")):
            self.badge.setText("Browser")
            chips = [
                ("Summarize Page", "@screen summarize this page"),
                ("Extract Text", "@clip clean formatted text"),
                ("Web Vision", "@screen explain what is shown"),
                ("Google Search", "search leetcode two sum")
            ]
        elif any(t in proc for t in ("cmd", "powershell", "windowsterminal", "wt")):
            self.badge.setText("Terminal")
            chips = [
                ("Diagnose Error", "@clip diagnose and fix terminal error"),
                ("Git Status", "@git"),
                ("Clean Cache", "clean temp"),
                ("Run Fast", "> git status")
            ]
        else:
            clean_name = proc.replace(".exe", "")[:8]
            self.badge.setText(clean_name.upper() if clean_name not in ("explorer", "system", "unknown") else "Lens")
            chips = [
                ("Screen Vision", "@screen what is on my screen?"),
                ("Clipboard AI", "@clip explain clipboard content"),
                ("Paint Shape", "draw rectangle in paint"),
                ("TagRush QA", "test tagrush")
            ]

        self._set_chips(chips)

        # 2. Position Lens with smart screen edge clamping
        screen = QApplication.primaryScreen().geometry()
        w = 460
        h = 85

        x = cx + 18
        y = cy + 18

        # Clamp right edge
        if x + w > screen.width() - 16:
            x = cx - w - 12
        # Clamp bottom edge
        if y + h > screen.height() - 48:
            y = cy - h - 12

        self.resize(w, h)
        self.move(int(x), int(y))
        self.resp_box.hide()
        self.show()
        self.activateWindow()
        self.input.clear()
        self.input.setFocus()

    def dismiss_lens(self):
        self._typewriter_timer.stop()
        self.resp_box.hide()
        self.input.clear()
        self.resize(460, 85)
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
        """Streams AI answer directly inside the floating cursor lens."""
        self.latest_answer_raw = answer
        self.resp_text.clear()
        self.resp_box.show()
        self.resize(480, 260)
        self._target_markdown = answer
        self._stream_index = 0
        self._typewriter_timer.start(8)

    def _on_typewriter_tick(self):
        chunk_size = max(8, len(self._target_markdown) // 25)
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
