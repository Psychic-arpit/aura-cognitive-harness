"""
brain/local_router.py - Zero-Latency Local Intent Router & Astra Classifier
Dispatches 95% of Desktop Commands in < 0.1ms with Zero API Calls
Routes Universal Apps, Hardware System Controls, Astra Inline Knowledge, and Autopilot
"""

import re
from dataclasses import dataclass
from typing import Optional, Any, Tuple
from automation.app_launcher import APP_LAUNCHER

@dataclass
class RouteIntent:
    intent_type: str        # 'app_launch', 'system_control', 'astra_inline_query', 'folder_open', 'tagrush_qa', 'whatsapp_open', 'web_search', 'url_open', 'switch_mode', 'clean_temp', 'browser_debug', 'youtube_shorts', 'youtube_play', 'youtube_next', 'ai_query', 'unknown'
    target: str = ""
    extra: dict = None

class LocalRouter:
    def __init__(self):
        # 1. Automation routines
        self.tagrush_pattern = re.compile(r"(?:tagrush|tag\s*rush|qa\s*tag|multiplayer\s*test|dual\s*qa|:qa)", re.IGNORECASE)
        self.whatsapp_pattern = re.compile(r"(?:whatsapp|wa|message|chat|:wa)\b(?:\s*(?:and\s*)?(?:open|select|to)\s*(.+))?", re.IGNORECASE)
        self.mode_pattern = re.compile(r"(?:^(?:mach|bio|biomimetic)$|mode\s*(?:mach|bio|biomimetic)|switch\s*to\s*(?:mach|bio|biomimetic)|:(?:mach|bio))", re.IGNORECASE)
        self.clean_pattern = re.compile(r"(?:clean\s*(?:temp|disk|cache)|:clean|free\s*space)", re.IGNORECASE)
        self.cdp_pattern = re.compile(r"^(?:(?:start|enable|launch|open)?\s*(?:cdp|browser\s*debug|debug\s*browser)|:cdp)$", re.IGNORECASE)
        self.theme_pattern = re.compile(r"(?:(?:activate|set|change|toggle)\s*(?:theme\s*to\s*)?(dark|light|obsidian)\s*mode|start\s*coding\s*mode)", re.IGNORECASE)

        # 2. YouTube Autopilot
        self.yt_shorts_pattern = re.compile(
            r"(?:(?:go\s*to|open|launch)?\s*youtube\s*(?:and\s*)?(?:click|play|watch|open)\s*(?:on\s*)?(?:a\s*)?shorts?|"
            r"(?:click|play|watch|open)\s*(?:on\s*)?(?:a\s*)?(?:youtube\s*)?shorts?(?:\s*video)?|"
            r"^(?:youtube\s*)?shorts?$|"
            r"shorts?\s*video)",
            re.IGNORECASE
        )
        self.yt_play_pattern = re.compile(
            r"(?:play\s+(.+?)\s+on\s+youtube|"
            r"(?:go\s*to|open)\s+youtube\s+(?:and\s+)?(?:play|watch|search\s*for)\s+(.+))",
            re.IGNORECASE
        )
        self.yt_next_pattern = re.compile(r"^(?:next\s*short|next\s*video|scroll\s*down)$", re.IGNORECASE)

        # 3. System Hardware & Workspace Controls
        self.system_control_pattern = re.compile(
            r"^(?:mute|unmute|vol(?:ume)?\s*(?:up|down|increase|decrease|\d+%)?|"
            r"lock(?:\s*screen|\s*workstation)?|empty\s*(?:recycle\s*bin|trash|bin)|"
            r"show\s*desktop|minimize\s*all|snap\s*(?:left|right)|maximize(?:\s*window)?|"
            r"media\s*(?:play|pause|next|prev)|play\s*pause|next\s*track|prev(?:ious)?\s*track)$",
            re.IGNORECASE
        )

        # 4. Folders
        self.folder_pattern = re.compile(r"^(?:open\s+)?(downloads|desktop|documents|scratch|pictures|music|videos)(?:\s*folder)?$", re.IGNORECASE)

        # 5. Queries & Knowledge (Astra Inline - No Chrome!)
        self.question_pattern = re.compile(
            r"^(?:what\s+is|what\s+are|who\s+is|who\s+are|how\s+to|how\s+do|why\s+does|why\s+is|define|explain|tell\s+me\s+about)\b|\?$",
            re.IGNORECASE
        )
        self.math_pattern = re.compile(r"^(?:calc(?:ulate)?\s+|math\s+)?[\d\.\+\-\*\/\(\)\^\%\s\÷\=]+$")

        # 6. Explicit search & AI
        self.search_prefix = re.compile(r"^(?:search|google|find|lookup|ddg)\s+(?:for\s+)?(.+)", re.IGNORECASE)
        self.ai_pattern = re.compile(r"^(?:ai|gemini|ask)\s*[:\s]\s*(.+)", re.IGNORECASE)
        self.yt_pattern = re.compile(r"^(?:yt|youtube)\s+(.+)", re.IGNORECASE)
        self.gh_pattern = re.compile(r"^(?:gh|github)\s+(.+)", re.IGNORECASE)
        self.url_pattern = re.compile(r"^(https?://|www\.)[^\s]+$|^[a-zA-Z0-9-]+\.(?:com|org|net|io|dev|app|edu|gov|co|in|me)(/[^\s]*)?$", re.IGNORECASE)
        self.auto_pattern = re.compile(r"^(?:auto|goal|agent)\s*[:\s]\s*(.+)", re.IGNORECASE)
        self.api_pattern = re.compile(r"^(?:api|set\s*key)\s*[:\s]\s*(.+)", re.IGNORECASE)

    def _match_turbo_platform(self, text: str) -> Optional[RouteIntent]:
        """Direct, high-speed resolution (<0.05ms) for top web platforms without relying on search fallback."""
        import urllib.parse
        t = text.strip()
        t_low = t.lower()

        # 1. Instagram: "open instagram and search X", "search X on instagram", "open instagram"
        if "instagram" in t_low:
            m_rev = re.search(r"search\s+(.+?)\s+(?:on|in)\s+instagram", t, re.IGNORECASE)
            m_fwd = re.search(r"instagram(?:\.com)?\s*(?:and\s*)?(?:search|find|for|watch|video)\s+(.+)", t, re.IGNORECASE)
            m_any = re.search(r"(?:search|find|watch)\s+(?:for\s+)?(.+?)(?:\s+on\s+instagram|\s+in\s+instagram|$)", t, re.IGNORECASE)
            q = ""
            if m_rev: q = m_rev.group(1).strip()
            elif m_fwd: q = m_fwd.group(1).strip()
            elif m_any and "instagram" not in m_any.group(1).lower(): q = m_any.group(1).strip()

            if q:
                return RouteIntent(intent_type="url_open", target=f"https://www.instagram.com/explore/search/keyword/?q={urllib.parse.quote(q)}")
            return RouteIntent(intent_type="url_open", target="https://www.instagram.com")

        # 2. LeetCode
        if "leetcode" in t_low:
            m = re.search(r"(?:search|find|solve|problem)\s+(.+?)(?:\s+on\s+leetcode|$)", t, re.IGNORECASE)
            if m and "leetcode" not in m.group(1).lower():
                q = m.group(1).strip()
                return RouteIntent(intent_type="url_open", target=f"https://leetcode.com/problemset/?search={urllib.parse.quote(q)}")
            return RouteIntent(intent_type="url_open", target="https://leetcode.com")

        # 3. GeeksforGeeks
        if re.search(r"\b(?:gfg|geeksforgeeks)\b", t_low):
            m = re.search(r"(?:search|find)\s+(.+?)(?:\s+on\s+(?:gfg|geeksforgeeks)|$)", t, re.IGNORECASE)
            q = m.group(1).strip() if m else t
            q = re.sub(r"\b(?:gfg|geeksforgeeks|website|site)\b", "", q, flags=re.IGNORECASE).strip()
            return RouteIntent(intent_type="web_search", target=f"site:geeksforgeeks.org {q}")

        # 4. GitHub
        if "github" in t_low:
            m = re.search(r"(?:search|find|repo)\s+(.+?)(?:\s+on\s+github|$)", t, re.IGNORECASE)
            if m and "github" not in m.group(1).lower():
                q = m.group(1).strip()
                return RouteIntent(intent_type="url_open", target=f"https://github.com/search?q={urllib.parse.quote(q)}")
            return RouteIntent(intent_type="url_open", target="https://github.com")

        # 5. Reddit
        if "reddit" in t_low:
            m = re.search(r"(?:search|find)\s+(.+?)(?:\s+on\s+reddit|$)", t, re.IGNORECASE)
            if m and "reddit" not in m.group(1).lower():
                q = m.group(1).strip()
                return RouteIntent(intent_type="url_open", target=f"https://www.reddit.com/search/?q={urllib.parse.quote(q)}")
            return RouteIntent(intent_type="url_open", target="https://www.reddit.com")

        # 6. Twitter / X
        if re.search(r"\b(?:twitter|x\.com)\b", t_low):
            m = re.search(r"(?:search|find)\s+(.+?)(?:\s+on\s+(?:twitter|x)|$)", t, re.IGNORECASE)
            if m:
                q = m.group(1).strip()
                return RouteIntent(intent_type="url_open", target=f"https://x.com/search?q={urllib.parse.quote(q)}")
            return RouteIntent(intent_type="url_open", target="https://x.com")

        return None

    def route(self, command_text: str) -> RouteIntent:
        """Parses user command and routes in < 0.05ms with zero API latency."""
        text = command_text.strip()
        if not text:
            return RouteIntent(intent_type="unknown", target="")

        # 0. Turbo Platform Direct Actions (Instagram, LeetCode, GFG, GitHub, Reddit, Twitter)
        turbo_intent = self._match_turbo_platform(text)
        if turbo_intent:
            return turbo_intent

        # 0.5 Multi-Step Physical GUI Action Sequences -> Autonomous Agent
        action_verbs = ["click", "type", "press", "scroll", "select", "tap", "drag", "fill"]
        has_action_verb = any(v in text.lower() for v in action_verbs)
        has_sequencing = any(conj in text.lower() for conj in [" and then ", " then ", " and click", " and type", " and search", " and open", " and play"])
        if has_action_verb and (has_sequencing or len(text.split()) > 7):
            return RouteIntent(intent_type="autonomous_goal", target=text)

        # 1. TagRush Multi-Client QA Test
        if self.tagrush_pattern.search(text):
            return RouteIntent(intent_type="tagrush_qa")

        # 2. WhatsApp Navigation
        wa_match = self.whatsapp_pattern.search(text)
        if wa_match:
            target_group = wa_match.group(1)
            if not target_group or "class" in target_group.lower():
                target_group = "Class Group"
            return RouteIntent(intent_type="whatsapp_open", target=target_group.strip())

        # 3. Mode Toggle
        mode_match = self.mode_pattern.search(text)
        if mode_match:
            if "mach" in text.lower():
                return RouteIntent(intent_type="switch_mode", target="mach")
            elif "bio" in text.lower():
                return RouteIntent(intent_type="switch_mode", target="biomimetic")

        # 4. Clean Temp
        if self.clean_pattern.search(text):
            return RouteIntent(intent_type="clean_temp")

        # 5. CDP Debug Mode Browser Launch
        if self.cdp_pattern.search(text):
            return RouteIntent(intent_type="browser_debug")

        # 5.5 PC Customization / Theme / Workspace
        theme_match = self.theme_pattern.search(text)
        if theme_match:
            if "coding" in text.lower():
                return RouteIntent(intent_type="workspace_setup", target="coding_mode")
            else:
                mode = theme_match.group(1).lower()
                is_dark = mode in ["dark", "obsidian"]
                return RouteIntent(intent_type="theme_change", target="dark" if is_dark else "light")

        # 6. YouTube Shorts Autopilot
        if self.yt_shorts_pattern.search(text):
            return RouteIntent(intent_type="youtube_shorts")

        # 7. YouTube Video Autopilot
        yt_play = self.yt_play_pattern.search(text)
        if yt_play:
            q = (yt_play.group(1) or yt_play.group(2) or "").strip()
            return RouteIntent(intent_type="youtube_play", target=q)

        # 8. Next Short / Scroll
        if self.yt_next_pattern.search(text):
            return RouteIntent(intent_type="youtube_next")

        # 9. Hardware & System Workspace Controls
        if self.system_control_pattern.match(text):
            return RouteIntent(intent_type="system_control", target=text)

        # 10. Standard Folder Open
        folder_match = self.folder_pattern.match(text)
        if folder_match:
            folder_name = folder_match.group(1)
            return RouteIntent(intent_type="folder_open", target=folder_name)

        # 11. URL Navigation
        if self.url_pattern.match(text):
            url = text if text.startswith("http") else f"https://{text}"
            return RouteIntent(intent_type="url_open", target=url)

        # 12. Explicit search prefixes
        yt_match = self.yt_pattern.match(text)
        if yt_match:
            import urllib.parse
            q = yt_match.group(1).strip()
            return RouteIntent(intent_type="url_open", target=f"https://www.youtube.com/results?search_query={urllib.parse.quote(q)}")

        gh_match = self.gh_pattern.match(text)
        if gh_match:
            import urllib.parse
            q = gh_match.group(1).strip()
            return RouteIntent(intent_type="url_open", target=f"https://github.com/search?q={urllib.parse.quote(q)}")

        ai_match = self.ai_pattern.match(text)
        if ai_match:
            return RouteIntent(intent_type="astra_inline_query", target=ai_match.group(1).strip())
            
        auto_match = self.auto_pattern.match(text)
        if auto_match:
            return RouteIntent(intent_type="autonomous_goal", target=auto_match.group(1).strip())
            
        api_match = self.api_pattern.match(text)
        if api_match:
            return RouteIntent(intent_type="set_api_key", target=api_match.group(1).strip())

        search_match = self.search_prefix.match(text)
        if search_match:
            return RouteIntent(intent_type="web_search", target=search_match.group(1).strip())
            
        # 12.5 NLP Web Search (e.g. "open chrome, go to gfg website and search X")
        if "search" in text.lower() or "google" in text.lower() or "find" in text.lower():
            # If they used quotes, extract exactly what's in quotes
            quote_match = re.search(r"\b(?:search|google|find)\s+(?:for\s+)?[\"'](.+?)[\"']", text, re.IGNORECASE)
            if quote_match:
                q = quote_match.group(1).strip()
            else:
                # Without quotes, stop at " and " or end of string
                complex_match = re.search(r"\b(?:search|google|find)\s+(?:for\s+)?(.+?)(?:\s+and\s+|\s+then\s+|$)", text, re.IGNORECASE)
                q = complex_match.group(1).strip() if complex_match else ""

            if q:
                site_match = re.search(r"go to\s+([a-zA-Z0-9_-]+)\s*(?:website|site)?", text, re.IGNORECASE)
                if site_match:
                    # Append site operator if they mentioned a specific site (like 'gfg')
                    site_kw = site_match.group(1).lower()
                    if site_kw == "gfg": site_kw = "geeksforgeeks.org"
                    q += f" site:{site_kw}"
                return RouteIntent(intent_type="web_search", target=q)

        # 13. Universal Local Application Resolution (Fixes "open jupyter", "blender", etc.!)
        # Checks if query starts with action verb or matches an installed app
        app_res = APP_LAUNCHER.resolve_app(text)
        if app_res:
            display_name, target_path = app_res
            return RouteIntent(intent_type="app_launch", target=text, extra={"display_name": display_name, "path": target_path})

        # 14. Astra Inline Knowledge & Math (No Chrome!)
        if self.math_pattern.match(text) and any(c in text for c in ["+", "-", "*", "/", "%", "^"]):
            return RouteIntent(intent_type="astra_inline_query", target=text)

        if self.question_pattern.search(text):
            return RouteIntent(intent_type="astra_inline_query", target=text)

        # 15. General queries default to Astra Inline Knowledge first!
        # If user wants full browser web search, they can use 'search ...' or click the Search button in the Astra card.
        return RouteIntent(intent_type="astra_inline_query", target=text)

    def get_intent_preview(self, command_text: str) -> Tuple[str, str]:
        """
        Returns (badge_label, badge_color_hex) in < 0.05ms for real-time typing preview.
        """
        text = command_text.strip()
        if not text:
            return "⚡ INSTANT (0ms)", "#10B981"

        intent = self.route(text)
        it = intent.intent_type

        if it == "app_launch":
            name = intent.extra.get("display_name", "App") if intent.extra else "App"
            return f"🚀 LAUNCH {name.upper()[:16]}", "#00F0FF"

        elif it == "system_control":
            return f"⚙️ SYSTEM ({intent.target.upper()[:12]})", "#F59E0B"

        elif it == "folder_open":
            return f"📂 OPEN {intent.target.upper()}", "#38BDF8"

        elif it == "youtube_shorts":
            return "▶ YOUTUBE SHORTS AUTOPILOT", "#FF0033"

        elif it == "youtube_play":
            return "🎵 PLAY YOUTUBE VIDEO", "#FF0033"

        elif it == "whatsapp_open":
            return "💬 OPEN WHATSAPP", "#25D366"

        elif it == "tagrush_qa":
            return "🎮 TAGRUSH DUAL QA", "#A855F7"

        elif it == "switch_mode":
            return f"🧬 MODE: {intent.target.upper()}", "#EC4899"

        elif it == "clean_temp":
            return "🧹 CLEAN TEMP CACHE", "#10B981"

        elif it == "browser_debug":
            return "🌐 CDP BROWSER DEBUG", "#00F0FF"

        elif it == "web_search":
            return "🌐 SEARCH GOOGLE", "#64748B"
            
        elif it == "theme_change":
            return f"🎨 SWITCH TO {intent.target.upper()} MODE", "#A855F7"
            
        elif it == "workspace_setup":
            return "💻 START CODING MODE", "#10B981"

        elif it == "url_open":
            return "🔗 OPEN URL", "#3B82F6"

        elif it == "autonomous_goal":
            return "🧠 AUTONOMOUS AGENT", "#8B5CF6"
            
        elif it == "set_api_key":
            return "🔑 CONFIGURE CLOUD API", "#F59E0B"

        elif it == "astra_inline_query":
            if any(op in text for op in ["+", "-", "*", "/", "%", "^"]):
                return "🔢 CALCULATE", "#10B981"
            return "🧠 CONTEXT AI", "#38BDF8"

        return "⚡ INSTANT (0ms)", "#10B981"

# Global router singleton
ROUTER = LocalRouter()
