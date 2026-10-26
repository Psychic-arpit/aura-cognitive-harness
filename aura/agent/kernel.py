"""
aura.agent.kernel - Master Contextual AI Perception Kernel
Synthesizes live OS state, active editor code, and screen captures into a zero-leak contextual prompt.
"""

import time
from typing import Dict, Any, Optional
from aura.agent.client import CLIENT
from aura.harness.perception import PERCEPTION

class OmniKernel:
    def __init__(self):
        self._visual_triggers = {
            "screen", "look", "this", "error", "traceback", "image",
            "page", "ui", "what is this", "explain this", "help me fix", "read this"
        }

    def process(self, query: str) -> Dict[str, Any]:
        q = query.strip()
        if not q:
            return {"title": "", "source": "Aura AI", "answer": "Ready for your instruction.", "elapsed": 0.0}

        t0 = time.time()
        ctx = PERCEPTION.get_context_snapshot()
        fg = ctx["window"]
        clip = ctx["clipboard"]

        # Determine if visual screen grounding is required
        q_low = q.lower()
        image_bytes: Optional[bytes] = None
        if any(trig in q_low for trig in self._visual_triggers) or q_low.startswith("explain:"):
            image_bytes = PERCEPTION.capture_screen_bytes()

        prompt = (
            f"You are Aura, an elite cybernetic desktop AI companion.\n"
            f"Active Environment Context:\n"
            f"- Foreground Application: {fg['process']} ('{fg['title'][:90]}')\n"
            f"- Category: {fg['category']}\n"
        )
        if clip:
            prompt += f"- Recent Clipboard Content:\n```{clip[:750]}```\n"

        if image_bytes:
            prompt += "- Visual State: Live screen capture attached.\n"

        prompt += (
            f"\nUser Instruction: {q}\n\n"
            f"Directives:\n"
            f"- Deliver direct, concise, copyable code or solutions without meta-explanations.\n"
            f"- Ground your answer in what the user is currently working on in {fg['process']}.\n"
            f"- Never act like a search engine or generic encyclopedia; you are a flagship desktop co-pilot."
        )

        ans = CLIENT.generate(prompt, image_bytes=image_bytes)
        elapsed = round(time.time() - t0, 2)

        source = "Aura Vision AI" if image_bytes else "Aura Context AI"
        return {
            "title": q[:36],
            "source": source,
            "answer": ans.strip(),
            "elapsed": elapsed
        }

KERNEL = OmniKernel()
