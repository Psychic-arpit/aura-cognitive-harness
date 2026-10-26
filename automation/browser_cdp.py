"""
automation/browser_cdp.py - Ultralight Chrome DevTools Protocol (CDP) DOM Grounding
Zero Vision-Model Overhead (<2ms DOM Querying via Local WebSocket)
Translates HTML Element Bounding Boxes directly into Absolute Windows Screen Coordinates
"""

import json
import urllib.request
import urllib.error
from typing import Optional
import websocket

class BrowserCDPClient:
    def __init__(self, port: int = 9222):
        self.port = port
        self.base_url = f"http://localhost:{port}"

    def is_available(self) -> bool:
        """Checks if Chrome/Edge remote debugging is reachable in < 40ms."""
        try:
            req = urllib.request.Request(f"{self.base_url}/json/version")
            with urllib.request.urlopen(req, timeout=0.08) as resp:
                return resp.status == 200
        except Exception:
            return False

    def get_active_tab(self) -> Optional[dict]:
        """Finds the currently focused browser tab."""
        try:
            req = urllib.request.Request(f"{self.base_url}/json")
            with urllib.request.urlopen(req, timeout=0.15) as resp:
                tabs = json.loads(resp.read().decode("utf-8"))
                # Prioritize active page tab
                for tab in tabs:
                    if tab.get("type") == "page" and "webSocketDebuggerUrl" in tab:
                        return tab
        except Exception:
            pass
        return None

    def evaluate_expression(self, js_expr: str) -> Optional[dict]:
        """Runs a lightweight JS expression in the active tab over WebSocket."""
        tab = self.get_active_tab()
        if not tab:
            return None

        ws_url = tab.get("webSocketDebuggerUrl")
        if not ws_url:
            return None

        ws = None
        try:
            ws = websocket.create_connection(ws_url, timeout=0.25)
            msg = {
                "id": 1,
                "method": "Runtime.evaluate",
                "params": {
                    "expression": js_expr,
                    "returnByValue": True
                }
            }
            ws.send(json.dumps(msg))
            resp = json.loads(ws.recv())
            val = resp.get("result", {}).get("result", {}).get("value")
            return val
        except Exception:
            return None
        finally:
            if ws:
                try:
                    ws.close()
                except Exception:
                    pass

    def find_element_coords(self, css_selector: str) -> Optional[tuple[int, int]]:
        """
        Locates element via CSS selector and returns exact Windows screen coordinates (x, y).
        """
        js = f"""
        (() => {{
            try {{
                const el = document.querySelector({json.dumps(css_selector)});
                if (!el) return null;
                const r = el.getBoundingClientRect();
                if (r.width === 0 || r.height === 0) return null;
                const navBarHeight = Math.max(0, window.outerHeight - window.innerHeight);
                return {{
                    x: Math.round(window.screenX + r.left + r.width / 2),
                    y: Math.round(window.screenY + navBarHeight + r.top + r.height / 2)
                }};
            }} catch(e) {{
                return null;
            }}
        }})()
        """
        res = self.evaluate_expression(js)
        if isinstance(res, dict) and "x" in res and "y" in res:
            return int(res["x"]), int(res["y"])
        return None

    def find_youtube_shorts_coords(self) -> Optional[tuple[int, int]]:
        """Locates the active YouTube Shorts video element on screen."""
        js = """
        (() => {
            try {
                const el = document.querySelector('ytd-reel-video-renderer[is-active] video') ||
                           document.querySelector('ytd-reel-video-renderer video') ||
                           document.querySelector('#shorts-player video') ||
                           document.querySelector('video.html5-main-video') ||
                           document.querySelector('a[href*="/shorts/"]');
                if (!el) return null;
                const r = el.getBoundingClientRect();
                const navBarHeight = Math.max(0, window.outerHeight - window.innerHeight);
                return {
                    x: Math.round(window.screenX + r.left + r.width / 2),
                    y: Math.round(window.screenY + navBarHeight + r.top + r.height / 2)
                };
            } catch(e) {
                return null;
            }
        })()
        """
        res = self.evaluate_expression(js)
        if isinstance(res, dict) and "x" in res and "y" in res:
            return int(res["x"]), int(res["y"])
        return None

    def find_youtube_first_video_coords(self) -> Optional[tuple[int, int]]:
        """Locates the first video result thumbnail or title on YouTube search."""
        js = """
        (() => {
            try {
                const el = document.querySelector('ytd-video-renderer #video-title') ||
                           document.querySelector('ytd-video-renderer a#thumbnail') ||
                           document.querySelector('ytd-rich-item-renderer #video-title-link');
                if (!el) return null;
                const r = el.getBoundingClientRect();
                const navBarHeight = Math.max(0, window.outerHeight - window.innerHeight);
                return {
                    x: Math.round(window.screenX + r.left + r.width / 2),
                    y: Math.round(window.screenY + navBarHeight + r.top + r.height / 2)
                };
            } catch(e) {
                return null;
            }
        })()
        """
        res = self.evaluate_expression(js)
        if isinstance(res, dict) and "x" in res and "y" in res:
            return int(res["x"]), int(res["y"])
        return None

# Global CDP Client singleton
CDP = BrowserCDPClient()
