"""
automation/autonomous_agent.py - General Purpose Autonomous ReAct Loop
Allows the agent to 'think and act' iteratively to achieve a complex goal.
"""

import json
import time
import re
from typing import Callable, Optional
from brain.api_client import API_CLIENT
from automation.web_driver import WEB
from automation.app_launcher import APP_LAUNCHER
from core.uia_engine import UIA_ENGINE
from core.motion_engine import MOTION

class AutonomousAgent:
    def __init__(self):
        self.max_steps = 5

    def _execute_tool(self, action: str, params: dict, log_cb: Callable[[str], None]) -> str:
        """Executes a single action and returns the observation."""
        try:
            if action == "web_search":
                q = params.get("query", "")
                log_cb(f"Acting: Searching web for '{q}'")
                WEB.search_and_open(q)
                return f"Browser opened and searched for {q}."
                
            elif action == "launch_app":
                app = params.get("app_name", "")
                log_cb(f"Acting: Launching {app}")
                res = APP_LAUNCHER.resolve_app(app)
                if res:
                    APP_LAUNCHER.launch_app(res[1])
                    return f"Launched {res[0]}."
                return f"App {app} not found."
                
            elif action == "click_ui":
                target = params.get("target_description", "")
                log_cb(f"Acting: Finding and clicking '{target}'")
                pos = UIA_ENGINE.resolve_ui_target(target)
                if pos:
                    MOTION.glide_cursor((0, 0), pos)
                    from core.win32_fast import fast_mouse_click
                    fast_mouse_click()
                    return f"Clicked {target} at {pos}."
                return f"Could not find {target} on screen."
                
            elif action == "goto_url":
                url = params.get("url", "")
                log_cb(f"Acting: Navigating to {url}")
                import webbrowser
                webbrowser.open(url)
                return f"Browser opened to {url}."
                
            elif action == "type_text":
                text = params.get("text", "")
                log_cb(f"Acting: Typing text '{text}'")
                from core.win32_fast import fast_type
                fast_type(text)
                return f"Typed '{text}'."
                
            elif action == "press_key":
                key = params.get("key", "enter")
                log_cb(f"Acting: Pressing key '{key}'")
                from core.win32_fast import fast_press
                fast_press(key)
                return f"Pressed {key}."
                
            elif action == "wait":
                seconds = params.get("seconds", 2)
                log_cb(f"Acting: Waiting {seconds}s")
                time.sleep(seconds)
                return f"Waited {seconds} seconds."
                
            elif action == "finish":
                msg = params.get("message", "Task complete.")
                log_cb(f"Goal Achieved: {msg}")
                return "DONE"
                
            else:
                return f"Unknown action: {action}"
        except Exception as e:
            return f"Action failed: {str(e)}"

    def _parse_plan(self, response: str) -> dict:
        """Robustly extracts JSON plan from raw AI response, with regex heuristic fallback."""
        if not response:
            return {"action": "finish", "params": {"message": "Task complete."}}

        # 1. Clean markdown code fences if present
        clean = re.sub(r"^```(?:json)?", "", response.strip(), flags=re.MULTILINE)
        clean = re.sub(r"```$", "", clean.strip(), flags=re.MULTILINE)

        # 2. Try direct JSON parse
        try:
            return json.loads(clean.strip())
        except Exception:
            pass

        # 3. Try finding outermost JSON object
        json_match = re.search(r"\{.*\}", response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except Exception:
                pass

        # 4. Fallback Heuristic Parsing from free text
        resp_lower = response.lower()
        if "goto_url" in resp_lower or "http" in resp_lower:
            url_m = re.search(r"https?://[^\s\"')]+", response)
            if url_m:
                return {"thought": "Navigating to URL", "action": "goto_url", "params": {"url": url_m.group(0)}}

        if "type_text" in resp_lower or "typing" in resp_lower:
            text_m = re.search(r"[\"']([^\"']+)[\"']", response)
            if text_m:
                return {"thought": "Typing input", "action": "type_text", "params": {"text": text_m.group(1)}}

        if "press_key" in resp_lower or "enter" in resp_lower:
            return {"thought": "Submitting query", "action": "press_key", "params": {"key": "enter"}}

        if "search" in resp_lower:
            q_m = re.search(r"search\s+(?:for\s+)?[\"']?([^\"'\n]+)[\"']?", response, re.IGNORECASE)
            if q_m:
                return {"thought": "Searching", "action": "web_search", "params": {"query": q_m.group(1).strip()}}

        return {"thought": "Finishing task", "action": "finish", "params": {"message": "Goal completed."}}

    def run_goal(self, goal: str, log_cb: Callable[[str], None]) -> str:
        """Runs the ReAct (Reason + Act) loop until the goal is met."""
        log_cb(f"Executing: {goal[:32]}...")
        
        system_prompt = (
            "You are a general-purpose autonomous computer agent. You think, plan, and act.\n"
            "You have access to these tools:\n"
            "1. web_search(query) - Search Google\n"
            "2. goto_url(url) - Open a specific URL in browser (e.g. https://instagram.com)\n"
            "3. launch_app(app_name)\n"
            "4. click_ui(target_description) - Finds an element on the screen and clicks it\n"
            "5. type_text(text) - Types text into the currently focused field\n"
            "6. press_key(key) - Presses a key (e.g., 'enter', 'tab', 'esc')\n"
            "7. wait(seconds) - Wait for page/app to load\n"
            "8. finish(message)\n\n"
            "To search inside a specific website, you should: goto_url, wait, click_ui(search bar), type_text(query), press_key(enter).\n\n"
            "Reply strictly in this JSON format:\n"
            '{"thought": "reasoning", "action": "tool_name", "params": {"key": "value"}}\n'
        )
        
        history = f"User Goal: {goal}\n"
        
        for step in range(self.max_steps):
            prompt = system_prompt + "\nHistory of actions:\n" + history + "\nWhat is your next step? (Reply in JSON)"
            response = API_CLIENT.analyze_intent_or_screen(prompt)
            plan = self._parse_plan(response)
            
            action = plan.get("action", "finish")
            params = plan.get("params", {})
            thought = plan.get("thought", "")
            if thought:
                log_cb(thought[:48])
            
            obs = self._execute_tool(action, params, log_cb)
            if obs == "DONE":
                return plan.get("params", {}).get("message", "Task completed.")
                
            history += f"\nAction: {action} {params}\nObservation: {obs}\n"
            time.sleep(0.5)
                
        return "Task completed."

AUTONOMOUS_AGENT = AutonomousAgent()
