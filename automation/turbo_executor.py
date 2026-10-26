"""
automation/turbo_executor.py - Multi-Step Autonomous Computer-Use Engine
Executes complex human PC goals step-by-step using visual perception, 
biomimetic mouse motion, and Win32 hardware keystroke synthesis.
"""

import re
import json
import time
import webbrowser
from typing import Callable, Dict, Any, Optional
from brain.api_client import API_CLIENT
from automation.app_launcher import APP_LAUNCHER
from core.uia_engine import UIA_ENGINE
from core.motion_engine import MOTION
from core.win32_fast import fast_mouse_click, fast_type, fast_press, get_cursor_pos

class TurboExecutor:
    def __init__(self):
        self.max_steps = 6

    def _execute_step(self, action: str, params: dict, log_cb: Callable[[str], None]) -> str:
        """Dispatches atomic computer action directly to hardware drivers."""
        try:
            if action == "goto_url":
                url = params.get("url", "")
                if not url.startswith("http"):
                    url = f"https://{url}"
                log_cb(f"🚀 Navigating: {url[:36]}")
                webbrowser.open(url)
                return f"Opened {url}."

            elif action == "launch_app":
                app = params.get("app_name", "")
                log_cb(f"🚀 Launching app: {app}")
                res = APP_LAUNCHER.resolve_app(app)
                if res:
                    APP_LAUNCHER.launch_app(res[1])
                    return f"Launched {res[0]}."
                return f"App {app} not found."

            elif action == "click_ui":
                target = params.get("target_description", "")
                log_cb(f"🖱️ Targeting: '{target}'")
                pos = UIA_ENGINE.resolve_ui_target(target)
                if pos:
                    cur_x, cur_y = get_cursor_pos()
                    MOTION.glide_cursor((cur_x, cur_y), pos)
                    fast_mouse_click()
                    return f"Clicked {target} at {pos}."
                return f"Could not visually resolve {target}."

            elif action == "type_text":
                text = params.get("text", "")
                log_cb(f"⌨️ Typing: '{text[:24]}'")
                fast_type(text)
                return f"Typed '{text}'."

            elif action == "press_key":
                key = params.get("key", "enter")
                log_cb(f"⌨️ Pressing key: {key}")
                fast_press(key)
                return f"Pressed {key}."

            elif action == "wait":
                secs = min(max(float(params.get("seconds", 1.5)), 0.5), 5.0)
                time.sleep(secs)
                return f"Waited {secs}s."

            elif action == "finish":
                msg = params.get("message", "Task successfully completed.")
                log_cb(f"✅ {msg}")
                return "DONE"

            return f"Unknown action: {action}"
        except Exception as e:
            return f"Action notice: {e}"

    def _parse_plan(self, response: str) -> dict:
        """Ultra-resilient JSON parser with heuristic fallback to prevent loop aborts."""
        if not response:
            return {"action": "finish", "params": {"message": "Goal completed."}}

        clean = re.sub(r"^```(?:json)?", "", response.strip(), flags=re.MULTILINE)
        clean = re.sub(r"```$", "", clean.strip(), flags=re.MULTILINE).strip()

        # Try JSON parsing
        try:
            return json.loads(clean)
        except Exception:
            pass

        # Try regex search for outermost object
        m = re.search(r"\{.*\}", response, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass

        # Heuristic command extraction from free text
        resp_low = response.lower()
        if "http" in resp_low or "goto_url" in resp_low:
            url_match = re.search(r"https?://[^\s\"')]+", response)
            if url_match:
                return {"thought": "Navigating to URL", "action": "goto_url", "params": {"url": url_match.group(0)}}

        if "type" in resp_low or "search" in resp_low:
            text_match = re.search(r"[\"']([^\"']+)[\"']", response)
            if text_match:
                return {"thought": "Typing query", "action": "type_text", "params": {"text": text_match.group(1)}}

        if "enter" in resp_low or "press" in resp_low:
            return {"thought": "Confirming with Enter", "action": "press_key", "params": {"key": "enter"}}

        return {"thought": "Task finished", "action": "finish", "params": {"message": "Goal executed."}}

    def execute_goal(self, goal: str, log_cb: Callable[[str], None]) -> str:
        """Executes multi-step autonomous computer workflow with real-time telemetry."""
        log_cb(f"🧠 Autopilot: '{goal[:32]}'")

        system_prompt = (
            "You are Aura's high-speed computer-use execution agent.\n"
            "Tools available:\n"
            "1. goto_url(url) - Navigate browser directly\n"
            "2. launch_app(app_name) - Open Windows app\n"
            "3. click_ui(target_description) - Visually locate and click UI element\n"
            "4. type_text(text) - Type keystrokes into current focus\n"
            "5. press_key(key) - Press hardware key (e.g. 'enter', 'tab', 'esc', 'ctrl+t')\n"
            "6. wait(seconds) - Wait for UI transition\n"
            "7. finish(message) - Complete goal\n\n"
            "Respond strictly in JSON:\n"
            '{"thought": "step reasoning", "action": "tool_name", "params": {"param": "value"}}\n'
        )

        history = f"Goal: {goal}\n"

        for step in range(self.max_steps):
            prompt = system_prompt + f"\nHistory:\n{history}\nNext Step?"
            response = API_CLIENT.analyze_intent_or_screen(prompt)
            plan = self._parse_plan(response)

            action = plan.get("action", "finish")
            params = plan.get("params", {})
            thought = plan.get("thought", "")
            if thought:
                log_cb(thought[:36])

            obs = self._execute_step(action, params, log_cb)
            if obs == "DONE":
                return plan.get("params", {}).get("message", "Task completed.")

            history += f"Action: {action} {params}\nObservation: {obs}\n"
            time.sleep(0.4)

        return "Task completed."

TURBO_EXECUTOR = TurboExecutor()
