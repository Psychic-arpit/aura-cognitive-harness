"""
aura.agent.kernel - Contextual AI Perception Kernel
Synthesizes live OS state, active editor code, and screen captures into a zero-leak contextual prompt.
Clean, direct, zero meta-slop or searcher behavior.
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
            return {"title": "", "source": "Response", "answer": "Ready for input.", "elapsed": 0.0}

        t0 = time.time()
        ctx = PERCEPTION.get_context_snapshot()
        fg = ctx["window"]
        clip = ctx["clipboard"]

        q_low = q.lower()
        image_bytes: Optional[bytes] = None
        if any(trig in q_low for trig in self._visual_triggers) or q_low.startswith("explain:"):
            image_bytes = PERCEPTION.capture_screen_bytes()

        prompt = (
            f"You are a high-speed, direct developer desktop co-pilot.\n"
            f"Environment Context:\n"
            f"- Focused Window: {fg['process']} ('{fg['title'][:90]}')\n"
            f"- Category: {fg['category']}\n"
        )
        if clip:
            prompt += f"- Active Clipboard:\n```{clip[:750]}```\n"

        if image_bytes:
            prompt += "- Visual Input: Live screen capture attached.\n"

        prompt += (
            f"\nInstruction: {q}\n\n"
            f"Directives:\n"
            f"- Provide exact, copyable code or solutions without meta-narrative.\n"
            f"- Ground your answer in what the user is working on in {fg['process']}.\n"
            f"- Do not use greeting fluff or unnecessary apologies; be surgically focused."
        )

        ans = CLIENT.generate(prompt, image_bytes=image_bytes)
        elapsed = round(time.time() - t0, 2)

        return {
            "title": q[:36],
            "source": "Response",
            "answer": ans.strip(),
            "elapsed": elapsed
        }

KERNEL = OmniKernel()
