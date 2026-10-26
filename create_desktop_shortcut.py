"""
create_desktop_shortcut.py - Creates a 1-Click Desktop Shortcut for AURA
"""

import os
import win32com.client

def create_shortcut():
    wsh = win32com.client.Dispatch("WScript.Shell")
    target_bat = r"C:\Users\arpit\.gemini\antigravity\scratch\glowing-cursor-agent\run.bat"
    working_dir = r"C:\Users\arpit\.gemini\antigravity\scratch\glowing-cursor-agent"

    candidate_desktops = [
        os.path.join(os.environ["USERPROFILE"], "OneDrive", "Desktop"),
        os.path.join(os.environ["USERPROFILE"], "Desktop")
    ]

    for d in candidate_desktops:
        if os.path.exists(d):
            shortcut_path = os.path.join(d, "AURA Agent.lnk")
            sc = wsh.CreateShortCut(shortcut_path)
            sc.TargetPath = target_bat
            sc.WorkingDirectory = working_dir
            sc.Description = "AURA - Autonomous Desktop Cognitive Agent & Execution Harness"
            sc.save()
            print(f"[OK] Desktop shortcut created at: {shortcut_path}")

if __name__ == "__main__":
    create_shortcut()
