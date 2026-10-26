"""
ui/stealth_capsule.py - Production Dark Obsidian Capsule HUD
Rock-solid QFrame card architecture. Zero black-box artifacts.
100% clean alpha transparency, luminous cyan/purple borders, and 1-click action chips.
"""

import ctypes
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QWidget, QFrame, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit, 
    QPushButton, QApplication, QTextBrowser
)
from config.tokens import TOKENS
from brain.local_router import ROUTER

user32 = ctypes.WinDLL("user32", use_last_error=True)

class AuraStealthCapsule(QWidget):
    command_submitted = pyqtSignal(str)
    mode_toggled = pyqtSignal(str)
    collapsed = pyqtSignal()

    def __init__(self, default_mode: str = "mach"):
        super().__init__()
        self.mode = default_mode
        self.is_expanded = False
        self.previous_hwnd = None

        # Frameless, transparent background, stays on top, tool window
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        self._apply_stealth()
        self._init_ui()
        self._update_styles()
        self._position_at_bottom_center()

    def _apply_stealth(self):
        """Applies WDA_EXCLUDEFROMCAPTURE (0x11) so window is completely invisible to screen recorders (OBS, Discord, Snipping Tool)."""
        try:
            hwnd = int(self.winId())
            if hasattr(user32, "SetWindowDisplayAffinity"):
                WDA_EXCLUDEFROMCAPTURE = 0x00000011
                user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)
        except Exception:
            pass

    def showEvent(self, event):
        super().showEvent(event)
        self._apply_stealth()
        self._position_at_bottom_center()

    def _init_ui(self):
        # Outer window layout (transparent margin around the card)
        self.window_layout = QVBoxLayout(self)
        self.window_layout.setContentsMargins(4, 4, 4, 4)
        self.window_layout.setSpacing(0)

        # Main Card Frame (handles background, border, and rounded corners)
        self.card = QFrame(self)
        self.card.setObjectName("CapsuleCard")
        self.card_layout = QVBoxLayout(self.card)
        self.card_layout.setContentsMargins(12, 6, 12, 6)
        self.card_layout.setSpacing(6)

        # --- Top Row (Controls & Input) ---
        self.top_row = QWidget(self.card)
        self.top_layout = QHBoxLayout(self.top_row)
        self.top_layout.setContentsMargins(0, 0, 0, 0)
        self.top_layout.setSpacing(8)

        # 1. Status Indicator Pip
        self.status_dot = QLabel("●", self.top_row)
        self.status_dot.setObjectName("StatusDot")

        # 2. Mode Toggle Button
        self.mode_btn = QPushButton("⚡ MACH", self.top_row)
        self.mode_btn.setObjectName("ModeBtn")
        self.mode_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mode_btn.clicked.connect(self._toggle_mode)

        # 3. Idle Status / Telemetry Label
        self.telemetry_label = QLabel("Click or Ctrl+Space to search · 0.01ms", self.top_row)
        self.telemetry_label.setObjectName("TelemetryLabel")

        # 4. Command Input Field (Visible when expanded)
        self.input_field = QLineEdit(self.top_row)
        self.input_field.setObjectName("InputField")
        self.input_field.setPlaceholderText("Search Google, open apps, or type command (e.g. 'godot 4 tips', 'tagrush')...")
        self.input_field.returnPressed.connect(self._on_submit)
        self.input_field.textChanged.connect(self._on_text_changed)
        self.input_field.hide()

        # 5. Fast Router Badge
        self.router_badge = QLabel("⚡ INSTANT (0ms)", self.top_row)
        self.router_badge.setObjectName("RouterBadge")
        self.router_badge.hide()

        # 6. Escape / Dismiss Button
        self.dismiss_btn = QPushButton("ESC ✕", self.top_row)
        self.dismiss_btn.setObjectName("DismissBtn")
        self.dismiss_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.dismiss_btn.clicked.connect(self.collapse_capsule)
        self.dismiss_btn.hide()

        self.top_layout.addWidget(self.status_dot)
        self.top_layout.addWidget(self.mode_btn)
        self.top_layout.addWidget(self.telemetry_label)
        self.top_layout.addWidget(self.input_field, 1)
        self.top_layout.addWidget(self.router_badge)
        self.top_layout.addWidget(self.dismiss_btn)

        # --- Bottom Row 1 (1-Click Action Chips) ---
        self.chips_row = QWidget(self.card)
        self.chips_layout = QHBoxLayout(self.chips_row)
        self.chips_layout.setContentsMargins(28, 0, 0, 2)
        self.chips_layout.setSpacing(6)

        self.chip_tagrush = self._create_chip("🎮 TagRush Dual QA", "test tagrush")
        self.chip_whatsapp = self._create_chip("💬 WhatsApp Class", "open whatsapp and open my class group")
        self.chip_shorts = self._create_chip("▶ YouTube Shorts", "go to youtube and click on a shorts video there by mouse")
        self.chip_search = self._create_chip("🔍 Search", "__SEARCH_ACTION__")
        self.chip_clean = self._create_chip("🧹 Clean Cache", "clean temp")

        self.chips_layout.addWidget(self.chip_tagrush)
        self.chips_layout.addWidget(self.chip_whatsapp)
        self.chips_layout.addWidget(self.chip_shorts)
        self.chips_layout.addWidget(self.chip_search)
        self.chips_layout.addWidget(self.chip_clean)
        self.chips_layout.addStretch()
        self.chips_row.hide()

        # --- Bottom Row 2 (Astra Inline Response Card) ---
        self.current_answer_text = ""
        self.current_query = ""
        self.response_card = QFrame(self.card)
        self.response_card.setObjectName("ResponseCard")
        self.resp_layout = QVBoxLayout(self.response_card)
        self.resp_layout.setContentsMargins(12, 8, 12, 8)
        self.resp_layout.setSpacing(6)

        # Header with source badge and action buttons
        self.resp_header = QWidget(self.response_card)
        self.resp_header_layout = QHBoxLayout(self.resp_header)
        self.resp_header_layout.setContentsMargins(0, 0, 0, 0)
        self.resp_header_layout.setSpacing(6)

        self.resp_source_lbl = QLabel("🧠 AURA CONTEXT AI", self.resp_header)
        self.resp_source_lbl.setObjectName("RespSourceLabel")
        self.resp_header_layout.addWidget(self.resp_source_lbl)
        self.resp_header_layout.addStretch()

        self.btn_copy = QPushButton("📋 Copy", self.resp_header)
        self.btn_copy.setObjectName("RespActionBtn")
        self.btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy.clicked.connect(self._copy_response)
        self.resp_header_layout.addWidget(self.btn_copy)

        self.btn_close_resp = QPushButton("✕", self.resp_header)
        self.btn_close_resp.setObjectName("RespCloseBtn")
        self.btn_close_resp.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close_resp.clicked.connect(self.hide_response_card)
        self.resp_header_layout.addWidget(self.btn_close_resp)

        self.resp_layout.addWidget(self.resp_header)

        # Response content display (Markdown enabled)
        self.resp_text = QTextBrowser(self.response_card)
        self.resp_text.setObjectName("ResponseText")
        self.resp_text.setOpenExternalLinks(True)
        self.resp_layout.addWidget(self.resp_text)

        self.response_card.hide()

        self.card_layout.addWidget(self.top_row)
        self.card_layout.addWidget(self.chips_row)
        self.card_layout.addWidget(self.response_card)
        self.window_layout.addWidget(self.card)

        self.card.setCursor(Qt.CursorShape.PointingHandCursor)
        self.resize(340, 46)

    def _create_chip(self, label: str, command: str) -> QPushButton:
        btn = QPushButton(label, self.chips_row)
        btn.setObjectName("ActionChip")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(lambda: self._on_chip_clicked(command))
        return btn

    def _on_chip_clicked(self, command: str):
        if command == "__SEARCH_ACTION__":
            text = self.input_field.text().strip()
            if text:
                self.collapse_capsule()
                self.command_submitted.emit(text)
            else:
                self.input_field.setPlaceholderText("Type query and press Enter (e.g. 'godot 4 tips')...")
                self.input_field.setFocus()
            return
        self.collapse_capsule()
        self.command_submitted.emit(command)

    def _update_styles(self):
        is_mach = (self.mode == "mach")
        accent_color = "#00F0FF" if is_mach else "#A855F7"
        accent_bg = "rgba(0, 240, 255, 0.15)" if is_mach else "rgba(168, 85, 247, 0.15)"
        accent_border = "rgba(0, 240, 255, 0.40)" if is_mach else "rgba(168, 85, 247, 0.40)"

        self.card.setStyleSheet(f"""
            QFrame#CapsuleCard {{
                background-color: #0B0F19;
                border: 1.5px solid {accent_color};
                border-radius: 14px;
            }}
            QLabel#StatusDot {{
                color: {accent_color};
                font-size: 12px;
            }}
            QLabel#TelemetryLabel {{
                color: #94A3B8;
                font-family: 'Segoe UI', Inter, sans-serif;
                font-size: 11px;
            }}
            QLabel#RouterBadge {{
                background-color: rgba(16, 185, 129, 0.15);
                border: 1px solid rgba(16, 185, 129, 0.4);
                border-radius: 4px;
                color: #10B981;
                font-family: 'Cascadia Code', Consolas, monospace;
                font-size: 9px;
                font-weight: bold;
                padding: 2px 5px;
            }}
            QPushButton#ModeBtn {{
                background-color: {accent_bg};
                border: 1px solid {accent_border};
                border-radius: 6px;
                color: {accent_color};
                font-family: 'Cascadia Code', Consolas, monospace;
                font-weight: bold;
                font-size: 10px;
                padding: 3px 7px;
            }}
            QPushButton#ModeBtn:hover {{
                background-color: {accent_color};
                color: #000000;
            }}
            QLineEdit#InputField {{
                background: transparent;
                border: none;
                color: #F8FAFC;
                font-family: 'Segoe UI', Inter, sans-serif;
                font-size: 13px;
                selection-background-color: {accent_color};
                selection-color: #000000;
            }}
            QPushButton#ActionChip {{
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 5px;
                color: #94A3B8;
                font-family: 'Segoe UI', Inter, sans-serif;
                font-size: 11px;
                padding: 3px 8px;
            }}
            QPushButton#ActionChip:hover {{
                background-color: {accent_bg};
                border-color: {accent_border};
                color: #F8FAFC;
            }}
            QPushButton#DismissBtn {{
                background: transparent;
                border: none;
                color: #64748B;
                font-family: 'Cascadia Code', Consolas, monospace;
                font-size: 10px;
                padding: 2px;
            }}
            QPushButton#DismissBtn:hover {{
                color: #EF4444;
            }}
            QFrame#ResponseCard {{
                background-color: #070A12;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 8px;
            }}
            QLabel#RespSourceLabel {{
                color: #38BDF8;
                font-family: 'Cascadia Code', Consolas, monospace;
                font-size: 10px;
                font-weight: bold;
                letter-spacing: 0.5px;
            }}
            QTextBrowser#ResponseText {{
                background: transparent;
                border: none;
                color: #E2E8F0;
                font-family: 'Segoe UI', Inter, sans-serif;
                font-size: 12px;
                line-height: 1.4;
            }}
            QPushButton#RespActionBtn {{
                background-color: rgba(255, 255, 255, 0.07);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 4px;
                color: #94A3B8;
                font-family: 'Segoe UI', sans-serif;
                font-size: 10px;
                padding: 2px 7px;
            }}
            QPushButton#RespActionBtn:hover {{
                background-color: rgba(0, 240, 255, 0.15);
                border-color: #00F0FF;
                color: #FFFFFF;
            }}
            QPushButton#RespCloseBtn {{
                background: transparent;
                border: none;
                color: #64748B;
                font-size: 11px;
                font-weight: bold;
                padding: 2px 5px;
            }}
            QPushButton#RespCloseBtn:hover {{
                color: #EF4444;
            }}
        """)

    def _position_at_bottom_center(self):
        screen = QApplication.primaryScreen().geometry()
        x = int((screen.width() - self.width()) / 2)
        y = int(screen.height() - self.height() - 24)
        self.move(x, y)

    def _toggle_mode(self):
        if self.mode == "mach":
            self.mode = "biomimetic"
            self.mode_btn.setText("🧬 BIO")
        else:
            self.mode = "mach"
            self.mode_btn.setText("⚡ MACH")

        self._update_styles()
        self.mode_toggled.emit(self.mode)

    def set_status(self, text: str, is_active: bool = False):
        """Displays real-time status message directly on the capsule without error jargon."""
        # Clean noisy technical error messages
        import re
        clean = re.sub(r"\[.*?\]", "", text).strip()
        if any(w in clean.lower() for w in ["http error", "failed to parse", "geminiclient", "traceback"]):
            clean = "Processing task..."
        if len(clean) > 42:
            clean = clean[:42] + "..."

        accent = "#00F0FF" if self.mode == "mach" else "#A855F7"
        if is_active:
            self.status_dot.setStyleSheet("color: #F59E0B; font-size: 12px;")
            self.telemetry_label.setText(f"⚡ {clean}")
        else:
            dot_color = "#10B981" if ("complete" in clean.lower() or "active" in clean.lower() or "ok" in clean.lower()) else accent
            self.status_dot.setStyleSheet(f"color: {dot_color}; font-size: 12px;")
            self.telemetry_label.setText(clean)

    def toggle_expand(self):
        if self.isHidden():
            self.show()
            self.expand_capsule()
            return
        if self.is_expanded:
            self.collapse_capsule()
        else:
            self.expand_capsule()

    def hide_to_tray(self):
        """Hides the assistant completely into the Windows system tray."""
        self.collapse_capsule()
        self.hide()

    def expand_capsule(self):
        """Expands into full command bar with 1-click chips (docked at bottom)."""
        if self.isHidden():
            self.show()
        if self.is_expanded:
            return
        self.previous_hwnd = user32.GetForegroundWindow()
        self.is_expanded = True

        self.telemetry_label.hide()
        self.input_field.show()
        self.router_badge.show()
        self.dismiss_btn.show()
        self.chips_row.show()

        self.card.setCursor(Qt.CursorShape.ArrowCursor)
        self.resize(740, 88)
        self._position_at_bottom_center()

        self.activateWindow()
        self.input_field.setFocus()
        
        # Check active window context and clipboard
        try:
            from brain.context_engine import CONTEXT_ENGINE
            fg = CONTEXT_ENGINE.get_foreground_window_info()
            if fg and fg.get("app") not in ["Desktop", "App"]:
                self.router_badge.setText(f"🎯 {fg['app'].upper()[:12]}")
                self.router_badge.show()
            clip = CONTEXT_ENGINE.check_clipboard_context()
            if clip:
                self.chip_clean.setText("📋 Paste Code/Error")
        except Exception:
            pass

    def _on_text_changed(self, text: str):
        """Dynamically updates router badge as user types (<0.05ms)."""
        label, color = ROUTER.get_intent_preview(text)
        self.router_badge.setText(label)
        self.router_badge.setStyleSheet(f"""
            background-color: rgba(255, 255, 255, 0.06);
            border: 1px solid {color};
            border-radius: 4px;
            color: {color};
            font-family: 'Cascadia Code', Consolas, monospace;
            font-size: 9px;
            font-weight: bold;
            padding: 2px 5px;
        """)

    def show_inline_answer(self, data: dict):
        """Displays rich Astra intelligence answer directly above the bottom capsule."""
        self.current_answer_text = data.get("answer", "")
        self.current_query = data.get("title", "")
        source = data.get("source", "Astra")
        elapsed = data.get("elapsed", 0)

        self.resp_source_lbl.setText(f"✨ {source.upper()} · {elapsed}s")
        self.resp_text.setMarkdown(self.current_answer_text)

        self.is_expanded = True
        self.telemetry_label.hide()
        self.input_field.show()
        self.router_badge.setText("🧠 CONTEXT AI")
        self.router_badge.show()
        self.dismiss_btn.show()
        self.chips_row.hide()
        self.response_card.show()

        self.card.setCursor(Qt.CursorShape.ArrowCursor)
        self.resize(740, 320)
        self._position_at_bottom_center()
        self.activateWindow()

    def hide_response_card(self):
        """Hides response card and restores compact expanded state."""
        self.response_card.hide()
        if self.is_expanded:
            self.resize(740, 88)
            self.chips_row.show()
            self._position_at_bottom_center()
            self.input_field.setFocus()
        else:
            self.collapse_capsule()

    def _copy_response(self):
        """Copies answer markdown to Windows clipboard."""
        if hasattr(self, "current_answer_text") and self.current_answer_text:
            QApplication.clipboard().setText(self.current_answer_text)
            self.btn_copy.setText("✓ Copied!")
            QTimer.singleShot(1500, lambda: self.btn_copy.setText("📋 Copy"))

    def collapse_capsule(self):
        """Collapses into clean idle micro-pill docked at bottom of desktop."""
        if not self.is_expanded:
            return
        self.is_expanded = False
        self.response_card.hide()
        self.input_field.clear()
        self.input_field.hide()
        self.router_badge.hide()
        self.dismiss_btn.hide()
        self.chips_row.hide()
        self.telemetry_label.show()

        self.card.setCursor(Qt.CursorShape.PointingHandCursor)
        self.resize(360, 46)
        self._position_at_bottom_center()

        if self.previous_hwnd:
            try:
                if user32.IsWindow(self.previous_hwnd):
                    user32.SetForegroundWindow(self.previous_hwnd)
            except Exception:
                pass
            self.previous_hwnd = None

        self.collapsed.emit()

    def mousePressEvent(self, event):
        """Clicking the idle pill automatically expands it!"""
        if not self.is_expanded and event.button() == Qt.MouseButton.LeftButton:
            self.expand_capsule()
        else:
            super().mousePressEvent(event)

    def _on_submit(self):
        cmd = self.input_field.text().strip()
        if not cmd:
            return
        intent = ROUTER.route(cmd)
        if intent.intent_type == "astra_inline_query":
            # Keep capsule open, display thinking indicator!
            self.router_badge.setText("⏳ AI THINKING...")
            self.router_badge.setStyleSheet("""
                background-color: rgba(56, 189, 248, 0.15);
                border: 1px solid #38BDF8;
                border-radius: 4px;
                color: #38BDF8;
                font-family: 'Cascadia Code', Consolas, monospace;
                font-size: 9px;
                font-weight: bold;
                padding: 2px 5px;
            """)
            self.command_submitted.emit(cmd)
        else:
            self.collapse_capsule()
            self.command_submitted.emit(cmd)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            if self.response_card.isVisible():
                self.hide_response_card()
            else:
                self.collapse_capsule()
        else:
            super().keyPressEvent(event)
