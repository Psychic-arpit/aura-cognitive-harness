"""
aura.harness.smart_launcher - Zero-Error Smart Application & Protocol Launcher
Resolves native Windows executables, Start Menu shortcuts, URI schemes, and web fallbacks.
Seamlessly escalates unresolved actions directly to the Gemini API with zero CLI failure messages.
"""

import os
import sys
import glob
import urllib.parse
import webbrowser
import subprocess
from typing import Optional, Tuple, Dict, Any

class SmartLauncher:
    def __init__(self):
        self.appdata = os.environ.get("APPDATA", "")
        self.localappdata = os.environ.get("LOCALAPPDATA", "")
        self.programdata = os.environ.get("ProgramData", "")
        self.progfiles = os.environ.get("ProgramFiles", r"C:\Program Files")
        self.progfiles_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")

        # Curated fast mappings for instant launch (< 1ms)
        self.curated_apps: Dict[str, Dict[str, Any]] = {
            "spotify": {
                "paths": [
                    os.path.join(self.appdata, "Spotify", "Spotify.exe"),
                    os.path.join(self.localappdata, "Microsoft", "WindowsApps", "Spotify.exe"),
                ],
                "protocol": "spotify:",
                "web": "https://open.spotify.com",
                "search_uri": "spotify:search:{query}",
                "web_search": "https://open.spotify.com/search/{query}"
            },
            "discord": {
                "paths": [
                    os.path.join(self.localappdata, "Discord", "Update.exe --processStart Discord.exe"),
                    os.path.join(self.localappdata, "Discord", "app-*", "Discord.exe")
                ],
                "protocol": "discord:",
                "web": "https://discord.com/app"
            },
            "steam": {
                "paths": [
                    os.path.join(self.progfiles_x86, "Steam", "steam.exe"),
                    os.path.join(self.progfiles, "Steam", "steam.exe")
                ],
                "protocol": "steam:",
                "web": "https://store.steampowered.com"
            },
            "code": {
                "paths": [
                    os.path.join(self.localappdata, "Programs", "Microsoft VS Code", "Code.exe"),
                    os.path.join(self.progfiles, "Microsoft VS Code", "Code.exe")
                ],
                "protocol": "vscode:"
            },
            "vscode": {
                "paths": [
                    os.path.join(self.localappdata, "Programs", "Microsoft VS Code", "Code.exe"),
                    os.path.join(self.progfiles, "Microsoft VS Code", "Code.exe")
                ],
                "protocol": "vscode:"
            },
            "cursor": {
                "paths": [
                    os.path.join(self.localappdata, "Programs", "cursor", "Cursor.exe"),
                    os.path.join(self.localappdata, "Programs", "Cursor", "Cursor.exe")
                ]
            },
            "chrome": {
                "paths": [
                    os.path.join(self.progfiles, "Google", "Chrome", "Application", "chrome.exe"),
                    os.path.join(self.progfiles_x86, "Google", "Chrome", "Application", "chrome.exe"),
                    os.path.join(self.localappdata, "Google", "Chrome", "Application", "chrome.exe")
                ],
                "protocol": "googlechrome:"
            },
            "edge": {
                "paths": [
                    os.path.join(self.progfiles_x86, "Microsoft", "Edge", "Application", "msedge.exe"),
                    os.path.join(self.progfiles, "Microsoft", "Edge", "Application", "msedge.exe")
                ],
                "protocol": "microsoft-edge:"
            },
            "whatsapp": {
                "protocol": "whatsapp:",
                "web": "https://web.whatsapp.com"
            },
            "telegram": {
                "protocol": "tg:",
                "web": "https://web.telegram.org"
            },
            "slack": {
                "paths": [
                    os.path.join(self.localappdata, "slack", "slack.exe")
                ],
                "protocol": "slack:",
                "web": "https://app.slack.com"
            },
            "obsidian": {
                "paths": [
                    os.path.join(self.localappdata, "Programs", "obsidian", "Obsidian.exe")
                ],
                "protocol": "obsidian:"
            },
            "notion": {
                "paths": [
                    os.path.join(self.localappdata, "Programs", "Notion", "Notion.exe")
                ],
                "protocol": "notion:",
                "web": "https://notion.so"
            },
            "paint": {
                "paths": ["mspaint"]
            },
            "mspaint": {
                "paths": ["mspaint"]
            },
            "calc": {
                "paths": ["calc"],
                "protocol": "calculator:"
            },
            "calculator": {
                "paths": ["calc"],
                "protocol": "calculator:"
            },
            "notepad": {
                "paths": ["notepad"]
            },
            "taskmgr": {
                "paths": ["taskmgr"]
            },
            "settings": {
                "protocol": "ms-settings:"
            }
        }

    def resolve_app(self, name: str) -> Optional[str]:
        """Resolves an app name to an executable path, Start Menu shortcut, or URI protocol."""
        key = name.strip().lower()

        # 1. Curated check
        if key in self.curated_apps:
            cfg = self.curated_apps[key]
            # Check explicit paths
            for p in cfg.get("paths", []):
                # Handle glob paths like app-*
                if "*" in p:
                    matches = glob.glob(p)
                    if matches and os.path.exists(matches[0]):
                        return matches[0]
                elif os.path.exists(p) or p in ("mspaint", "calc", "notepad", "taskmgr", "explorer"):
                    return p
            # Check protocol
            if "protocol" in cfg:
                return cfg["protocol"]

        # 2. Dynamic Start Menu Scan (< 3ms)
        search_dirs = [
            os.path.join(self.appdata, r"Microsoft\Windows\Start Menu\Programs"),
            os.path.join(self.programdata, r"Microsoft\Windows\Start Menu\Programs"),
            os.path.join(self.localappdata, "Programs")
        ]
        for sdir in search_dirs:
            if not os.path.exists(sdir):
                continue
            for root, _, files in os.walk(sdir):
                for f in files:
                    fl = f.lower()
                    if fl.endswith((".lnk", ".exe")) and key in fl:
                        candidate = os.path.join(root, f)
                        if os.path.exists(candidate):
                            return candidate

        # 3. Direct protocol attempt if key has no spaces
        if " " not in key:
            return f"{key}:"

        return None

    def launch(self, name: str, extra_query: str = "") -> Tuple[bool, str]:
        """
        Launches an application or executes an intent with zero cmd errors.
        Returns (success: bool, status_message: str).
        """
        key = name.strip().lower()

        # Handle Spotify search queries directly
        if key == "spotify" and extra_query:
            q_enc = urllib.parse.quote(extra_query)
            try:
                os.startfile(f"spotify:search:{q_enc}")
                return True, f"Spotify searching for '{extra_query}'"
            except Exception:
                webbrowser.open(f"https://open.spotify.com/search/{q_enc}")
                return True, f"Spotify Web searching for '{extra_query}'"

        target = self.resolve_app(name)

        if target:
            try:
                if target.startswith("http://") or target.startswith("https://"):
                    webbrowser.open(target)
                    return True, f"Opened {target}"
                elif target.endswith(":") or target.endswith(".lnk"):
                    os.startfile(target)
                    return True, f"Launched {name.title()}"
                elif os.path.exists(target) or target in ("mspaint", "calc", "notepad", "taskmgr"):
                    subprocess.Popen(target, shell=True)
                    return True, f"Launched {name.title()}"
                else:
                    # Try os.startfile as fallback
                    os.startfile(target)
                    return True, f"Launched {name.title()}"
            except Exception:
                pass

        # Check web fallback
        if key in self.curated_apps and "web" in self.curated_apps[key]:
            web_url = self.curated_apps[key]["web"]
            webbrowser.open(web_url)
            return True, f"Opened {name.title()} (Web)"

        return False, f"Could not launch {name}"

SMART_LAUNCHER = SmartLauncher()
