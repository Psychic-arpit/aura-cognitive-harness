"""
aura.agent.ambient - Proactive Ambient Intelligence Loop
Monitors OS state every 4 seconds. Surfaces context signals WITHOUT being asked.
Error dialogs, clipboard code, repeated failures — all trigger proactive help.
"""

import time
import re
from typing import Optional, Callable

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from aura.harness.perception import PERCEPTION
from aura.agent.memory import MEMORY

# ── Thresholds ────────────────────────────────────────────────────────────────

POLL_INTERVAL = 4.0           # seconds between ambient scans
CLIPBOARD_MIN_LEN = 15        # minimum clip length to care about
ERROR_KEYWORDS = {
    "traceback", "error:", "exception", "syntaxerror", "typeerror",
    "nameerror", "valueerror", "filenotfounderror", "importerror",
    "permissionerror", "keyerror", "attributeerror", "failed", "fatal"
}
CODE_PATTERNS = [
    r"def\s+\w+\(",           # Python function
    r"class\s+\w+[:\(]",      # Python/JS class
    r"import\s+\w+",          # import statement
    r"function\s+\w+\s*\(",   # JS function
    r"=>\s*\{",               # arrow function
    r"\bfor\b.+\bin\b",       # for-in loop
]

_code_re = re.compile("|".join(CODE_PATTERNS), re.IGNORECASE)


class AmbientSignals(QObject):
    suggestion = pyqtSignal(str, str)        # (message, action_hint)
    context_changed = pyqtSignal(dict)       # full ctx snapshot
    error_detected = pyqtSignal(str)         # error text
    code_in_clipboard = pyqtSignal(str)      # code text
    app_switched = pyqtSignal(str, str)      # (old_app, new_app)


class AmbientThread(QThread):
    """Background polling thread — zero UI blocking."""

    def __init__(self, signals: AmbientSignals):
        super().__init__()
        self.signals = signals
        self._running = True

        # State tracking
        self._last_app: str = ""
        self._last_clip: str = ""
        self._last_clip_time: float = 0.0
        self._error_count: int = 0
        self._last_error: str = ""
        self._clip_code_notified: bool = False

    def stop(self):
        self._running = False

    def run(self):
        while self._running:
            try:
                self._scan()
            except Exception:
                pass
            time.sleep(POLL_INTERVAL)

    def _scan(self):
        ctx = PERCEPTION.get_context_snapshot()
        fg = ctx.get("window", {})
        clip = ctx.get("clipboard", "").strip()
        app = fg.get("process", "")
        title = fg.get("title", "")

        # Emit raw context for kernel world model
        self.signals.context_changed.emit(ctx)

        # ── App switch ───────────────────────────────────────────────────────
        if app and app != self._last_app:
            if self._last_app:
                self.signals.app_switched.emit(self._last_app, app)
            MEMORY.add_context_event(app, "focused", title[:80])
            self._last_app = app

        # ── Clipboard monitoring ─────────────────────────────────────────────
        if clip and clip != self._last_clip and len(clip) >= CLIPBOARD_MIN_LEN:
            self._last_clip = clip
            self._last_clip_time = time.time()
            MEMORY.add_clipboard(clip)
            self._clip_code_notified = False

            clip_low = clip.lower()

            # Error / traceback in clipboard
            if any(kw in clip_low for kw in ERROR_KEYWORDS):
                self._error_count += 1
                self._last_error = clip
                self.signals.error_detected.emit(clip)
                if self._error_count >= 2:
                    self.signals.suggestion.emit(
                        f"You've copied this error {self._error_count}x. Want me to fix it?",
                        "fix_error"
                    )
                else:
                    self.signals.suggestion.emit("Error on clipboard — ask me to fix it.", "fix_error")
            else:
                self._error_count = 0

            # Code in clipboard
            if not self._clip_code_notified and _code_re.search(clip[:400]):
                self._clip_code_notified = True
                self.signals.code_in_clipboard.emit(clip)
                self.signals.suggestion.emit("Code copied — ask me to explain or refactor.", "explain_code")

        # ── Title-based heuristics ───────────────────────────────────────────
        title_low = title.lower()
        if "error" in title_low or "failed" in title_low or "exception" in title_low:
            self.signals.suggestion.emit(
                f"{app}: looks like an error dialog. Want help?",
                "diagnose"
            )


class AmbientIntelligence(QObject):
    """
    Public interface for the ambient system.
    Owns the thread lifecycle; exposes signals for main.py to connect.
    """

    suggestion = pyqtSignal(str, str)
    context_changed = pyqtSignal(dict)
    error_detected = pyqtSignal(str)
    code_in_clipboard = pyqtSignal(str)
    app_switched = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        self._signals = AmbientSignals()
        self._thread = AmbientThread(self._signals)

        # Bridge inner signals → public interface
        self._signals.suggestion.connect(self.suggestion)
        self._signals.context_changed.connect(self.context_changed)
        self._signals.error_detected.connect(self.error_detected)
        self._signals.code_in_clipboard.connect(self.code_in_clipboard)
        self._signals.app_switched.connect(self.app_switched)

    def start(self):
        self._thread.daemon = True
        self._thread.start()

    def stop(self):
        self._thread.stop()
        self._thread.wait(2000)


AMBIENT = AmbientIntelligence()
