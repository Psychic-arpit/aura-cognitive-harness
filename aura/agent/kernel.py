"""
aura.agent.kernel - Jarvis-Level Contextual Intelligence Engine
Multi-turn conversation, persistent memory injection, Jarvis personality.
Every response is grounded in live OS state + session history.
"""

import time
from typing import Dict, Any, List, Optional

from aura.agent.client import CLIENT
from aura.agent.memory import MEMORY
from aura.harness.perception import PERCEPTION

JARVIS_SYSTEM_PROMPT = """You are AURA — a razor-sharp personal AI co-pilot running live on the user's Windows desktop.

Personality:
- Confident, concise, direct. No filler. No apologies. No "Great question!"
- Sound like a brilliant senior engineer who already knows the context.
- When you see an error, give the fix immediately — not "Here's how you can approach..."
- Anticipate the follow-up. If you explain a bug, also mention what to watch for next.
- Refer to previous conversation naturally: "Like I mentioned..." or "Following up on that..."
- Never say you're an AI, never mention your model name, never disclaim limitations.

Format rules:
- Code: fenced blocks with language tag.
- Short answers: one or two sentences max.
- Multi-step: numbered list, tight.
- Never repeat the user's question back to them.
- Never use markdown headers (###) for a 2-line answer.
"""

MAX_HISTORY = 10   # pairs kept in context window
VISUAL_TRIGGERS = {
    "screen", "look", "this", "error", "traceback", "image",
    "page", "ui", "what is this", "explain this", "help me fix", "read this",
    "show", "see", "visible", "dialog", "window"
}


class OmniKernel:
    def __init__(self):
        self._history: List[Dict[str, str]] = []   # [{role, text}, ...]
        self._world_model: Dict[str, Any] = {}

    # ── World Model (fed by AmbientIntelligence) ─────────────────────────────

    def update_world_model(self, ctx: dict):
        """Called by ambient loop — keeps a live OS snapshot."""
        self._world_model = ctx

    # ── History Management ───────────────────────────────────────────────────

    def _push(self, role: str, text: str):
        self._history.append({"role": role, "text": text})
        if len(self._history) > MAX_HISTORY * 2:
            self._history = self._history[-(MAX_HISTORY * 2):]

    def clear_history(self):
        self._history.clear()

    # ── Core Process ─────────────────────────────────────────────────────────

    def process(self, query: str, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        q = query.strip()
        if not q:
            return {"title": "", "source": "Response", "answer": "Ready.", "elapsed": 0.0}

        t0 = time.time()
        ctx = PERCEPTION.get_context_snapshot() if not self._world_model else self._world_model
        fg = ctx.get("window", {})
        clip = ctx.get("clipboard", "")

        extra = extra or {}
        q_low = q.lower()

        # Visual capture decision
        image_bytes: Optional[bytes] = None
        if extra.get("force_visual") or any(t in q_low for t in VISUAL_TRIGGERS):
            image_bytes = PERCEPTION.capture_screen_bytes()

        # ── Build system prompt ───────────────────────────────────────────────
        mem_summary = MEMORY.build_context_summary()
        os_ctx = (
            f"Current app: {fg.get('process', '?')} ('{fg.get('title', '')[:80]}') "
            f"[{fg.get('category', '?')}]"
        )
        if clip:
            os_ctx += f"\nClipboard: {clip[:300]}"
        if image_bytes:
            os_ctx += "\nScreen capture: attached."

        system = (
            f"{JARVIS_SYSTEM_PROMPT}\n\n"
            f"Live OS state:\n{os_ctx}\n\n"
            f"Session memory:\n{mem_summary or 'No prior context.'}"
        )

        # ── Build conversation turns ──────────────────────────────────────────
        turns: List[Dict] = []
        for h in self._history:
            turns.append({"role": h["role"], "text": h["text"]})
        turns.append({"role": "user", "text": q})

        # ── Call Gemini with multi-turn history ───────────────────────────────
        answer = CLIENT.generate_chat(system, turns, image_bytes=image_bytes)
        elapsed = round(time.time() - t0, 2)

        # ── Persist to memory + history ───────────────────────────────────────
        self._push("user", q)
        self._push("model", answer)
        MEMORY.add_command(q, answer, elapsed)

        return {
            "title": q[:36],
            "source": "AURA",
            "answer": answer.strip(),
            "elapsed": elapsed
        }

    # ── Ambient-triggered quick analysis ─────────────────────────────────────

    def quick_analyze(self, snippet: str, hint: str) -> str:
        """Fast one-shot analysis for ambient suggestions (error/code in clipboard)."""
        if not snippet:
            return ""
        prompt = f"[Context hint: {hint}]\n\n{snippet[:600]}"
        return CLIENT.generate_chat(JARVIS_SYSTEM_PROMPT, [{"role": "user", "text": prompt}])


KERNEL = OmniKernel()
