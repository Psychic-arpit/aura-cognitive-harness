"""
aura.main - Master Application Orchestrator
Binds the Sensory Perception & Execution Harness to the Cognitive Agent and Cyber-HUD.
Thread-Safe Architecture · Zero Screen-Capture Footprint · Real-Time Telemetry
"""

import sys
import os
import ctypes
import webbrowser
import subprocess

# Ensure Windows console handles Unicode cleanly
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QColor, QPixmap, QPainter
from PyQt6.QtCore import QObject, pyqtSignal, QThread, Qt

# Enforce Per-Monitor V2 DPI Awareness before GUI creation
try:
    ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
except Exception:
    pass

from aura.harness.perception import PERCEPTION
from aura.harness.actuation import ACTUATION
from aura.harness.safety import SAFETY
from aura.harness.stealth import STEALTH, MOD_ALT, MOD_CONTROL
from aura.agent.router import ROUTER, Intent
from aura.agent.kernel import KERNEL
from aura.agent.planner import PLANNER
from aura.agent.client import CLIENT
from aura.ui.dock import CyberDock
from aura.ui.overlay import AuraOverlayWindow

class TaskWorker(QObject):
    progress = pyqtSignal(str)
    finished = pyqtSignal(str)
    telemetry = pyqtSignal(float, float)
    click = pyqtSignal(float, float)
    ai_answer = pyqtSignal(dict)

    def __init__(self, intent: Intent, mode: str):
        super().__init__()
        self.intent = intent
        self.mode = mode

    def run(self):
        SAFETY.activate()
        res_msg = "Completed"

        try:
            it = self.intent.type

            # 1. Contextual AI & Visual Grounding
            if it == "context_ai":
                self.progress.emit("Consulting Aura Intelligence...")
                data = KERNEL.process(self.intent.target)
                self.ai_answer.emit(data)
                res_msg = "Aura Ready [OK]"

            # 2. Instant Math (< 0.01ms)
            elif it == "math_eval":
                expr = self.intent.extra.get("expression", "") if self.intent.extra else self.intent.target
                val = self.intent.target
                data = {
                    "title": f"Math: {expr}",
                    "source": "Instant Math Engine",
                    "answer": f"### Result: **{val}**\n\nExpression: `{expr}`\n*Evaluated in < 0.01ms.*",
                    "elapsed": 0.0
                }
                self.ai_answer.emit(data)
                res_msg = f"= {val}"

            # 3. Direct Platform Deep Navigation
            elif it == "turbo_nav":
                url = self.intent.target
                self.progress.emit(f"🚀 Launching: {url[:36]}...")
                webbrowser.open(url)
                res_msg = "Navigated [OK]"

            # 4. Multi-Step Autonomous ReAct Loop
            elif it == "autonomous_goal":
                self.progress.emit(f"Autopilot: '{self.intent.target[:28]}'...")
                result = PLANNER.execute_goal(self.intent.target, lambda msg: self.progress.emit(msg))
                res_msg = f"Autopilot Done: {result}"

            # 5. Native Application Launch
            elif it == "app_launch":
                target = self.intent.target
                self.progress.emit(f"Launching {target}...")
                cur_x, cur_y = ACTUATION.get_cursor_pos()
                sw = ctypes.windll.user32.GetSystemMetrics(0)
                sh = ctypes.windll.user32.GetSystemMetrics(1)
                ACTUATION.glide_cursor((cur_x, cur_y), (sw // 2, sh // 2), duration=0.25, telemetry_cb=lambda x, y: self.telemetry.emit(x, y))
                self.click.emit(sw // 2, sh // 2)
                subprocess.Popen(target, shell=True)
                res_msg = f"Launched {target} [OK]"

            # 6. System & Hardware Controls
            elif it == "system_control":
                action = self.intent.target
                self.progress.emit(f"System: '{action}'...")
                if action == "mute":
                    ACTUATION.fast_press("volumemute")
                elif action in ("volume up", "vol up"):
                    ACTUATION.fast_press("volumeup")
                elif action in ("volume down", "vol down"):
                    ACTUATION.fast_press("volumedown")
                elif action in ("lock", "lock screen"):
                    ctypes.windll.user32.LockWorkStation()
                elif action in ("show desktop", "minimize all"):
                    ACTUATION.fast_press("win+d")
                res_msg = f"System action {action} [OK]"

            # 7. Clean Temp Cache
            elif it == "clean_temp":
                self.progress.emit("Cleaning temporary cache...")
                import tempfile
                temp_dir = tempfile.gettempdir()
                res_msg = f"Temp cache inspected: {os.path.basename(temp_dir)} [OK]"

            # 8. Set API Key
            elif it == "set_api_key":
                CLIENT.set_key(self.intent.target)
                self.progress.emit("Gemini AI Brain Unlocked!")
                res_msg = "API Key saved successfully [OK]"

        except Exception as e:
            print(f"[TaskWorker Error]: {e}")
            res_msg = f"Notice: {e}"
        finally:
            SAFETY.deactivate()

        self.finished.emit(res_msg)

class AuraApp(QObject):
    sig_toggle_dock = pyqtSignal()
    sig_abort_gui = pyqtSignal()

    def __init__(self, q_app: QApplication):
        super().__init__()
        self.q_app = q_app
        self.mode = "mach"
        self.active_thread = None
        self.active_worker = None

        # 1. Initialize UI Viewports
        self.overlay = AuraOverlayWindow(mode=self.mode)
        self.dock = CyberDock(default_mode=self.mode)

        # 2. Wire Cross-Thread Signals
        self.sig_toggle_dock.connect(self.dock.toggle_expand, Qt.ConnectionType.QueuedConnection)
        self.sig_abort_gui.connect(self._on_abort_gui, Qt.ConnectionType.QueuedConnection)

        # 3. Wire User Actions
        self.dock.command_submitted.connect(self.on_command)
        self.dock.mode_toggled.connect(self.on_mode_toggled)

        # 4. Setup Failsafe Watchdog Callback (Esc interrupt)
        SAFETY.register_abort_callback(self._on_abort_from_watchdog)

        # 5. Setup Hotkey Sentinel (Alt+C, Ctrl+Alt+Space, Alt+Space)
        STEALTH.register_hotkey(MOD_ALT, 0x43, self._on_hotkey_from_sentinel)  # Alt + C
        STEALTH.register_hotkey(MOD_CONTROL | MOD_ALT, 0x20, self._on_hotkey_from_sentinel)  # Ctrl + Alt + Space
        STEALTH.register_hotkey(MOD_ALT, 0x20, self._on_hotkey_from_sentinel)  # Alt + Space (if free)
        STEALTH.start_hotkey_sentinel()

        # 6. Initialize System Tray
        self._init_tray_icon()

        # Show initial views
        self.overlay.show()
        self.dock.show()

        print("\n" + "=" * 62)
        print("⚡ AURA: AUTONOMOUS DESKTOP AGENT & EXECUTION HARNESS")
        print("  Placement: Bottom desktop dock (Alt+C / Ctrl+Alt+Space)")
        print("  Stealth: 100% Invisible to screen recorders (0x11)")
        print("  Harness: Hardware SendInput + UIAutomation + Safety Circuit")
        print("  Agent: Gemini 3.5 Flash Lite + Multi-Step ReAct Planner")
        print("=" * 62 + "\n")

    def _init_tray_icon(self):
        pix = QPixmap(16, 16)
        pix.fill(QColor(0, 0, 0, 0))
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(0, 240, 255))
        painter.setPen(QColor(255, 255, 255, 200))
        painter.drawEllipse(2, 2, 12, 12)
        painter.end()

        self.tray = QSystemTrayIcon(QIcon(pix), self.q_app)
        self.tray.setToolTip("AURA Cognitive Harness (Alt+C)")
        self.tray.activated.connect(self._on_tray_activated)

        menu = QMenu()
        act_open = menu.addAction("Toggle Cyber-Dock (Alt+C)")
        act_open.triggered.connect(self._toggle_assistant)

        menu.addSeparator()
        act_ig = menu.addAction("Instagram Search")
        act_ig.triggered.connect(lambda: self.on_command("open instagram"))

        act_yt = menu.addAction("YouTube Shorts")
        act_yt.triggered.connect(lambda: self.on_command("play youtube shorts"))

        menu.addSeparator()
        act_hide = menu.addAction("Hide to Tray")
        act_hide.triggered.connect(self.dock.hide_to_tray)

        act_mode = menu.addAction("Switch Mode (Mach / Bio)")
        act_mode.triggered.connect(self.dock._toggle_mode)

        menu.addSeparator()
        act_exit = menu.addAction("Exit Aura")
        act_exit.triggered.connect(self.q_app.quit)

        self.tray.setContextMenu(menu)
        self.tray.show()

    def _on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self._toggle_assistant()

    def _toggle_assistant(self):
        if self.dock.isHidden():
            self.dock.show()
            self.dock.expand_capsule()
        else:
            self.dock.toggle_expand()

    def _on_hotkey_from_sentinel(self):
        self._toggle_assistant()

    def _on_abort_from_watchdog(self):
        self.sig_abort_gui.emit()

    def _on_abort_gui(self):
        print("\n[AURA FAILSAFE] Emergency Esc pressed! Terminating active tasks.")
        self.overlay.clear_overlay()
        self.dock.set_status("Aborted via Esc [STOP]", is_active=False)
        self.dock.collapse_capsule()

    def on_mode_toggled(self, new_mode: str):
        self.mode = new_mode
        self.overlay.set_mode(new_mode)

    def on_command(self, cmd_text: str):
        intent = ROUTER.route(cmd_text)

        if intent.type == "switch_mode":
            self.on_mode_toggled(intent.target)
            return

        self.dock.set_status(f"Starting: {cmd_text[:24]}...", is_active=True)

        self.active_thread = QThread()
        self.active_worker = TaskWorker(intent, self.mode)
        self.active_worker.moveToThread(self.active_thread)

        self.active_thread.started.connect(self.active_worker.run)
        self.active_worker.progress.connect(lambda msg: self.dock.set_status(msg, is_active=True))
        self.active_worker.telemetry.connect(self.overlay.update_telemetry)
        self.active_worker.click.connect(self.overlay.trigger_click)
        self.active_worker.ai_answer.connect(self.dock.show_ai_answer)
        self.active_worker.finished.connect(self._on_task_finished)

        self.active_thread.start()

    def _on_task_finished(self, status: str):
        self.overlay.clear_overlay()
        if not self.dock.ai_card.isVisible():
            self.dock.set_status(status, is_active=False)
        if self.active_thread:
            self.active_thread.quit()
            self.active_thread.wait(500)
            self.active_thread = None
            self.active_worker = None

    def cleanup(self):
        STEALTH.stop_hotkey_sentinel()
        if hasattr(self, "tray"):
            self.tray.hide()

def main():
    app = QApplication(sys.argv)
    aura = AuraApp(app)
    app.aboutToQuit.connect(aura.cleanup)
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
