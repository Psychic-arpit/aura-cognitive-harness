"""
aura.agent.memory - Persistent Episodic Brain
Stores commands, clipboard, context patterns, and user preferences across sessions.
Jarvis knows what you've done, what you care about, and what you'll do next.
"""

import json
import os
import time
from collections import deque
from typing import Any, Dict, List, Optional

BRAIN_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "brain")
MEMORY_FILE = os.path.join(BRAIN_DIR, "memory.json")

MAX_COMMANDS = 60
MAX_CLIPBOARD = 20
MAX_CONTEXT_EVENTS = 40


def _now() -> float:
    return time.time()


class AuraMemory:
    """Persistent episodic memory — survives process restarts."""

    def __init__(self):
        os.makedirs(BRAIN_DIR, exist_ok=True)
        self._data: Dict[str, Any] = self._load()

    # ── Persistence ─────────────────────────────────────────────────────────

    def _load(self) -> Dict[str, Any]:
        if os.path.exists(MEMORY_FILE):
            try:
                with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "commands": [],
            "clipboard_history": [],
            "context_events": [],
            "app_launch_counts": {},
            "preferences": {},
            "facts": {},
            "session_start": _now(),
        }

    def _save(self):
        try:
            with open(MEMORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    # ── Commands ─────────────────────────────────────────────────────────────

    def add_command(self, query: str, answer: str, elapsed: float = 0.0):
        entry = {"q": query[:200], "a": answer[:600], "t": _now(), "ms": elapsed}
        cmds: list = self._data.setdefault("commands", [])
        cmds.append(entry)
        if len(cmds) > MAX_COMMANDS:
            self._data["commands"] = cmds[-MAX_COMMANDS:]
        self._save()

    def recent_commands(self, n: int = 8) -> List[Dict]:
        return self._data.get("commands", [])[-n:]

    def last_command(self) -> Optional[Dict]:
        cmds = self._data.get("commands", [])
        return cmds[-1] if cmds else None

    # ── Clipboard History ────────────────────────────────────────────────────

    def add_clipboard(self, text: str):
        if not text or len(text) < 3:
            return
        hist: list = self._data.setdefault("clipboard_history", [])
        # Deduplicate head
        if hist and hist[-1].get("v") == text[:300]:
            return
        hist.append({"v": text[:300], "t": _now()})
        if len(hist) > MAX_CLIPBOARD:
            self._data["clipboard_history"] = hist[-MAX_CLIPBOARD:]
        self._save()

    def recent_clipboard(self, n: int = 5) -> List[str]:
        return [e["v"] for e in self._data.get("clipboard_history", [])[-n:]]

    # ── Context Events (ambient awareness) ───────────────────────────────────

    def add_context_event(self, app: str, event: str, detail: str = ""):
        events: list = self._data.setdefault("context_events", [])
        events.append({"app": app, "event": event, "detail": detail[:120], "t": _now()})
        if len(events) > MAX_CONTEXT_EVENTS:
            self._data["context_events"] = events[-MAX_CONTEXT_EVENTS:]
        self._save()

    def recent_context(self, n: int = 6) -> List[Dict]:
        return self._data.get("context_events", [])[-n:]

    # ── App Launch Tracking ──────────────────────────────────────────────────

    def track_app_launch(self, app_name: str):
        counts: dict = self._data.setdefault("app_launch_counts", {})
        counts[app_name] = counts.get(app_name, 0) + 1
        self._save()

    def top_apps(self, n: int = 5) -> List[str]:
        counts = self._data.get("app_launch_counts", {})
        return sorted(counts, key=lambda k: counts[k], reverse=True)[:n]

    # ── Facts & Preferences ──────────────────────────────────────────────────

    def remember(self, key: str, value: Any):
        self._data.setdefault("facts", {})[key] = value
        self._save()

    def recall(self, key: str, default: Any = None) -> Any:
        return self._data.get("facts", {}).get(key, default)

    def set_preference(self, key: str, value: Any):
        self._data.setdefault("preferences", {})[key] = value
        self._save()

    def get_preference(self, key: str, default: Any = None) -> Any:
        return self._data.get("preferences", {}).get(key, default)

    # ── Context Summary for Kernel Injection ─────────────────────────────────

    def build_context_summary(self) -> str:
        """Returns a compact paragraph injected into every kernel prompt."""
        lines: List[str] = []

        recent = self.recent_commands(5)
        if recent:
            entries = "; ".join(f'"{r["q"]}"' for r in recent[-3:])
            lines.append(f"Recent user queries: {entries}.")

        clips = self.recent_clipboard(3)
        if clips:
            snippet = clips[-1][:80].replace("\n", " ")
            lines.append(f"Clipboard contains: {snippet!r}.")

        top = self.top_apps(3)
        if top:
            lines.append(f"Frequently used apps: {', '.join(top)}.")

        facts = self._data.get("facts", {})
        if facts:
            kv = "; ".join(f"{k}={v}" for k, v in list(facts.items())[:4])
            lines.append(f"Remembered facts: {kv}.")

        return " ".join(lines)


MEMORY = AuraMemory()
