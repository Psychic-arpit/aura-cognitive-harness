"""
aura.ui.dock - The Cyber-Dock Viewport
Positioned at bottom center of desktop (above taskbar).
100% Stream-Invisible via Win32 WDA_EXCLUDEFROMCAPTURE (0x11).
Expands upwards, collapses into Windows System Tray, renders live Markdown AI responses.
"""

import ctypes
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtWidgets import (
    QWidget, QFrame, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QApplication, QTextBrowser
)
from aura.agent.router import ROUTER
from aura.harness.perception import PERCEPTION
from aura.harness.stealth import STEALTH

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

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        self._init_ui()
        self._update_styles()
        self._apply_stealth()
        self._reposition()

    def _apply_stealth(self):
        try:
            hwnd = int(self.winId())
            STEALTH.apply_stream_invisibility(hwnd)
        except Exception:
            pass

    def showEvent(self, event):
        super().showEvent(event)
        self._apply_stealth()
        self._reposition()

    def _init_ui(self):
        self.window_layout = QVBoxLayout(self)
        self.window_layout.setContentsMargins(4, 4, 4, 4)
        self.window_layout.setSpacing(0)

        # Main Card Frame
        self.card = QFrame(self)
        self.card.setObjectName("CyberCard")
        self.card_layout = QVBoxLayout(self.card)
        self.card_layout.setContentsMargins(12, 6, 12, 6)
        self.card_layout.setSpacing(6)

        # Top Control & Input Bar
        self.top_row = QWidget(self.card)
        self.top_layout = QHBoxLayout(self.top_row)
        self.top_layout.setContentsMargins(0, 0, 0, 0)
        self.top_layout.setSpacing(8)

        # 1. Status Neon Pip
        self.status_dot = QLabel("●", self.top_row)
        self.status_dot.setObjectName("StatusDot")

        # 2. Mode Pill
        self.mode_btn = QPushButton("⚡ MACH", self.top_row)
        self.mode_btn.setObjectName("ModeBtn")
        self.mode_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mode_btn.clicked.connect(self._toggle_mode)

        # 3. Context & Telemetry Pill (Visible when idle)
        self.context_label = QLabel("⚡ Ready · Alt+C / Ctrl+Alt+Space", self.top_row)
        self.context_label.setObjectName("ContextLabel")

        # 4. Command Input Field (Visible when expanded)
        self.input_field = QLineEdit(self.top_row)
        self.input_field.setObjectName("InputField")
        self.input_field.setPlaceholderText("Ask AI, search platform, launch app, or give autonomous task...")
        self.input_field.returnPressed.connect(self._on_submit)
        self.input_field.textChanged.connect(self._on_text_changed)
        self.input_field.hide()

        # 5. Real-Time Semantic Intent Badge
        self.intent_badge = QLabel("⚡ AURA PILOT", self.top_row)
        self.intent_badge.setObjectName("IntentBadge")
        self.intent_badge.hide()

        # 6. Minimize to Tray Button
        self.tray_btn = QPushButton("─", self.top_row)
        self.tray_btn.setObjectName("TrayBtn")
        self.tray_btn.setToolTip("Minimize to Tray")
        self.tray_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tray_btn.clicked.connect(self.hide_to_tray)
        self.tray_btn.hide()

        # 7. Dismiss Button
        self.dismiss_btn = QPushButton("✕", self.top_row)
        self.dismiss_btn.setObjectName("DismissBtn")
        self.dismiss_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.dismiss_btn.clicked.connect(self.collapse_capsule)
        self.dismiss_btn.hide()

        self.top_layout.addWidget(self.status_dot)
        self.top_layout.addWidget(self.mode_btn)
        self.top_layout.addWidget(self.context_label, 1)
        self.top_layout.addWidget(self.input_field, 1)
        self.top_layout.addWidget(self.intent_badge)
        self.top_layout.addWidget(self.tray_btn)
        self.top_layout.addWidget(self.dismiss_btn)

        # Dynamic Action Chips Row
        self.chips_row = QWidget(self.card)
        self.chips_layout = QHBoxLayout(self.chips_row)
        self.chips_layout.setContentsMargins(28, 0, 0, 2)
        self.chips_layout.setSpacing(6)

        self.chip_tagrush = self._create_chip("🎮 TagRush QA", "test tagrush")
        self.chip_shorts = self._create_chip("▶ YouTube Shorts", "play youtube shorts")
        self.chip_clean = self._create_chip("🧹 Clean Cache", "clean temp")
        self.chip_explain = self._create_chip("📋 Explain Clipboard", "explain this error")

        self.chips_layout.addWidget(self.chip_tagrush)
        self.chips_layout.addWidget(self.chip_shorts)
        self.chips_layout.addWidget(self.chip_explain)
        self.chips_layout.addWidget(self.chip_clean)
        self.chips_layout.addStretch()
        self.chips_row.hide()

        # AI Viewport (Markdown Intelligence Card)
        self.ai_card = QFrame(self.card)
        self.ai_card.setObjectName("AiCard")
        self.ai_layout = QVBoxLayout(self.ai_card)
        self.ai_layout.setContentsMargins(12, 8, 12, 8)
        self.ai_layout.setSpacing(6)

        self.ai_header = QWidget(self.ai_card)
        self.ai_header_layout = QHBoxLayout(self.ai_header)
        self.ai_header_layout.setContentsMargins(0, 0, 0, 0)

        self.ai_source_lbl = QLabel("🧠 AURA CONTEXT AI", self.ai_header)
        self.ai_source_lbl.setObjectName("AiSourceLabel")
        self.ai_header_layout.addWidget(self.ai_source_lbl)
        self.ai_header_layout.addStretch()

        self.btn_copy = QPushButton("📋 Copy", self.ai_header)
        self.btn_copy.setObjectName("AiActionBtn")
        self.btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy.clicked.connect(self._copy_answer)
        self.ai_header_layout.addWidget(self.btn_copy)

        self.btn_close_ai = QPushButton("✕", self.ai_header)
        self.btn_close_ai.setObjectName("AiCloseBtn")
        self.btn_close_ai.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close_ai.clicked.connect(self.hide_ai_card)
        self.ai_header_layout.addWidget(self.btn_close_ai)

        self.ai_layout.addWidget(self.ai_header)

        self.ai_text = QTextBrowser(self.ai_card)
        self.ai_text.setObjectName("AiText")
        self.ai_text.setOpenExternalLinks(True)
        self.ai_layout.addWidget(self.ai_text)
        self.ai_card.hide()

        self.card_layout.addWidget(self.top_row)
        self.card_layout.addWidget(self.chips_row)
        self.card_layout.addWidget(self.ai_card)
        self.window_layout.addWidget(self.card)

        self.card.setCursor(Qt.CursorShape.PointingHandCursor)
        self.resize(360, 46)

    def _create_chip(self, label: str, command: str) -> QPushButton:
        btn = QPushButton(label, self.chips_row)
        btn.setObjectName("ActionChip")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(lambda: self._on_chip_clicked(command))
        return btn

    def _on_chip_clicked(self, command: str):
        self.collapse_capsule()
        self.command_submitted.emit(command)

    def _update_styles(self):
        is_mach = (self.mode == "mach")
        accent = "#00F0FF" if is_mach else "#A855F7"
        accent_bg = "rgba(0, 240, 255, 0.12)" if is_mach else "rgba(168, 85, 247, 0.12)"
        accent_border = "rgba(0, 240, 255, 0.35)" if is_mach else "rgba(168, 85, 247, 0.35)"

        self.card.setStyleSheet(f"""
            QFrame#CyberCard {{
                background-color: #0A0D14;
                border: 1.5px solid {accent};
                border-radius: 14px;
            }}
            QLabel#StatusDot {{
                color: {accent};
                font-size: 11px;
            }}
            QLabel#ContextLabel {{
                color: #94A3B8;
                font-family: 'Segoe UI', Inter, sans-serif;
                font-size: 11px;
            }}
            QLabel#IntentBadge {{
                background-color: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(0, 240, 255, 0.4);
                border-radius: 4px;
                color: #00F0FF;
                font-family: 'Cascadia Code', Consolas, monospace;
                font-size: 9px;
                font-weight: bold;
                padding: 2px 6px;
            }}
            QPushButton#ModeBtn {{
                background-color: {accent_bg};
                border: 1px solid {accent_border};
                border-radius: 6px;
                color: {accent};
                font-family: 'Cascadia Code', Consolas, monospace;
                font-weight: bold;
                font-size: 10px;
                padding: 2px 7px;
            }}
            QPushButton#ModeBtn:hover {{
                background-color: {accent};
                color: #000000;
            }}
            QLineEdit#InputField {{
                background: transparent;
                border: none;
                color: #F8FAFC;
                font-family: 'Segoe UI', Inter, sans-serif;
                font-size: 13px;
                selection-background-color: {accent};
                selection-color: #000000;
            }}
            QPushButton#TrayBtn, QPushButton#DismissBtn {{
                background: transparent;
                border: none;
                color: #64748B;
                font-size: 11px;
                padding: 2px 4px;
            }}
            QPushButton#TrayBtn:hover, QPushButton#DismissBtn:hover {{
                color: #EF4444;
            }}
            QPushButton#ActionChip {{
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                color: #CBD5E1;
                font-family: 'Segoe UI', Inter, sans-serif;
                font-size: 10px;
                padding: 3px 8px;
            }}
            QPushButton#ActionChip:hover {{
                background-color: {accent_bg};
                border-color: {accent};
                color: #FFFFFF;
            }}
            QFrame#AiCard {{
                background-color: rgba(15, 23, 42, 0.7);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
            }}
            QLabel#AiSourceLabel {{
                color: {accent};
                font-family: 'Cascadia Code', Consolas, monospace;
                font-size: 10px;
                font-weight: bold;
            }}
            QTextBrowser#AiText {{
                background: transparent;
                border: none;
                color: #E2E8F0;
                font-family: 'Segoe UI', Inter, sans-serif;
                font-size: 12px;
                line-height: 1.4;
            }}
            QPushButton#AiActionBtn {{
                background-color: rgba(255, 255, 255, 0.07);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 4px;
                color: #94A3B8;
                font-size: 10px;
                padding: 2px 6px;
            }}
            QPushButton#AiActionBtn:hover {{
                border-color: {accent};
                color: #FFFFFF;
            }}
            QPushButton#AiCloseBtn {{
                background: transparent;
                border: none;
                color: #64748B;
                font-size: 11px;
            }}
            QPushButton#AiCloseBtn:hover {{
                color: #EF4444;
            }}
        """)

    def _reposition(self):
        screen = QApplication.primaryScreen().geometry()
        x = int((screen.width() - self.width()) / 2)
        y = int(screen.height() - self.height() - 20)
        self.move(x, y)

    def _toggle_mode(self):
        self.mode = "biomimetic" if self.mode == "mach" else "mach"
        self.mode_btn.setText("🧬 BIO" if self.mode == "biomimetic" else "⚡ MACH")
        self._update_styles()
        self.mode_toggled.emit(self.mode)

    def set_status(self, text: str, is_active: bool = False):
        clean = text.strip()
        if len(clean) > 38:
            clean = clean[:38] + "..."
        accent = "#00F0FF" if self.mode == "mach" else "#A855F7"
        if is_active:
            self.status_dot.setStyleSheet("color: #F59E0B; font-size: 11px;")
            self.context_label.setText(f"⚡ {clean}")
        else:
            dot_color = "#10B981" if any(w in clean.lower() for w in ["done", "complete", "ready", "ok"]) else accent
            self.status_dot.setStyleSheet(f"color: {dot_color}; font-size: 11px;")
            self.context_label.setText(clean)

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
        self.intent_badge.show()
        self.tray_btn.show()
        self.dismiss_btn.show()
        self.chips_row.show()

        fg = PERCEPTION.get_foreground_window()
        if fg["process"] not in ["explorer.exe", "system"]:
            self.intent_badge.setText(f"🎯 {fg['process'].upper()[:12]}")

        clip = PERCEPTION.get_clipboard_text()
        if clip:
            self.chip_explain.setText("📋 Fix Clipboard Code")

        self.card.setCursor(Qt.CursorShape.ArrowCursor)
        self.resize(720, 86)
        self._reposition()

        self.activateWindow()
        self.input_field.setFocus()

    def collapse_capsule(self):
        if not self.is_expanded:
            return
        self.is_expanded = False
        self.ai_card.hide()
        self.input_field.clear()
        self.input_field.hide()
        self.intent_badge.hide()
        self.tray_btn.hide()
        self.dismiss_btn.hide()
        self.chips_row.hide()
        self.context_label.show()

        fg = PERCEPTION.get_foreground_window()
        self.context_label.setText(f"⚡ In {fg['process']} · Alt+C to summon")

        self.card.setCursor(Qt.CursorShape.PointingHandCursor)
        self.resize(360, 46)
        self._reposition()

        if self.previous_hwnd:
            try:
                if user32.IsWindow(self.previous_hwnd):
                    user32.SetForegroundWindow(self.previous_hwnd)
            except Exception:
                pass
            self.previous_hwnd = None

    def _on_text_changed(self, text: str):
        label, color = ROUTER.get_preview(text)
        self.intent_badge.setText(label)
        self.intent_badge.setStyleSheet(f"""
            background-color: rgba(255, 255, 255, 0.06);
            border: 1px solid {color};
            border-radius: 4px;
            color: {color};
            font-family: 'Cascadia Code', Consolas, monospace;
            font-size: 9px;
            font-weight: bold;
            padding: 2px 6px;
        """)

    def show_ai_answer(self, data: dict):
        self.current_answer = data.get("answer", "")
        source = data.get("source", "Aura AI")
        elapsed = data.get("elapsed", 0)

        self.ai_source_lbl.setText(f"✨ {source.upper()} · {elapsed}s")
        self.ai_text.setMarkdown(self.current_answer)

        self.is_expanded = True
        self.context_label.hide()
        self.input_field.show()
        self.intent_badge.show()
        self.intent_badge.setText("🧠 AURA READY")
        self.tray_btn.show()
        self.dismiss_btn.show()
        self.chips_row.hide()
        self.ai_card.show()

        self.card.setCursor(Qt.CursorShape.ArrowCursor)
        self.resize(720, 320)
        self._reposition()
        self.activateWindow()

    def hide_ai_card(self):
        self.ai_card.hide()
        if self.is_expanded:
            self.resize(720, 86)
            self.chips_row.show()
            self._reposition()
            self.input_field.setFocus()
        else:
            self.collapse_capsule()

    def _copy_answer(self):
        if hasattr(self, "current_answer") and self.current_answer:
            QApplication.clipboard().setText(self.current_answer)
            self.btn_copy.setText("✓ Copied")
            QTimer.singleShot(1500, lambda: self.btn_copy.setText("📋 Copy"))

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
            self.intent_badge.setText("⏳ AI THINKING...")
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
