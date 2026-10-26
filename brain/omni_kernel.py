"""
brain/omni_kernel.py - Master Contextual AI & Vision Perception Kernel
Injects live OS state, active window metadata, and real-time screen captures into the AI Brain.
Replaces brittle search engines with true desktop intelligence.
"""

import time
from typing import Dict, Any, Optional
from brain.api_client import API_CLIENT
from brain.context_engine import CONTEXT_ENGINE

class OmniKernel:
    def __init__(self):
        self.visual_triggers = {
            "screen", "look", "this", "error", "traceback", "image", 
            "page", "ui", "what is this", "explain this", "help me fix", "read this"
        }

    def process(self, query: str) -> Dict[str, Any]:
        """Processes a contextual query or visual analysis request."""
        q = query.strip()
        if not q:
            return {"title": "", "source": "Aura AI", "answer": "Ready for your instruction.", "elapsed": 0}

        t0 = time.time()

        # 1. Gather active OS perception
        fg = CONTEXT_ENGINE.get_foreground_window_info()
        clip = CONTEXT_ENGINE.check_clipboard_context()

        # 2. Check if screen capture is needed
        image_bytes = None
        q_low = q.lower()
        if any(trig in q_low for trig in self.visual_triggers) or q_low.startswith("explain:"):
            image_bytes = CONTEXT_ENGINE.capture_visual_context()

        # 3. Construct rich contextual prompt
        prompt = (
            f"You are Aura, an elite cybernetic desktop AI companion.\n"
            f"Current Environment Context:\n"
            f"- Foreground Application: {fg['app']} ('{fg['title'][:90]}')\n"
            f"- Category: {fg.get('category', 'general')}\n"
        )
        if clip:
            prompt += f"- Recent Clipboard Content:\n```{clip[:750]}```\n"

        if image_bytes:
            prompt += "- Visual State: Live screen capture attached.\n"

        prompt += (
            f"\nUser Instruction: {q}\n\n"
            f"Instructions for response:\n"
            f"- Be direct, concise, and highly intelligent.\n"
            f"- If answering code or errors, provide exact, copyable code fixes.\n"
            f"- Ground your answer in what the user is currently looking at in {fg['app']}.\n"
            f"- Never act like an offline encyclopedia or search engine; be a high-performance co-pilot."
        )

        # 4. Dispatch to Brain
        ans = API_CLIENT.analyze_intent_or_screen(prompt, image_bytes=image_bytes)
        elapsed = round(time.time() - t0, 2)

        if not ans or not ans.strip():
            ans = f"Analyzed active context in **{fg['app']}**, but received an empty response. Please retry."

        source = "Aura Vision AI" if image_bytes else "Aura Context AI"
        return {
            "title": q[:36],
            "source": source,
            "answer": ans.strip(),
            "elapsed": elapsed
        }

OMNI_KERNEL = OmniKernel()
