"""
aura.agent.planner - Multi-Step Autonomous Computer-Use ReAct Loop
Executes complex human PC goals step-by-step with real-time observation, actuation, and safety checks.
Clean telemetry without emoji clutter.
"""

import re
import json
import time
import os
import subprocess
import webbrowser
from typing import Callable, Dict, Any, Optional, Tuple
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
                log_cb(f"Navigating to {url[:36]}")
                webbrowser.open(url)
                return f"Opened {url}."

            elif action == "launch_app":
                app = params.get("app_name", "")
                log_cb(f"Launching {app}")
                subprocess.Popen(app, shell=True)
                return f"Launched {app}."

            elif action == "click_ui":
                target = params.get("target_description", "")
                button = params.get("button", "left")
                log_cb(f"Clicking {target}")
                pos = UIA.resolve_target(target)
                if pos:
                    cur_pos = ACTUATION.get_cursor_pos()
                    ACTUATION.glide_cursor(cur_pos, pos, duration=0.25)
                    ACTUATION.click(button=button)
                    return f"Clicked {target} at {pos}."
                return f"Could not visually resolve {target}."

            elif action == "double_click_ui":
                target = params.get("target_description", "")
                log_cb(f"Double-clicking {target}")
                pos = UIA.resolve_target(target)
                if pos:
                    cur_pos = ACTUATION.get_cursor_pos()
                    ACTUATION.glide_cursor(cur_pos, pos, duration=0.25)
                    ACTUATION.double_click()
                    return f"Double-clicked {target} at {pos}."
                return f"Could not visually resolve {target}."

            elif action == "drag_mouse":
                # Can accept explicit coordinates or target descriptions
                fx = params.get("from_x")
                fy = params.get("from_y")
                tx = params.get("to_x")
                ty = params.get("to_y")
                from_target = params.get("from_target")
                to_target = params.get("to_target")

                if fx is None or fy is None:
                    p1 = UIA.resolve_target(from_target or "center")
                    fx, fy = p1 if p1 else (400, 400)
                if tx is None or ty is None:
                    p2 = UIA.resolve_target(to_target or "center")
                    tx, ty = p2 if p2 else (700, 700)

                duration = float(params.get("duration", 0.45))
                log_cb(f"Dragging ({fx}, {fy}) -> ({tx}, {ty})")
                ACTUATION.drag_cursor((int(fx), int(fy)), (int(tx), int(ty)), duration=duration)
                return f"Dragged from ({fx}, {fy}) to ({tx}, {ty})."

            elif action == "type_text":
                text = params.get("text", "")
                log_cb(f"Typing '{text[:24]}'")
                ACTUATION.fast_type(text)
                return f"Typed '{text}'."

            elif action == "press_key" or action == "hotkey":
                key = params.get("key") or params.get("hotkey", "enter")
                log_cb(f"Pressing {key}")
                ACTUATION.fast_press(key)
                return f"Pressed {key}."

            elif action == "execute_shell":
                cmd = params.get("command", "")
                log_cb(f"Shell: {cmd[:32]}")
                proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=12)
                out = (proc.stdout or proc.stderr or "Executed with no output.").strip()
                return out[:300]

            elif action == "execute_code":
                code = params.get("code", "")
                log_cb("Executing Python script...")
                proc = subprocess.run(["python", "-c", code], capture_output=True, text=True, timeout=12)
                out = (proc.stdout or proc.stderr or "Script finished with no output.").strip()
                return out[:300]

            elif action == "mspaint_draw":
                shape = params.get("shape", "rectangle").lower()
                return self.run_paint_recipe(shape, log_cb)

            elif action == "tagrush_qa":
                return self.run_tagrush_qa(log_cb)

            elif action == "wait":
                secs = min(max(float(params.get("seconds", 1.0)), 0.2), 4.0)
                time.sleep(secs)
                return f"Waited {secs}s."

            elif action == "finish":
                msg = params.get("message", "Task completed.")
                log_cb(msg)
                return "DONE"

            return f"Unknown action: {action}"
        except Exception as e:
            return f"Notice: {e}"

    def run_paint_recipe(self, shape: str = "rectangle", log_cb: Optional[Callable[[str], None]] = None) -> str:
        """Automates launching MS Paint, selecting shape, and dragging canvas."""
        cb = log_cb or (lambda m: None)
        cb("Launching MS Paint...")
        subprocess.Popen("mspaint", shell=True)
        time.sleep(1.2)

        # Select Shape
        cb(f"Selecting {shape} tool...")
        ACTUATION.fast_press("alt+h")
        time.sleep(0.15)
        ACTUATION.fast_press("o")
        time.sleep(0.15)

        if shape in ("rectangle", "rect", "box"):
            ACTUATION.fast_press("r")
        elif shape in ("circle", "ellipse", "oval"):
            ACTUATION.fast_press("c")
        elif shape in ("line",):
            ACTUATION.fast_press("l")
        time.sleep(0.3)

        # Drag on canvas
        sw, sh = ACTUATION.get_screen_size()
        cx, cy = sw // 2, sh // 2
        start_pt = (cx - 160, cy - 80)
        end_pt = (cx + 160, cy + 120)

        cb("Drawing shape on canvas...")
        ACTUATION.drag_cursor(start_pt, end_pt, duration=0.6)
        return f"Successfully rendered {shape} in MS Paint."

    def run_tagrush_qa(self, log_cb: Optional[Callable[[str], None]] = None) -> str:
        """Launches TagRush in dual-client multiplayer mode for QA playtesting."""
        cb = log_cb or (lambda m: None)
        cb("Locating Godot engine and TagRush project...")

        # Search for Godot engine
        godot_candidates = [
            r"C:\Users\arpit\Downloads\Godot_v4.7.2-stable_win64.exe",
            r"C:\Godot\godot.exe",
            r"D:\Godot\godot.exe"
        ]
        godot_exe = next((p for p in godot_candidates if os.path.exists(p)), None)

        # Search for TagRush project
        tagrush_candidates = [
            r"C:\Users\arpit\Downloads\Hide and Seek Game v1.o\TagRush",
            r"C:\Users\arpit\OneDrive\Documents\GitHub\tagrush-backup",
            r"C:\Users\arpit\.config\freebuff-desktop\projects\TagRush-823ae6e1-ab7a-432e-9562-353715df73a2"
        ]
        project_dir = next((p for p in tagrush_candidates if os.path.exists(os.path.join(p, "project.godot"))), None)

        if not godot_exe or not project_dir:
            return f"TagRush QA: Engine or project path not found (checked {len(tagrush_candidates)} locations)."

        cb("Spawning Client 1 (Left 960x1080)...")
        cmd_c1 = [godot_exe, "--path", project_dir, "--resolution", "960x1040", "--position", "0,0"]
        subprocess.Popen(cmd_c1)
        time.sleep(1.0)

        cb("Spawning Client 2 (Right 960x1080)...")
        cmd_c2 = [godot_exe, "--path", project_dir, "--resolution", "960x1040", "--position", "960,0"]
        subprocess.Popen(cmd_c2)

        return "TagRush QA Dual-Client Environment active (Left: Host, Right: Peer)."

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
        log_cb(f"Running: {goal[:32]}")

        g_low = goal.lower()

        # Fast-Path Direct Recipes
        if any(w in g_low for w in ["tagrush", "playtest tagrush", "test tagrush"]):
            res = self.run_tagrush_qa(log_cb)
            SAFETY.deactivate()
            return res

        if "paint" in g_low and any(w in g_low for w in ["draw", "rectangle", "rect", "box", "circle", "ellipse", "shape"]):
            shape = "rectangle"
            if any(w in g_low for w in ["circle", "ellipse", "round"]):
                shape = "circle"
            elif "line" in g_low:
                shape = "line"
            res = self.run_paint_recipe(shape, log_cb)
            SAFETY.deactivate()
            return res

        system_prompt = (
            "You are a computer-use execution agent.\n"
            "Tools:\n"
            "1. goto_url(url) - Navigate browser directly\n"
            "2. launch_app(app_name) - Open Windows app\n"
            "3. click_ui(target_description, button) - Locate and click UI element\n"
            "4. double_click_ui(target_description) - Double click UI element\n"
            "5. drag_mouse(from_x, from_y, to_x, to_y) - Drag mouse on screen\n"
            "6. type_text(text) - Type keystrokes into current focus\n"
            "7. press_key(key) - Press hardware key or combo ('enter', 'ctrl+c', 'alt+h')\n"
            "8. execute_shell(command) - Run PowerShell or CMD command directly\n"
            "9. execute_code(code) - Run Python script\n"
            "10. mspaint_draw(shape) - Draw shape in MS Paint\n"
            "11. wait(seconds) - Wait for UI transition\n"
            "12. finish(message) - Complete goal\n\n"
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
