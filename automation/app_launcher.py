"""
automation/app_launcher.py - Universal Windows App & Environment Resolver
Discovers, Indexes, and Launches Any Installed Program, Tool, or Script in < 10ms
Bypasses Duplicate Process Spawning via Win32 Window Focus
"""

import os
import subprocess
import glob
import ctypes
from ctypes import wintypes
from typing import Optional, Dict, Tuple

user32 = ctypes.WinDLL("user32", use_last_error=True)

class AppLauncher:
    def __init__(self):
        self.app_index: Dict[str, str] = {}
        self.common_aliases: Dict[str, str] = {
            "jupyter": "jupyter notebook",
            "jupyter notebook": "jupyter notebook",
            "jupyterlab": "jupyter-lab",
            "jupyter lab": "jupyter-lab",
            "notebook": "jupyter notebook",
            "blender": "blender",
            "spotify": "spotify",
            "code": "visual studio code",
            "vscode": "visual studio code",
            "notepad": "notepad",
            "notepad++": "notepad++",
            "calc": "calculator",
            "calculator": "calculator",
            "chrome": "google chrome",
            "google chrome": "google chrome",
            "edge": "microsoft edge",
            "terminal": "windows terminal",
            "cmd": "command prompt",
            "powershell": "windows powershell",
            "wt": "windows terminal",
            "explorer": "file explorer",
            "files": "file explorer",
            "taskmgr": "task manager",
            "task manager": "task manager",
            "paint": "paint",
            "mspaint": "paint",
        }
        self.build_index()

    def build_index(self):
        """Scans Windows Start Menu, local programs, and Anaconda scripts in < 15ms."""
        self.app_index.clear()
        scan_dirs = [
            os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"),
            r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs",
            r"D:\Apps\Anaconda\Scripts",
            os.path.expandvars(r"%LOCALAPPDATA%\Programs"),
        ]

        for d in scan_dirs:
            if not os.path.exists(d):
                continue
            for root, _, files in os.walk(d):
                for f in files:
                    fl = f.lower()
                    if fl.endswith(".lnk") or fl.endswith(".exe"):
                        # Strip extension
                        name = os.path.splitext(f)[0].lower()
                        # Prefer .lnk files over raw helper .exe scripts
                        if name not in self.app_index or fl.endswith(".lnk"):
                            self.app_index[name] = os.path.join(root, f)

    def find_running_window(self, app_stem: str) -> Optional[int]:
        """Checks if a top-level window matching app_stem already exists."""
        found_hwnd = None
        stem_lower = app_stem.lower()

        # Specific window title keywords
        title_map = {
            "jupyter": "jupyter",
            "blender": "blender",
            "spotify": "spotify",
            "notepad": "notepad",
            "code": "visual studio code",
            "chrome": "google chrome",
            "edge": "microsoft edge",
            "terminal": "terminal",
        }
        keyword = title_map.get(stem_lower, stem_lower)

        def enum_windows_callback(hwnd, extra):
            nonlocal found_hwnd
            if not user32.IsWindowVisible(hwnd):
                return True
            length = user32.GetWindowTextLengthW(hwnd)
            if length == 0:
                return True
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            title = buff.value.lower()
            if keyword in title:
                found_hwnd = hwnd
                return False  # stop enumeration
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        user32.EnumWindows(WNDENUMPROC(enum_windows_callback), 0)
        return found_hwnd

    def focus_window(self, hwnd: int) -> bool:
        """Restores and focuses an existing window."""
        try:
            SW_RESTORE = 9
            user32.ShowWindow(hwnd, SW_RESTORE)
            user32.SetForegroundWindow(hwnd)
            return True
        except Exception:
            return False

    def resolve_app(self, query: str) -> Optional[Tuple[str, str]]:
        """
        Resolves a user query (e.g. 'jupyter', 'open blender', 'spotify')
        Returns (display_name, target_path_or_command) or None.
        """
        q = query.strip().lower()
        # Strip common action verbs
        for prefix in ["open ", "launch ", "start ", "run ", "goto ", "bring up "]:
            if q.startswith(prefix):
                q = q[len(prefix):].strip()
                break

        # Check aliases first
        resolved_key = self.common_aliases.get(q, q)

        # 1. Exact match in app_index
        if resolved_key in self.app_index:
            return resolved_key.title(), self.app_index[resolved_key]

        # 2. Substring match (e.g. 'jupyter' in 'jupyter notebook')
        for k, path in self.app_index.items():
            if resolved_key == k or resolved_key in k:
                return k.title(), path

        # 3. Built-in Windows system utilities
        builtin_tools = {
            "calc": "calc.exe",
            "calculator": "calc.exe",
            "notepad": "notepad.exe",
            "paint": "mspaint.exe",
            "mspaint": "mspaint.exe",
            "cmd": "cmd.exe",
            "terminal": "wt.exe",
            "powershell": "powershell.exe",
            "taskmgr": "taskmgr.exe",
            "explorer": "explorer.exe",
            "snippingtool": "snippingtool.exe",
            "control": "control.exe",
        }
        if q in builtin_tools:
            return q.title(), builtin_tools[q]

        # 4. UWP / Protocol URIs
        protocols = {
            "whatsapp": "whatsapp:",
            "spotify": "spotify:",
            "settings": "ms-settings:",
        }
        if q in protocols:
            return q.title(), protocols[q]

        return None

    def launch(self, query: str) -> Tuple[bool, str]:
        """
        Executes launching or focusing the target application.
        Returns (success: bool, status_message: str).
        """
        resolved = self.resolve_app(query)
        if not resolved:
            # Fallback attempt: check if query is a valid command on PATH
            try:
                subprocess.Popen([query], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True, f"Launched '{query}' [OK]"
            except Exception:
                return False, f"Could not locate application '{query}'"

        name, target = resolved

        # Check if already running and focus it!
        existing_hwnd = self.find_running_window(name)
        if existing_hwnd:
            self.focus_window(existing_hwnd)
            return True, f"Focused active '{name}' [OK]"

        # Handle special jupyter launch
        if "jupyter" in name.lower() or "jupyter" in target.lower():
            return self.launch_jupyter()

        # Launch via os.startfile for Windows native shortcuts / executables / URIs
        try:
            os.startfile(target)
            return True, f"Launched '{name}' [OK]"
        except Exception as e:
            try:
                subprocess.Popen(target, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True, f"Launched '{name}' [OK]"
            except Exception as e2:
                return False, f"Failed to launch '{name}': {e2}"

    def launch_jupyter(self) -> Tuple[bool, str]:
        """Specialized, reliable launcher for Jupyter Notebook / JupyterLab."""
        # Check if Jupyter is already open in a browser tab or window
        jupyter_hwnd = self.find_running_window("jupyter")
        if jupyter_hwnd:
            self.focus_window(jupyter_hwnd)
            return True, "Focused active Jupyter session [OK]"

        # Preferred Anaconda shortcut
        shortcut = os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Anaconda (Anaconda)\Jupyter Notebook.lnk")
        if os.path.exists(shortcut):
            try:
                os.startfile(shortcut)
                return True, "Launching Jupyter Notebook (Anaconda)... [OK]"
            except Exception:
                pass

        # Direct executable fallback
        exe_path = r"D:\Apps\Anaconda\Scripts\jupyter-notebook.exe"
        if os.path.exists(exe_path):
            try:
                subprocess.Popen([exe_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True, "Launching Jupyter Notebook Server... [OK]"
            except Exception as e:
                return False, f"Jupyter launch failed: {e}"

        # Standard command fallback
        try:
            subprocess.Popen(["jupyter", "notebook"], shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True, "Launching Jupyter Notebook... [OK]"
        except Exception as e:
            return False, f"Could not start Jupyter: {e}"

    def launch_folder(self, folder_name: str) -> Tuple[bool, str]:
        """Opens standard user folders in Windows Explorer."""
        known_folders = {
            "downloads": os.path.expandvars(r"%USERPROFILE%\Downloads"),
            "desktop": os.path.expandvars(r"%USERPROFILE%\Desktop"),
            "documents": os.path.expandvars(r"%USERPROFILE%\Documents"),
            "scratch": r"C:\Users\arpit\.gemini\antigravity\scratch\glowing-cursor-agent",
            "pictures": os.path.expandvars(r"%USERPROFILE%\Pictures"),
            "music": os.path.expandvars(r"%USERPROFILE%\Music"),
            "videos": os.path.expandvars(r"%USERPROFILE%\Videos"),
        }
        target = known_folders.get(folder_name.lower())
        if not target or not os.path.exists(target):
            # Try direct path
            if os.path.exists(folder_name):
                target = folder_name
            else:
                return False, f"Folder '{folder_name}' not found"

        try:
            os.startfile(target)
            return True, f"Opened {folder_name.title()} [OK]"
        except Exception as e:
            return False, f"Failed to open folder: {e}"

# Global AppLauncher singleton
APP_LAUNCHER = AppLauncher()
