"""
brain/astra_engine.py - Astra-Style Zero-Friction Desktop Intelligence
Answers Questions, Explains Code, Solves Math Directly in the Capsule HUD
Zero Need to Open Chrome for Instant Answers (< 300ms)
Multi-Tier Engine: Safe Math -> DuckDuckGo API -> Wikipedia REST -> Gemini 2.0 Flash
"""

import urllib.request
import urllib.parse
import json
import math
import re
import time
from typing import Optional, Dict, Any
from brain.api_client import API_CLIENT

class AstraEngine:
    def __init__(self):
        pass

    def solve_math(self, query: str) -> Optional[Dict[str, Any]]:
        """Safely evaluates basic arithmetic and mathematical expressions."""
        clean = query.lower().strip()
        for prefix in ["calculate ", "calc ", "what is ", "solve ", "math "]:
            if clean.startswith(prefix):
                clean = clean[len(prefix):].strip()

        clean = clean.replace("x", "*").replace("^", "**").replace("÷", "/")
        clean = clean.strip("?=").strip()

        # Handle "X% of Y"
        pct_match = re.match(r"^(\d+(?:\.\d+)?)\s*%\s*(?:of)?\s*(\d+(?:\.\d+)?)$", clean)
        if pct_match:
            pct = float(pct_match.group(1))
            val = float(pct_match.group(2))
            res = (pct / 100.0) * val
            return {
                "title": f"{pct}% of {val}",
                "source": "Math Engine",
                "answer": f"**Result**: `{res:g}`",
                "elapsed": 0.001
            }

        if not re.match(r"^[0-9\.\+\-\*\/\(\)\s\%\,]+$", clean):
            return None

        if not any(op in clean for op in ["+", "-", "*", "/", "%"]):
            return None

        try:
            safe_dict = {k: getattr(math, k) for k in dir(math) if not k.startswith("_")}
            ans = eval(clean, {"__builtins__": None}, safe_dict)
            return {
                "title": query.strip("?"),
                "source": "Math Engine",
                "answer": f"**Calculation**: `{clean}`\n\n**Result**: `{ans:g}`" if isinstance(ans, float) else f"**Calculation**: `{clean}`\n\n**Result**: `{ans}`",
                "elapsed": 0.001
            }
        except Exception:
            return None

    def answer(self, query: str) -> Dict[str, Any]:
        """
        Pure Context-Aware Visual AI Intelligence.
        Uses live active window state, clipboard content, and screen perception.
        Zero offline searcher slop, zero Google search fallbacks.
        """
        q = query.strip()
        if not q:
            return {"title": "", "source": "Aura AI", "answer": "No request provided.", "elapsed": 0}

        # 1. Instant Math calculation
        math_res = self.solve_math(q)
        if math_res:
            return math_res

        t0 = time.time()

        # 2. Ingest Live Desktop Context (Foreground App, Window Title, Clipboard)
        from brain.context_engine import CONTEXT_ENGINE
        fg = CONTEXT_ENGINE.get_foreground_window_info()
        clip = CONTEXT_ENGINE.check_clipboard_context()

        # 3. Detect if visual screen context is relevant
        image_bytes = None
        visual_triggers = ["screen", "this", "look", "error", "page", "code", "image", "ui", "what is this", "explain this"]
        if any(vt in q.lower() for vt in visual_triggers):
            try:
                from core.screen_capture import SCREEN
                image_bytes = SCREEN.capture_to_bytes()
            except Exception:
                pass

        # 4. Construct rich, context-aware prompt
        prompt = (
            f"You are Aura, an elite contextual desktop AI assistant.\n"
            f"User's Current Desktop Context:\n"
            f"- Active App: {fg['app']} ('{fg['title'][:80]}')\n"
        )
        if clip:
            prompt += f"- Active Clipboard Snippet:\n```{clip[:800]}```\n"

        prompt += (
            f"\nUser Request: {q}\n\n"
            f"Provide a direct, intelligent, and context-aware response. "
            f"If code or technical explanation is required, write concise, high-quality code. "
            f"Do not act like a search engine or quote Wikipedia; act like an intelligent co-pilot."
        )

        # 5. Query AI Brain
        ai_response = API_CLIENT.analyze_intent_or_screen(prompt, image_bytes=image_bytes)
        elapsed = round(time.time() - t0, 2)

        if not ai_response:
            ai_response = f"I evaluated your active context in **{fg['app']}**, but could not complete the query. Please retry."

        source_name = "Visual AI" if image_bytes else "Context AI"
        return {
            "title": q[:40],
            "source": f"Aura {source_name}",
            "answer": ai_response.strip(),
            "elapsed": elapsed
        }

# Global Astra singleton
ASTRA = AstraEngine()
