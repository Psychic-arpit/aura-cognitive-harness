"""
aura.ui.dock - Ethereal Aero Glassmorphic Cyber-Dock
Hardware-accelerated Windows DWM Acrylic & Aero Blur-Behind.
Docked at desktop bottom (above taskbar), expands upwards, 100% stream-invisible (0x11).
Progressive typewriter streaming viewport + specular glass bevels.
"""

import ctypes
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QWidget, QFrame, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QApplication, QTextBrowser
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
            # 1. OS-level screen recording & stream stealth (0x11)
            STEALTH.apply_stream_invisibility(hwnd)
            # 2. Windows DWM Acrylic & Aero hardware blur-behind
            GLASS.enable_aero_glass(hwnd, tint_rgba=(10, 14, 24, 185))
        except Exception:
            pass

    def showEvent(self, event):
        super().showEvent(event)
        self._apply_stealth_and_glass()
        self._reposition()

    def _init_ui(self):
        self.window_layout = QVBoxLayout(self)
        self.window_layout.setContentsMargins(4, 4, 4, 4)
        self.window_layout.setSpacing(0)

        # Main Aero Glass Card Frame
        self.card = QFrame(self)
        self.card.setObjectName("AeroGlassCard")
        self.card_layout = QVBoxLayout(self.card)
        self.card_layout.setContentsMargins(14, 8, 14, 8)
        self.card_layout.setSpacing(6)

        # Top Control & Input Bar
        self.top_row = QWidget(self.card)
        self.top_layout = QHBoxLayout(self.top_row)
        self.top_layout.setContentsMargins(0, 0, 0, 0)
        self.top_layout.setSpacing(8)

        # 1. Pulsing Neon Pip
        self.status_dot = QLabel("●", self.top_row)
        self.status_dot.setObjectName("StatusDot")

        # 2. Aero Mode Pill
        self.mode_btn = QPushButton("⚡ MACH", self.top_row)
        self.mode_btn.setObjectName("ModeBtn")
        self.mode_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mode_btn.clicked.connect(self._toggle_mode)

        # 3. Ambient Context Pill (Visible when idle)
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

        # Aero Glass Action Chips Row
        self.chips_row = QWidget(self.card)
        self.chips_layout = QHBoxLayout(self.chips_row)
        self.chips_layout.setContentsMargins(28, 2, 0, 4)
        self.chips_layout.setSpacing(6)

        self.chip_tagrush = self._create_chip("🎮 TagRush QA", "test tagrush")
        self.chip_shorts = self._create_chip("▶ YouTube Shorts", "play youtube shorts")
        self.chip_clean = self._create_chip("🧹 Clean Cache", "clean temp")
        self.chip_explain = self._create_chip("📋 Fix Clipboard Code", "explain this error")

        self.chips_layout.addWidget(self.chip_tagrush)
        self.chips_layout.addWidget(self.chip_shorts)
        self.chips_layout.addWidget(self.chip_explain)
        self.chips_layout.addWidget(self.chip_clean)
        self.chips_layout.addStretch()
        self.chips_row.hide()

        # Aero AI Viewport (Frosted Intelligence Card)
        self.ai_card = QFrame(self.card)
        self.ai_card.setObjectName("AiGlassCard")
        self.ai_layout = QVBoxLayout(self.ai_card)
        self.ai_layout.setContentsMargins(14, 10, 14, 10)
        self.ai_layout.setSpacing(6)

        self.ai_header = QWidget(self.ai_card)
        self.ai_header_layout = QHBoxLayout(self.ai_header)
        self.ai_header_layout.setContentsMargins(0, 0, 0, 0)

        self.ai_source_lbl = QLabel("🧠 AURA CONTEXT AI", self.ai_header)
        self.ai_source_lbl.setObjectName("AiSourceLabel")
        self.ai_header_layout.addWidget(self.ai_source_lbl)
        self.ai_header_layout.addStretch()

        self.btn_copy = QPushButton("📋 Copy", self.ai_header)
        self.btn_copy.setObjectName("GlassActionBtn")
        self.btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy.clicked.connect(self._copy_answer)
        self.ai_header_layout.addWidget(self.btn_copy)

        self.btn_close_ai = QPushButton("✕", self.ai_header)
        self.btn_close_ai.setObjectName("GlassCloseBtn")
        self.btn_close_ai.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close_ai.clicked.connect(self.hide_ai_card)
        self.ai_header_layout.addWidget(self.btn_close_ai)

        self.ai_layout.addWidget(self.ai_header)

        self.ai_text = QTextBrowser(self.ai_card)
        self.ai_text.setObjectName("AiGlassText")
        self.ai_text.setOpenExternalLinks(True)
        self.ai_layout.addWidget(self.ai_text)
        self.ai_card.hide()

        self.card_layout.addWidget(self.top_row)
        self.card_layout.addWidget(self.chips_row)
        self.card_layout.addWidget(self.ai_card)
        self.window_layout.addWidget(self.card)

        self.card.setCursor(Qt.CursorShape.PointingHandCursor)
        self.resize(380, 48)

    def _create_chip(self, label: str, command: str) -> QPushButton:
        btn = QPushButton(label, self.chips_row)
        btn.setObjectName("AeroChip")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(lambda: self._on_chip_clicked(command))
        return btn

    def _on_chip_clicked(self, command: str):
        self.collapse_capsule()
        self.command_submitted.emit(command)

    def _update_styles(self):
        is_mach = (self.mode == "mach")
        accent = "#00F0FF" if is_mach else "#C084FC"
        accent_glow = "rgba(0, 240, 255, 0.35)" if is_mach else "rgba(192, 132, 252, 0.35)"
        accent_bg = "rgba(0, 240, 255, 0.15)" if is_mach else "rgba(192, 132, 252, 0.15)"

        self.card.setStyleSheet(f"""
            QFrame#AeroGlassCard {{
                background-color: rgba(10, 15, 26, 0.65);
                border: 1.5px solid {accent};
                border-top: 1.5px solid rgba(255, 255, 255, 0.45);
                border-radius: 16px;
            }}
            QLabel#StatusDot {{
                color: {accent};
                font-size: 11px;
            }}
            QLabel#ContextLabel {{
                color: #CBD5E1;
                font-family: 'Segoe UI Variable Display', 'Segoe UI', Inter, sans-serif;
                font-size: 11px;
                font-weight: 500;
            }}
            QLabel#IntentBadge {{
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid {accent};
                border-radius: 5px;
                color: {accent};
                font-family: 'Cascadia Code', Consolas, monospace;
                font-size: 9px;
                font-weight: bold;
                padding: 2px 7px;
            }}
            QPushButton#ModeBtn {{
                background-color: {accent_bg};
                border: 1px solid {accent};
                border-radius: 7px;
                color: {accent};
                font-family: 'Cascadia Code', Consolas, monospace;
                font-weight: bold;
                font-size: 10px;
                padding: 2px 8px;
            }}
            QPushButton#ModeBtn:hover {{
                background-color: {accent};
                color: #050811;
            }}
            QLineEdit#InputField {{
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.14);
                border-radius: 7px;
                color: #F8FAFC;
                font-family: 'Segoe UI Variable Display', 'Segoe UI', Inter, sans-serif;
                font-size: 13px;
                padding: 2px 8px;
                selection-background-color: {accent};
                selection-color: #050811;
            }}
            QLineEdit#InputField:focus {{
                border: 1px solid {accent};
            }}
            QPushButton#TrayBtn, QPushButton#DismissBtn {{
                background: transparent;
                border: none;
                color: #94A3B8;
                font-size: 12px;
                padding: 2px 5px;
            }}
            QPushButton#TrayBtn:hover, QPushButton#DismissBtn:hover {{
                color: #EF4444;
            }}
            QPushButton#AeroChip {{
                background-color: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.14);
                border-top: 1px solid rgba(255, 255, 255, 0.28);
                border-radius: 7px;
                color: #E2E8F0;
                font-family: 'Segoe UI Variable Display', 'Segoe UI', Inter, sans-serif;
                font-size: 10px;
                font-weight: 500;
                padding: 3px 9px;
            }}
            QPushButton#AeroChip:hover {{
                background-color: {accent_bg};
                border-color: {accent};
                color: #FFFFFF;
            }}
            QFrame#AiGlassCard {{
                background-color: rgba(8, 12, 22, 0.82);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-top: 1.5px solid rgba(255, 255, 255, 0.35);
                border-radius: 12px;
            }}
            QLabel#AiSourceLabel {{
                color: {accent};
                font-family: 'Cascadia Code', Consolas, monospace;
                font-size: 10px;
                font-weight: bold;
                letter-spacing: 0.5px;
            }}
            QTextBrowser#AiGlassText {{
                background: transparent;
                border: none;
                color: #F1F5F9;
                font-family: 'Segoe UI Variable Display', 'Segoe UI', Inter, sans-serif;
                font-size: 12px;
                line-height: 1.45;
            }}
            QPushButton#GlassActionBtn {{
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.18);
                border-radius: 5px;
                color: #CBD5E1;
                font-size: 10px;
                padding: 2px 8px;
            }}
            QPushButton#GlassActionBtn:hover {{
                border-color: {accent};
                color: #FFFFFF;
                background-color: {accent_bg};
            }}
            QPushButton#GlassCloseBtn {{
                background: transparent;
                border: none;
                color: #94A3B8;
                font-size: 11px;
            }}
            QPushButton#GlassCloseBtn:hover {{
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
        accent = "#00F0FF" if self.mode == "mach" else "#C084FC"
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
        self.resize(740, 88)
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
        self.intent_badge.hide()
        self.tray_btn.hide()
        self.dismiss_btn.hide()
        self.chips_row.hide()
        self.context_label.show()

        fg = PERCEPTION.get_foreground_window()
        self.context_label.setText(f"⚡ In {fg['process']} · Alt+C to summon")

        self.card.setCursor(Qt.CursorShape.PointingHandCursor)
        self.resize(380, 48)
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
            background-color: rgba(255, 255, 255, 0.08);
            border: 1px solid {color};
            border-radius: 5px;
            color: {color};
            font-family: 'Cascadia Code', Consolas, monospace;
            font-size: 9px;
            font-weight: bold;
            padding: 2px 7px;
        """)

    def show_ai_answer(self, data: dict):
        self.current_answer = data.get("answer", "")
        source = data.get("source", "Aura AI")
        elapsed = data.get("elapsed", 0)

        self.ai_source_lbl.setText(f"✨ {source.upper()} · {elapsed}s")

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
        self.resize(740, 330)
        self._reposition()
        self.activateWindow()

        # Start 60 FPS Progressive Typewriter stream
        self._target_markdown = self.current_answer
        self._stream_index = 0
        self.ai_text.clear()
        self._typewriter_timer.start(12)  # fast typewriter step

    def _on_typewriter_tick(self):
        chunk_size = max(4, len(self._target_markdown) // 40)
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
            self.resize(740, 88)
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
