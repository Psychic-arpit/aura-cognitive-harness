"""
aura.agent.planner - Multi-Step Autonomous Computer-Use ReAct Loop
Executes complex human PC goals step-by-step with real-time observation, actuation, and safety checks.
"""

import re
import json
import time
import webbrowser
from typing import Callable, Dict, Any, Optional
from aura.agent.client import CLIENT
from aura.harness.actuation import ACTUATION
from aura.harness.uia import UIA
from aura.harness.safety import SAFETY
from aura.harness.perception import PERCEPTION

class AutonomousPlanner:
    def __init__(self, max_steps: int = 8):
        self.max_steps = max_steps

    def _execute_tool(self, action: str, params: dict, log_cb: Callable[[str], None]) -> str:
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
                import subprocess
                subprocess.Popen(app, shell=True)
                return f"Launched {app}."

            elif action == "click_ui":
                target = params.get("target_description", "")
                log_cb(f"🖱️ Targeting: '{target}'")
                pos = UIA.resolve_target(target)
                if pos:
                    cur_pos = ACTUATION.get_cursor_pos()
                    ACTUATION.glide_cursor(cur_pos, pos, duration=0.3)
                    ACTUATION.click()
                    return f"Clicked {target} at {pos}."
                return f"Could not visually resolve {target}."

            elif action == "type_text":
                text = params.get("text", "")
                log_cb(f"⌨️ Typing: '{text[:24]}'")
                ACTUATION.fast_type(text)
                return f"Typed '{text}'."

            elif action == "press_key":
                key = params.get("key", "enter")
                log_cb(f"⌨️ Pressing key: {key}")
                ACTUATION.fast_press(key)
                return f"Pressed {key}."

            elif action == "wait":
                secs = min(max(float(params.get("seconds", 1.0)), 0.2), 4.0)
                time.sleep(secs)
                return f"Waited {secs}s."

            elif action == "finish":
                msg = params.get("message", "Goal accomplished.")
                log_cb(f"✅ {msg}")
                return "DONE"

            return f"Unknown action: {action}"
        except Exception as e:
            return f"Notice: {e}"

    def _parse_plan(self, response: str) -> dict:
        if not response:
            return {"action": "finish", "params": {"message": "Goal completed."}}

        clean = re.sub(r"^```(?:json)?", "", response.strip(), flags=re.MULTILINE)
        clean = re.sub(r"```$", "", clean.strip(), flags=re.MULTILINE).strip()

        try:
            return json.loads(clean)
        except Exception:
            pass

        m = re.search(r"\{.*\}", response, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass

        # Heuristic extraction
        resp_low = response.lower()
        if "http" in resp_low or "goto_url" in resp_low:
            u = re.search(r"https?://[^\s\"')]+", response)
            if u:
                return {"thought": "Navigating to URL", "action": "goto_url", "params": {"url": u.group(0)}}

        if "type" in resp_low or "search" in resp_low:
            t_match = re.search(r"[\"']([^\"']+)[\"']", response)
            if t_match:
                return {"thought": "Typing query", "action": "type_text", "params": {"text": t_match.group(1)}}

        if "enter" in resp_low or "press" in resp_low:
            return {"thought": "Confirming with Enter", "action": "press_key", "params": {"key": "enter"}}

        return {"thought": "Finished", "action": "finish", "params": {"message": "Executed successfully."}}

    def execute_goal(self, goal: str, log_cb: Callable[[str], None]) -> str:
        SAFETY.activate(step_budget=self.max_steps)
        log_cb(f"🧠 Autopilot: '{goal[:32]}'")

        system_prompt = (
            "You are Aura's computer-use execution agent.\n"
            "Tools:\n"
            "1. goto_url(url) - Navigate browser directly\n"
            "2. launch_app(app_name) - Open Windows app\n"
            "3. click_ui(target_description) - Locate and click UI element\n"
            "4. type_text(text) - Type keystrokes into current focus\n"
            "5. press_key(key) - Press hardware key ('enter', 'tab', 'esc', 'ctrl+t')\n"
            "6. wait(seconds) - Wait for UI transition\n"
            "7. finish(message) - Complete goal\n\n"
            "Respond strictly in JSON:\n"
            '{"thought": "reasoning", "action": "tool_name", "params": {"param": "value"}}\n'
        )

        history = f"Goal: {goal}\n"

        for step in range(self.max_steps):
            if SAFETY.is_aborted():
                return "Aborted by safety harness."
            if not SAFETY.record_step():
                return "Aborted: Max step limit reached."

            ctx = PERCEPTION.get_context_snapshot()
            prompt = system_prompt + f"\nEnvironment: Active Window={ctx['window']['process']}\nHistory:\n{history}\nNext Step?"
            response = CLIENT.generate(prompt, max_tokens=250)
            plan = self._parse_plan(response)

            action = plan.get("action", "finish")
            params = plan.get("params", {})
            thought = plan.get("thought", "")
            if thought:
                log_cb(thought[:36])

            obs = self._execute_tool(action, params, log_cb)
            if obs == "DONE":
                SAFETY.deactivate()
                return plan.get("params", {}).get("message", "Task completed.")

            history += f"Action: {action} {params}\nObservation: {obs}\n"
            time.sleep(0.3)

        SAFETY.deactivate()
        return "Goal execution cycle finished."

PLANNER = AutonomousPlanner()
