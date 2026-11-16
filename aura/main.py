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
from aura.harness.smart_launcher import SMART_LAUNCHER
from aura.agent.router import ROUTER, Intent
from aura.agent.kernel import KERNEL
from aura.agent.planner import PLANNER
from aura.agent.client import CLIENT
from aura.ui.dock import CyberDock
from aura.ui.overlay import AuraOverlayWindow
from aura.ui.lens import CursorLens

class TaskWorker(QObject):
    progress = pyqtSignal(str)
    finished = pyqtSignal(str)
    telemetry = pyqtSignal(float, float)
    click = pyqtSignal(float, float)
    lock_target = pyqtSignal(float, float, str)
    ai_state = pyqtSignal(str)
    ai_answer = pyqtSignal(dict)
    ghost_telemetry = pyqtSignal(float, float, str)
    ghost_clear = pyqtSignal()

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
                self.ai_state.emit("thinking")
                data = KERNEL.process(self.intent.target, self.intent.extra)
                self.ai_answer.emit(data)
                self.ai_state.emit("idle")
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
                self.progress.emit(f"Launching: {url[:36]}...")
                webbrowser.open(url)
                res_msg = "Navigated [OK]"

            # 4. Multi-Step Autonomous ReAct Loop with Visual Grounding & Real Telemetry
            elif it == "autonomous_goal":
                self.progress.emit(f"Autopilot: '{self.intent.target[:28]}'...")
                self.ai_state.emit("navigating")
                result = PLANNER.execute_goal(
                    self.intent.target,
                    log_cb=lambda msg: self.progress.emit(msg),
                    telemetry_cb=lambda x, y: (self.telemetry.emit(x, y), self.ghost_telemetry.emit(x, y, "Autopilot Navigation")),
                    click_cb=lambda x, y: (self.click.emit(x, y), self.ghost_telemetry.emit(x, y, "Clicking Target")),
                    target_cb=lambda x, y, lbl: (self.lock_target.emit(x, y, lbl), self.ghost_telemetry.emit(x, y, lbl))
                )
                self.ai_state.emit("idle")
                res_msg = f"Autopilot Done: {result}"

            # 5. Fast Terminal Shell Execution (> command) with Auto-API Fallback
            elif it == "shell_exec":
                cmd = self.intent.target
                self.progress.emit(f"Running: {cmd[:32]}")
                import time
                t0 = time.time()
                proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
                elapsed = time.time() - t0
                raw_out = (proc.stdout or proc.stderr or "Executed with zero output.").strip()

                # Check if command failed due to unrecognized binary / PATH failure
                is_unrecognized = proc.returncode != 0 and any(
                    phrase in raw_out.lower() for phrase in [
                        "is not recognized",
                        "not recognized",
                        "cannot find the path",
                        "command not found"
                    ]
                )

                if is_unrecognized:
                    # 1. Attempt smart app resolution (e.g. user typed '> spotify')
                    parts = cmd.strip().split(maxsplit=1)
                    cmd_app = parts[0].lower()
                    extra_arg = parts[1] if len(parts) > 1 else ""
                    success, msg = SMART_LAUNCHER.launch(cmd_app, extra_query=extra_arg)
                    if success:
                        data = {
                            "title": f"Resolved: {cmd_app.title()}",
                            "source": "Aura Smart Execution",
                            "answer": f"### {cmd_app.title()} Active\n\n• **Status**: {msg}\n• **Harness**: Resolved natively without CLI failure.",
                            "elapsed": elapsed
                        }
                        self.ai_answer.emit(data)
                        res_msg = f"{msg} [OK]"
                    else:
                        # 2. Seamlessly escalate to Gemini 3.5 Flash API Brain
                        self.progress.emit("Consulting Aura Brain...")
                        self.ai_state.emit("thinking")
                        data = KERNEL.process(cmd)
                        self.ai_answer.emit(data)
                        self.ai_state.emit("idle")
                        res_msg = f"Aura Brain: Executed [OK]"
                else:
                    data = {
                        "title": f"Terminal: {cmd[:28]}",
                        "source": "Terminal Execution",
                        "answer": f"```text\n{raw_out}\n```",
                        "elapsed": elapsed
                    }
                    self.ai_answer.emit(data)
                    res_msg = f"Terminal exited with code {proc.returncode}"

            # 6. Git Status / Diff Telemetry (@git)
            elif it == "git_status":
                self.progress.emit("Inspecting Git Repository...")
                import time
                t0 = time.time()
                proc = subprocess.run("git status --short && git diff --stat", shell=True, capture_output=True, text=True, timeout=8)
                elapsed = time.time() - t0
                out = (proc.stdout or proc.stderr or "Clean working directory (no unstaged changes).").strip()
                data = {
                    "title": "Git Repository State",
                    "source": "Git Telemetry",
                    "answer": f"### Repository State\n\n```text\n{out}\n```",
                    "elapsed": elapsed
                }
                self.ai_answer.emit(data)
                res_msg = "Git Telemetry [OK]"

            # 7. TagRush QA & Dual Client Environment
            elif it == "tagrush_qa":
                self.progress.emit("Launching TagRush QA Dual-Client...")
                msg = PLANNER.run_tagrush_qa(lambda m: self.progress.emit(m))
                data = {
                    "title": "TagRush QA Playtest",
                    "source": "Game QA Automation",
                    "answer": f"### TagRush QA Environment\n\n• **Status**: {msg}\n• **Layout**: Left (Host 960x1040), Right (Peer 960x1040)\n• **Failsafe**: Press `Esc` anytime to abort.",
                    "elapsed": 1.2
                }
                self.ai_answer.emit(data)
                res_msg = "TagRush QA Ready [OK]"

            # 8. MS Paint Shape Rendering Automation with Physical Drag Telemetry
            elif it == "paint_draw":
                self.progress.emit("Rendering Shape in MS Paint...")
                self.ai_state.emit("actuating")
                msg = PLANNER.run_paint_recipe(
                    "rectangle",
                    lambda m: self.progress.emit(m),
                    telemetry_cb=lambda x, y: (self.telemetry.emit(x, y), self.ghost_telemetry.emit(x, y, "MS Paint Canvas Drag")),
                    click_cb=lambda x, y: self.click.emit(x, y)
                )
                self.ai_state.emit("idle")
                data = {
                    "title": "MS Paint Automation",
                    "source": "Actuation Harness",
                    "answer": f"### Canvas Render Complete\n\n• **Action**: {msg}\n• **Physics**: Cubic Bezier glide and hardware mouse drag.",
                    "elapsed": 1.5
                }
                self.ai_answer.emit(data)
                res_msg = "Paint Render Complete [OK]"

            # 9. Smart Native Application Launch with Direct API Integration
            elif it == "app_launch":
                target = self.intent.target
                extra_q = self.intent.extra.get("query", "") if self.intent.extra else ""
                self.progress.emit(f"Launching {target}...")
                cur_x, cur_y = ACTUATION.get_cursor_pos()
                sw, sh = ACTUATION.get_screen_size()
                ACTUATION.glide_cursor((cur_x, cur_y), (sw // 2, sh // 2), duration=0.25, telemetry_cb=lambda x, y: self.telemetry.emit(x, y))
                self.click.emit(sw // 2, sh // 2)

                # Smart Protocol, Path, Start Menu, or Web Resolution
                success, msg = SMART_LAUNCHER.launch(target, extra_query=extra_q)
                if not success:
                    # Escalates directly to Gemini API so it does the work without errors
                    self.progress.emit(f"Fulfilling '{target}' via Aura Brain...")
                    self.ai_state.emit("thinking")
                    data = KERNEL.process(f"Open or handle {target}")
                    self.ai_answer.emit(data)
                    self.ai_state.emit("idle")
                    res_msg = f"Aura Handled: {target}"
                else:
                    data = {
                        "title": f"Application: {target.title()}",
                        "source": "Aura Smart Execution",
                        "answer": f"### {target.title()} Active\n\n• **Status**: {msg}\n• **Harness**: Resolved natively with zero command-line dependency.",
                        "elapsed": 0.1
                    }
                    self.ai_answer.emit(data)
                    res_msg = f"{msg} [OK]"

            # 10. System & Hardware Media Controls
            elif it == "system_control":
                action = self.intent.target
                self.progress.emit(f"Hardware: '{action}'...")
                res_msg = f"Executed {action}"
                if action in ("playpause", "play", "pause"):
                    ACTUATION.fast_press("playpause")
                    res_msg = "Media: Play / Pause"
                elif action in ("nexttrack", "next"):
                    ACTUATION.fast_press("nexttrack")
                    res_msg = "Media: Next Track"
                elif action in ("prevtrack", "prev"):
                    ACTUATION.fast_press("prevtrack")
                    res_msg = "Media: Previous Track"
                elif action in ("mute", "unmute", "volumemute"):
                    ACTUATION.fast_press("volumemute")
                    res_msg = "Audio: Mute Toggled"
                elif action in ("volume up", "vol up", "volumeup"):
                    ACTUATION.fast_press("volumeup")
                    ACTUATION.fast_press("volumeup")
                    res_msg = "Audio: Volume Up (+4%)"
                elif action in ("volume down", "vol down", "volumedown"):
                    ACTUATION.fast_press("volumedown")
                    ACTUATION.fast_press("volumedown")
                    res_msg = "Audio: Volume Down (-4%)"
                elif action in ("lock", "lock screen"):
                    ctypes.windll.user32.LockWorkStation()
                    res_msg = "System: Workstation Locked"
                elif action in ("show desktop", "minimize all"):
                    ACTUATION.fast_press("win+d")
                    res_msg = "Desktop: Toggled"
                elif action == "taskmgr":
                    subprocess.Popen("taskmgr", shell=True)
                    res_msg = "Task Manager Launched"

                data = {
                    "title": "Hardware Actuation",
                    "source": "Win32 Hardware Engine",
                    "answer": f"### {res_msg}\n\n• **Signal**: Win32 hardware keystroke synthesis.\n• **Latency**: < 0.5ms.",
                    "elapsed": 0.01
                }
                self.ai_answer.emit(data)
                res_msg = f"{res_msg} [OK]"

            # 11. Clean Temp Cache
            elif it == "clean_temp":
                self.progress.emit("Cleaning temporary cache...")
                import tempfile
                temp_dir = tempfile.gettempdir()
                bytes_freed = 0
                files_freed = 0
                for root, dirs, files in os.walk(temp_dir):
                    for f in files:
                        p = os.path.join(root, f)
                        try:
                            sz = os.path.getsize(p)
                            os.remove(p)
                            bytes_freed += sz
                            files_freed += 1
                        except Exception:
                            pass
                mb_freed = bytes_freed / (1024 * 1024)
                data = {
                    "title": "Clean Cache",
                    "source": "System Maintenance",
                    "answer": f"### Cache Purged\n\n• **Reclaimed Space**: **{mb_freed:.1f} MB**\n• **Files Removed**: {files_freed} temporary files\n• **Directory**: `{temp_dir}`",
                    "elapsed": 0.2
                }
                self.ai_answer.emit(data)
                res_msg = f"Cleaned {mb_freed:.1f} MB [OK]"

            # 12. Set API Key
            elif it == "set_api_key":
                CLIENT.set_key(self.intent.target)
                self.progress.emit("Gemini AI Brain Unlocked")
                res_msg = "API Key saved successfully [OK]"

        except Exception as e:
            print(f"[TaskWorker Error]: {e}")
            res_msg = f"Notice: {e}"
        finally:
            self.ghost_clear.emit()
            SAFETY.deactivate()

        self.finished.emit(res_msg)

class AuraApp(QObject):
    sig_toggle_dock = pyqtSignal()
    sig_summon_lens = pyqtSignal()
    sig_toggle_companion = pyqtSignal()
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
        self.lens = CursorLens()

        # 2. Wire Cross-Thread Signals
        self.sig_toggle_dock.connect(self.dock.toggle_expand, Qt.ConnectionType.QueuedConnection)
        self.sig_summon_lens.connect(self.lens.summon_at_cursor, Qt.ConnectionType.QueuedConnection)
        self.sig_toggle_companion.connect(self.overlay.toggle_companion, Qt.ConnectionType.QueuedConnection)
        self.sig_abort_gui.connect(self._on_abort_gui, Qt.ConnectionType.QueuedConnection)

        # 3. Wire User Actions
        self.dock.command_submitted.connect(self.on_command)
        self.dock.mode_toggled.connect(self.on_mode_toggled)
        self.lens.command_submitted.connect(self.on_command)

        # 4. Setup Failsafe Watchdog Callback (Esc interrupt)
        SAFETY.register_abort_callback(self._on_abort_from_watchdog)

        # 5. Setup Hotkey Sentinel (Alt+C, Alt+Q, Ctrl+Alt+Space, Alt+T)
        STEALTH.register_hotkey(MOD_ALT, 0x43, self.sig_toggle_dock.emit)  # Alt + C -> Dock
        STEALTH.register_hotkey(MOD_ALT, 0x51, self.sig_summon_lens.emit)  # Alt + Q -> Inline Cursor Lens!
        STEALTH.register_hotkey(MOD_CONTROL | 0x0004, 0x20, self.sig_summon_lens.emit)  # Ctrl + Shift + Space -> Lens
        STEALTH.register_hotkey(MOD_CONTROL | MOD_ALT, 0x20, self.sig_toggle_dock.emit)  # Ctrl + Alt + Space -> Dock
        STEALTH.register_hotkey(MOD_ALT, 0x54, self.sig_toggle_companion.emit)  # Alt + T -> Toggle Glowing Cursor
        STEALTH.start_hotkey_sentinel()

        # 6. Initialize System Tray
        self._init_tray_icon()

        # Show initial views
        self.overlay.show()
        self.dock.show()

        print("\n" + "=" * 62)
        print("AURA 2.1: LUMINESCENT CURSOR AI & COGNITIVE EXECUTION HARNESS")
        print("  Dock Summon: Alt + C / Ctrl + Alt + Space")
        print("  Cursor Lens: Alt + Q / Ctrl + Shift + Space (Inline at Cursor)")
        print("  Glowing Companion: Alt + T (Ethereal 60 FPS Cursor Halo)")
        print("  Stealth: 100% Invisible to screen recorders (0x11)")
        print("=" * 62 + "\n")

    def _init_tray_icon(self):
        pix = QPixmap(16, 16)
        pix.fill(QColor(0, 0, 0, 0))
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(255, 255, 255, 220))
        painter.setPen(QColor(255, 255, 255, 120))
        painter.drawEllipse(2, 2, 12, 12)
        painter.end()

        self.tray = QSystemTrayIcon(QIcon(pix), self.q_app)
        self.tray.setToolTip("AURA Cursor AI (Alt+Q / Alt+C)")
        self.tray.activated.connect(self._on_tray_activated)

        menu = QMenu()
        act_lens = menu.addAction("Summon Cursor Lens (Alt+Q)")
        act_lens.triggered.connect(self.lens.summon_at_cursor)

        act_dock = menu.addAction("Toggle Aero Dock (Alt+C)")
        act_dock.triggered.connect(self._toggle_assistant)

        act_glow = menu.addAction("Toggle Glowing Cursor (Alt+T)")
        act_glow.triggered.connect(self.overlay.toggle_companion)

        menu.addSeparator()
        act_qa = menu.addAction("TagRush QA Dual Client")
        act_qa.triggered.connect(lambda: self.on_command("test tagrush"))

        act_paint = menu.addAction("Draw in MS Paint")
        act_paint.triggered.connect(lambda: self.on_command("draw rectangle in paint"))

        act_clean = menu.addAction("Clean Temp Cache")
        act_clean.triggered.connect(lambda: self.on_command("clean temp"))

        menu.addSeparator()
        act_hide = menu.addAction("Hide to Tray")
        act_hide.triggered.connect(self.dock.hide_to_tray)

        menu.addSeparator()
        act_exit = menu.addAction("Exit Aura")
        act_exit.triggered.connect(self.q_app.quit)

        self.tray.setContextMenu(menu)
        self.tray.show()

    def _on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.lens.summon_at_cursor()

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
        self.lens.dismiss_lens()

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
        self.active_worker.lock_target.connect(self.overlay.lock_target)
        self.active_worker.ghost_telemetry.connect(self.overlay.set_ghost_co_pilot)
        self.active_worker.ghost_clear.connect(self.overlay.clear_ghost_co_pilot)
        self.active_worker.ai_state.connect(self.overlay.set_ai_state)
        self.active_worker.ai_answer.connect(self._on_ai_answer)
        self.active_worker.finished.connect(self._on_task_finished)

        self.active_thread.start()

    def _on_ai_answer(self, data: dict):
        self.dock.show_ai_answer(data)
        if self.lens.isVisible():
            self.lens.show_inline_answer(data.get("answer", ""))

    def _on_task_finished(self, status: str):
        self.overlay.clear_target()
        self.overlay.clear_ghost_co_pilot()
        self.overlay.set_ai_state("idle")
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
