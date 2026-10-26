"""
aura.agent.router - Zero-Regex-Fragility Semantic Intent Dispatcher
Resolves OS primitives, instant math, turbo platform navigators, and autonomous goals in < 0.05ms.
"""

import re
import math
import urllib.parse
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any

@dataclass
class Intent:
    type: str  # 'system_control', 'math_eval', 'turbo_nav', 'autonomous_goal', 'app_launch', 'context_ai', 'clean_temp', 'switch_mode'
    target: str = ""
    extra: Optional[Dict[str, Any]] = None

class SemanticRouter:
    def __init__(self):
        self._math_allowed = set("0123456789.+-*/()%^= ")

    def _eval_math(self, text: str) -> Optional[str]:
        t = text.strip().lower()
        for p in ["calculate ", "calc ", "what is ", "solve ", "math "]:
            if t.startswith(p):
                t = t[len(p):].strip()

        # Percentage 'X% of Y'
        m_pct = re.match(r"^(\d+(?:\.\d+)?)\s*%\s*(?:of)?\s*(\d+(?:\.\d+)?)$", t)
        if m_pct:
            res = (float(m_pct.group(1)) / 100.0) * float(m_pct.group(2))
            return f"{res:g}"

        t_clean = t.replace("x", "*").replace("^", "**").replace("÷", "/").strip("?=").strip()
        if not t_clean or not any(op in t_clean for op in ["+", "-", "*", "/", "%", "**"]):
            return None

        if all(c in self._math_allowed for c in t_clean):
            try:
                safe_math = {k: getattr(math, k) for k in dir(math) if not k.startswith("_")}
                val = eval(t_clean, {"__builtins__": None}, safe_math)
                return f"{val:g}" if isinstance(val, float) else f"{val}"
            except Exception:
                pass
        return None

    def _clean_query(self, text: str, kw_list: list) -> str:
        for kw in kw_list:
            m = re.search(rf"search\s+(.+?)\s+(?:on|in)\s+{kw}", text, re.IGNORECASE)
            if m:
                return m.group(1).strip()
        q = text
        for kw in kw_list:
            q = re.sub(rf"\b{re.escape(kw)}(?:\.com)?\b", "", q, flags=re.IGNORECASE)
        q = re.sub(r"^(?:open|go to|search for|search|find|solve|watch|play|run)\b", "", q.strip(), flags=re.IGNORECASE).strip()
        q = re.sub(r"^(?:and\s+)?(?:search for|search|find|solve|watch|play)\b", "", q.strip(), flags=re.IGNORECASE).strip()
        q = re.sub(r"^(?:for|on|in|about)\b", "", q.strip(), flags=re.IGNORECASE).strip()
        return q.strip()

    def _match_turbo_platform(self, text: str) -> Optional[Intent]:
        t = text.strip()
        t_low = t.lower()

        if "instagram" in t_low:
            q = self._clean_query(t, ["instagram"])
            if q and q.lower() not in ["website", "site", "app"]:
                return Intent(type="turbo_nav", target=f"https://www.instagram.com/explore/search/keyword/?q={urllib.parse.quote(q)}")
            return Intent(type="turbo_nav", target="https://www.instagram.com")

        if "youtube" in t_low:
            if "shorts" in t_low and any(w in t_low for w in ["play", "watch", "click", "mouse"]):
                return Intent(type="turbo_nav", target="https://www.youtube.com/shorts")
            q = self._clean_query(t, ["youtube"])
            if q and q.lower() not in ["website", "site", "app"]:
                return Intent(type="turbo_nav", target=f"https://www.youtube.com/results?search_query={urllib.parse.quote(q)}")
            return Intent(type="turbo_nav", target="https://www.youtube.com")

        if "leetcode" in t_low:
            q = self._clean_query(t, ["leetcode"])
            if q and q.lower() not in ["website", "site", "app"]:
                return Intent(type="turbo_nav", target=f"https://leetcode.com/problemset/?search={urllib.parse.quote(q)}")
            return Intent(type="turbo_nav", target="https://leetcode.com")

        if "github" in t_low:
            q = self._clean_query(t, ["github"])
            if q and q.lower() not in ["website", "site", "app"]:
                return Intent(type="turbo_nav", target=f"https://github.com/search?q={urllib.parse.quote(q)}")
            return Intent(type="turbo_nav", target="https://github.com")

        if re.search(r"\b(?:gfg|geeksforgeeks)\b", t_low):
            q = self._clean_query(t, ["gfg", "geeksforgeeks"])
            if q and q.lower() not in ["website", "site", "app"]:
                return Intent(type="turbo_nav", target=f"https://www.google.com/search?q=site:geeksforgeeks.org+{urllib.parse.quote(q)}")
            return Intent(type="turbo_nav", target="https://www.geeksforgeeks.org")

        if "reddit" in t_low:
            q = self._clean_query(t, ["reddit"])
            if q and q.lower() not in ["website", "site", "app"]:
                return Intent(type="turbo_nav", target=f"https://www.reddit.com/search/?q={urllib.parse.quote(q)}")
            return Intent(type="turbo_nav", target="https://www.reddit.com")

        if re.search(r"\b(?:twitter|x\.com)\b", t_low):
            q = self._clean_query(t, ["twitter", "x.com", "x"])
            if q and q.lower() not in ["website", "site", "app"]:
                return Intent(type="turbo_nav", target=f"https://x.com/search?q={urllib.parse.quote(q)}")
            return Intent(type="turbo_nav", target="https://x.com")

        # Direct URLs
        if re.match(r"^(https?://|www\.)[^\s]+$|^[a-zA-Z0-9-]+\.(?:com|org|net|io|dev|app|in)(/[^\s]*)?$", t):
            url = t if t.startswith("http") else f"https://{t}"
            return Intent(type="turbo_nav", target=url)

        return None

    def route(self, text: str) -> Intent:
        t = text.strip()
        if not t:
            return Intent(type="unknown")

        t_low = t.lower()

        # 1. Hardware & OS controls
        if t_low in ["mute", "unmute", "volume up", "volume down", "lock", "lock screen", "show desktop", "minimize all"]:
            return Intent(type="system_control", target=t_low)

        if "clean" in t_low and any(w in t_low for w in ["temp", "cache", "disk"]):
            return Intent(type="clean_temp")

        if any(w in t_low for w in ["dark mode", "light mode", "obsidian mode"]):
            mode = "dark" if "dark" in t_low or "obsidian" in t_low else "light"
            return Intent(type="system_control", target=f"theme_{mode}")

        if t_low in ["mach", "bio", "switch mode", ":mach", ":bio"]:
            return Intent(type="switch_mode", target="biomimetic" if "bio" in t_low else "mach")

        # 2. Instant Math (< 0.01ms)
        math_res = self._eval_math(t)
        if math_res is not None:
            return Intent(type="math_eval", target=math_res, extra={"expression": t})

        # 3. Direct Turbo Platform Navigation
        turbo = self._match_turbo_platform(t)
        if turbo:
            return turbo

        # 4. Multi-Step Physical GUI Sequences
        action_verbs = ["click", "type", "press", "scroll", "select", "tap", "drag", "fill"]
        has_action = any(v in t_low for v in action_verbs)
        has_chaining = any(c in t_low for c in [" and then ", " then ", " and click", " and type", " and open"])
        if has_action and (has_chaining or len(t.split()) > 5):
            return Intent(type="autonomous_goal", target=t)

        # 5. App Launches
        for prefix in ["open ", "launch ", "start "]:
            if t_low.startswith(prefix):
                app_target = t[len(prefix):].strip()
                return Intent(type="app_launch", target=app_target)

        # 6. Contextual AI Vision & Reasoning
        return Intent(type="context_ai", target=t)

    def get_preview(self, text: str) -> Tuple[str, str]:
        t = text.strip()
        if not t:
            return "⚡ AURA PILOT", "#10B981"

        intent = self.route(t)
        mapping = {
            "turbo_nav": ("🚀 TURBO NAV", "#3B82F6"),
            "autonomous_goal": ("🧠 AUTONOMOUS AGENT", "#8B5CF6"),
            "app_launch": (f"🚀 LAUNCH {intent.target.upper()[:12]}", "#00F0FF"),
            "system_control": (f"⚙️ SYSTEM ({intent.target.upper()[:10]})", "#F59E0B"),
            "math_eval": (f"= {intent.target}", "#10B981"),
            "clean_temp": ("🧹 CLEAN TEMP", "#10B981"),
            "context_ai": ("🧠 CONTEXT AI", "#00F0FF")
        }
        return mapping.get(intent.type, ("⚡ AURA PILOT", "#10B981"))

ROUTER = SemanticRouter()
