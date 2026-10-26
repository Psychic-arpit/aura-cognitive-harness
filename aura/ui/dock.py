"""
aura.ui.dock - Authentic Aero Glassmorphic Cyber-Dock
Hardware DWM Acrylic blur-behind, specular glass bevels, and distraction-free typography.
Zero emojis, zero AI buzzwords, pure minimal glass aesthetics.
"""

import ctypes
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

class CyberDock(QWidget):
    command_submitted = pyqtSignal(str)
    mode_toggled = pyqtSignal(str)
    minimized_to_tray = pyqtSignal()

    def __init__(self, default_mode: str = "mach"):
        super().__init__()
        self.mode = default_mode
        self.is_expanded = False
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
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        self._init_ui()
        self._apply_stealth_and_glass()
        self._update_styles()
        self._reposition()

    def _apply_stealth_and_glass(self):
        try:
            hwnd = int(self.winId())
            STEALTH.apply_stream_invisibility(hwnd)
            GLASS.enable_aero_glass(hwnd, tint_rgba=(18, 22, 30, 160))
        except Exception:
            pass

    def showEvent(self, event):
        super().showEvent(event)
        self._apply_stealth_and_glass()
        self._reposition()

    def _init_ui(self):
        self.window_layout = QVBoxLayout(self)
        self.window_layout.setContentsMargins(12, 12, 12, 12)
        self.window_layout.setSpacing(0)

        # Main Aero Glass Card Frame
        self.card = QFrame(self)
        self.card.setObjectName("GlassFrame")
        self.card_layout = QVBoxLayout(self.card)
        self.card_layout.setContentsMargins(14, 8, 14, 8)
        self.card_layout.setSpacing(6)

        # Ambient Drop Shadow for floating glass feel
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 140))
        self.card.setGraphicsEffect(shadow)

        # Top Control & Input Bar
        self.top_row = QWidget(self.card)
        self.top_layout = QHBoxLayout(self.top_row)
        self.top_layout.setContentsMargins(0, 0, 0, 0)
        self.top_layout.setSpacing(10)

        # 1. Subtle Status Pip
        self.status_dot = QLabel(self.top_row)
        self.status_dot.setObjectName("StatusDot")
        self.status_dot.setFixedSize(6, 6)

        # 2. Ambient Idle Context Text
        self.context_label = QLabel("Search or type a command...", self.top_row)
        self.context_label.setObjectName("ContextLabel")

        # 3. Command Input Field (Visible when expanded)
        self.input_field = QLineEdit(self.top_row)
        self.input_field.setObjectName("InputField")
        self.input_field.setPlaceholderText("Search, execute command, or paste code...")
        self.input_field.returnPressed.connect(self._on_submit)
        self.input_field.textChanged.connect(self._on_text_changed)
        self.input_field.hide()

        # 4. Minimalist Action Type Badge
        self.action_badge = QLabel("Run", self.top_row)
        self.action_badge.setObjectName("ActionBadge")
        self.action_badge.hide()

        # 5. Keycap Indicator
        self.keycap_label = QLabel("Alt+C", self.top_row)
        self.keycap_label.setObjectName("KeycapLabel")

        # 6. Minimize to Tray Button
        self.tray_btn = QPushButton("—", self.top_row)
        self.tray_btn.setObjectName("WindowBtn")
        self.tray_btn.setToolTip("Minimize to Tray")
        self.tray_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tray_btn.clicked.connect(self.hide_to_tray)
        self.tray_btn.hide()

        # 7. Dismiss Button
        self.dismiss_btn = QPushButton("×", self.top_row)
        self.dismiss_btn.setObjectName("WindowBtn")
        self.dismiss_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.dismiss_btn.clicked.connect(self.collapse_capsule)
        self.dismiss_btn.hide()

        self.top_layout.addWidget(self.status_dot)
        self.top_layout.addWidget(self.context_label, 1)
        self.top_layout.addWidget(self.input_field, 1)
        self.top_layout.addWidget(self.action_badge)
        self.top_layout.addWidget(self.keycap_label)
        self.top_layout.addWidget(self.tray_btn)
        self.top_layout.addWidget(self.dismiss_btn)

        # Frosted Glass Action Chips Row
        self.chips_row = QWidget(self.card)
        self.chips_layout = QHBoxLayout(self.chips_row)
        self.chips_layout.setContentsMargins(16, 2, 0, 4)
        self.chips_layout.setSpacing(8)

        self.chip_tagrush = self._create_chip("TagRush QA", "test tagrush")
        self.chip_shorts = self._create_chip("YouTube Shorts", "play youtube shorts")
        self.chip_explain = self._create_chip("Explain Code", "explain this code")
        self.chip_clean = self._create_chip("Clean Cache", "clean temp")

        self.chips_layout.addWidget(self.chip_tagrush)
        self.chips_layout.addWidget(self.chip_shorts)
        self.chips_layout.addWidget(self.chip_explain)
        self.chips_layout.addWidget(self.chip_clean)
        self.chips_layout.addStretch()
        self.chips_row.hide()

        # Aero Glass Response Viewport
        self.ai_card = QFrame(self.card)
        self.ai_card.setObjectName("ResponseCard")
        self.ai_layout = QVBoxLayout(self.ai_card)
        self.ai_layout.setContentsMargins(14, 10, 14, 10)
        self.ai_layout.setSpacing(6)

        self.ai_header = QWidget(self.ai_card)
        self.ai_header_layout = QHBoxLayout(self.ai_header)
        self.ai_header_layout.setContentsMargins(0, 0, 0, 0)

        self.ai_source_lbl = QLabel("RESPONSE", self.ai_header)
        self.ai_source_lbl.setObjectName("ResponseHeaderLabel")
        self.ai_header_layout.addWidget(self.ai_source_lbl)
        self.ai_header_layout.addStretch()

        self.btn_copy = QPushButton("Copy", self.ai_header)
        self.btn_copy.setObjectName("GlassPillBtn")
        self.btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy.clicked.connect(self._copy_answer)
        self.ai_header_layout.addWidget(self.btn_copy)

        self.btn_close_ai = QPushButton("×", self.ai_header)
        self.btn_close_ai.setObjectName("GlassCloseBtn")
        self.btn_close_ai.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close_ai.clicked.connect(self.hide_ai_card)
        self.ai_header_layout.addWidget(self.btn_close_ai)

        self.ai_layout.addWidget(self.ai_header)

        self.ai_text = QTextBrowser(self.ai_card)
        self.ai_text.setObjectName("ResponseText")
        self.ai_text.setOpenExternalLinks(True)
        self.ai_layout.addWidget(self.ai_text)
        self.ai_card.hide()

        self.card_layout.addWidget(self.top_row)
        self.card_layout.addWidget(self.chips_row)
        self.card_layout.addWidget(self.ai_card)
        self.window_layout.addWidget(self.card)

        self.card.setCursor(Qt.CursorShape.PointingHandCursor)
        self.resize(360, 52)

    def _create_chip(self, label: str, command: str) -> QPushButton:
        btn = QPushButton(label, self.chips_row)
        btn.setObjectName("GlassChip")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(lambda: self._on_chip_clicked(command))
        return btn

    def _on_chip_clicked(self, command: str):
        self.collapse_capsule()
        self.command_submitted.emit(command)

    def _update_styles(self):
        self.card.setStyleSheet("""
            QFrame#GlassFrame {
                background-color: rgba(20, 24, 32, 0.55);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-top: 1px solid rgba(255, 255, 255, 0.28);
                border-radius: 14px;
            }
            QLabel#StatusDot {
                background-color: #22C55E;
                border-radius: 3px;
            }
            QLabel#ContextLabel {
                color: rgba(255, 255, 255, 0.55);
                font-family: -apple-system, 'Segoe UI Variable Display', 'Segoe UI', Inter, sans-serif;
                font-size: 12px;
                font-weight: 400;
            }
            QLabel#KeycapLabel {
                background-color: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.10);
                border-radius: 4px;
                color: rgba(255, 255, 255, 0.50);
                font-family: -apple-system, 'Segoe UI', monospace;
                font-size: 10px;
                font-weight: 500;
                padding: 2px 6px;
            }
            QLabel#ActionBadge {
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.14);
                border-radius: 4px;
                color: #FFFFFF;
                font-family: -apple-system, 'Segoe UI', sans-serif;
                font-size: 10px;
                font-weight: 500;
                padding: 2px 6px;
            }
            QLineEdit#InputField {
                background: transparent;
                border: none;
                color: #FFFFFF;
                font-family: -apple-system, 'Segoe UI Variable Display', 'Segoe UI', Inter, sans-serif;
                font-size: 13.5px;
                font-weight: 400;
                padding: 0px 4px;
                selection-background-color: rgba(255, 255, 255, 0.20);
                selection-color: #FFFFFF;
            }
            QPushButton#WindowBtn {
                background: transparent;
                border: none;
                color: rgba(255, 255, 255, 0.40);
                font-size: 13px;
                font-weight: 300;
                padding: 0px 4px;
            }
            QPushButton#WindowBtn:hover {
                color: #FFFFFF;
            }
            QPushButton#GlassChip {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.09);
                border-top: 1px solid rgba(255, 255, 255, 0.18);
                border-radius: 6px;
                color: rgba(255, 255, 255, 0.65);
                font-family: -apple-system, 'Segoe UI', Inter, sans-serif;
                font-size: 11px;
                font-weight: 400;
                padding: 4px 10px;
            }
            QPushButton#GlassChip:hover {
                background-color: rgba(255, 255, 255, 0.11);
                border-color: rgba(255, 255, 255, 0.20);
                color: #FFFFFF;
            }
            QFrame#ResponseCard {
                background-color: rgba(16, 20, 28, 0.65);
                border: 1px solid rgba(255, 255, 255, 0.09);
                border-top: 1px solid rgba(255, 255, 255, 0.20);
                border-radius: 10px;
            }
            QLabel#ResponseHeaderLabel {
                color: rgba(255, 255, 255, 0.50);
                font-family: -apple-system, 'Segoe UI', monospace;
                font-size: 10px;
                font-weight: 600;
                letter-spacing: 0.8px;
            }
            QTextBrowser#ResponseText {
                background: transparent;
                border: none;
                color: #F1F5F9;
                font-family: -apple-system, 'Segoe UI Variable Text', 'Segoe UI', Inter, sans-serif;
                font-size: 12.5px;
                line-height: 1.55;
            }
            QPushButton#GlassPillBtn {
                background-color: rgba(255, 255, 255, 0.07);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 4px;
                color: rgba(255, 255, 255, 0.70);
                font-size: 10px;
                font-weight: 500;
                padding: 2px 8px;
            }
            QPushButton#GlassPillBtn:hover {
                border-color: rgba(255, 255, 255, 0.25);
                color: #FFFFFF;
                background-color: rgba(255, 255, 255, 0.12);
            }
            QPushButton#GlassCloseBtn {
                background: transparent;
                border: none;
                color: rgba(255, 255, 255, 0.40);
                font-size: 13px;
                font-weight: 300;
                padding: 0px 4px;
            }
            QPushButton#GlassCloseBtn:hover {
                color: #EF4444;
            }
        """)

    def _reposition(self):
        screen = QApplication.primaryScreen().geometry()
        x = int((screen.width() - self.width()) / 2)
        y = int(screen.height() - self.height() - 16)
        self.move(x, y)

    def set_status(self, text: str, is_active: bool = False):
        clean = text.strip()
        if len(clean) > 36:
            clean = clean[:36] + "..."
        if is_active:
            self.status_dot.setStyleSheet("background-color: #F59E0B; border-radius: 3px;")
            self.context_label.setText(clean)
        else:
            self.status_dot.setStyleSheet("background-color: #22C55E; border-radius: 3px;")
            self.context_label.setText("Search or type a command...")

    def toggle_expand(self):
        if self.isHidden():
            self.show()
            self.expand_capsule()
        elif self.is_expanded:
            self.collapse_capsule()
        else:
            self.expand_capsule()

    def hide_to_tray(self):
        self.collapse_capsule()
        self.hide()
        self.minimized_to_tray.emit()

    def expand_capsule(self):
        if self.isHidden():
            self.show()
        if self.is_expanded:
            return

        self.previous_hwnd = user32.GetForegroundWindow()
        self.is_expanded = True

        self.context_label.hide()
        self.input_field.show()
        self.action_badge.show()
        self.keycap_label.setText("Esc")
        self.tray_btn.show()
        self.dismiss_btn.show()
        self.chips_row.show()

        fg = PERCEPTION.get_foreground_window()
        if fg["process"] not in ["explorer.exe", "system"]:
            self.action_badge.setText(fg["process"][:12])

        self.card.setCursor(Qt.CursorShape.ArrowCursor)
        self.resize(700, 84)
        self._reposition()

        self.activateWindow()
        self.input_field.setFocus()

    def collapse_capsule(self):
        if not self.is_expanded:
            return
        self._typewriter_timer.stop()
        self.is_expanded = False
        self.ai_card.hide()
        self.input_field.clear()
        self.input_field.hide()
        self.action_badge.hide()
        self.keycap_label.setText("Alt+C")
        self.tray_btn.hide()
        self.dismiss_btn.hide()
        self.chips_row.hide()
        self.context_label.show()

        self.card.setCursor(Qt.CursorShape.PointingHandCursor)
        self.resize(360, 52)
        self._reposition()

        if self.previous_hwnd:
            try:
                if user32.IsWindow(self.previous_hwnd):
                    user32.SetForegroundWindow(self.previous_hwnd)
            except Exception:
                pass
            self.previous_hwnd = None

    def _on_text_changed(self, text: str):
        label = ROUTER.get_preview(text)
        self.action_badge.setText(label if label else "Run")

    def show_ai_answer(self, data: dict):
        self.current_answer = data.get("answer", "")

        self.is_expanded = True
        self.context_label.hide()
        self.input_field.show()
        self.action_badge.show()
        self.action_badge.setText("Ready")
        self.keycap_label.setText("Esc")
        self.tray_btn.show()
        self.dismiss_btn.show()
        self.chips_row.hide()
        self.ai_card.show()

        self.card.setCursor(Qt.CursorShape.ArrowCursor)
        self.resize(700, 310)
        self._reposition()
        self.activateWindow()

        # Render Markdown cleanly
        self._target_markdown = self.current_answer
        self._stream_index = 0
        self.ai_text.clear()
        self._typewriter_timer.start(10)

    def _on_typewriter_tick(self):
        chunk_size = max(5, len(self._target_markdown) // 35)
        self._stream_index += chunk_size
        if self._stream_index >= len(self._target_markdown):
            self._typewriter_timer.stop()
            self.ai_text.setMarkdown(self._target_markdown)
        else:
            self.ai_text.setMarkdown(self._target_markdown[:self._stream_index] + " ▌")

    def hide_ai_card(self):
        self._typewriter_timer.stop()
        self.ai_card.hide()
        if self.is_expanded:
            self.resize(700, 84)
            self.chips_row.show()
            self._reposition()
            self.input_field.setFocus()
        else:
            self.collapse_capsule()

    def _copy_answer(self):
        if hasattr(self, "current_answer") and self.current_answer:
            QApplication.clipboard().setText(self.current_answer)
            self.btn_copy.setText("Copied")
            QTimer.singleShot(1500, lambda: self.btn_copy.setText("Copy"))

    def mousePressEvent(self, event):
        if not self.is_expanded and event.button() == Qt.MouseButton.LeftButton:
            self.expand_capsule()
        else:
            super().mousePressEvent(event)

    def _on_submit(self):
        cmd = self.input_field.text().strip()
        if not cmd:
            return
        intent = ROUTER.route(cmd)
        if intent.type in ["context_ai", "math_eval"]:
            self.action_badge.setText("Thinking...")
            self.command_submitted.emit(cmd)
        else:
            self.collapse_capsule()
            self.command_submitted.emit(cmd)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            if self.ai_card.isVisible():
                self.hide_ai_card()
            else:
                self.hide_to_tray()
        else:
            super().keyPressEvent(event)
