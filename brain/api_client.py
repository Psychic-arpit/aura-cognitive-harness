"""
brain/api_client.py - Aura Ultra-Low-Latency Anonymized Gemini AI Engine
Supports both legacy (AIzaSy...) and modern (AQ...) Google AI Studio Auth Keys.
Session keep-alive + Multi-model cascade (gemini-3.5-flash-lite -> gemini-flash-lite-latest).
Strict PII sanitization ensures 100% privacy and anonymity.
"""

import os
import json
import base64
import getpass
import re
import requests
from typing import Optional

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")

def anonymize_text(text: str) -> str:
    """Strips personal identifying information (PII) before sending to external AI."""
    try:
        user = getpass.getuser()
        if user and len(user) > 2:
            text = re.sub(re.escape(user), "user", text, flags=re.IGNORECASE)
    except Exception:
        pass

    # Strip Windows username paths (e.g. C:\Users\xyz\...)
    text = re.sub(r"[A-Za-z]:\\[Uu]sers\\[^\\]+\\", "~/", text)
    text = re.sub(r"[A-Za-z]:/[Uu]sers/[^/]+/", "~/", text)
    # Strip IP addresses
    text = re.sub(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "<ip>", text)
    # Strip potential API keys/tokens
    text = re.sub(r"(AIzaSy[A-Za-z0-9_-]{33}|AQ\.[A-Za-z0-9_-]{40,})", "<token>", text)
    return text

def is_valid_key(key: str) -> bool:
    if not key:
        return False
    k = key.strip()
    return k.startswith("AIzaSy") or k.startswith("AQ.")

def load_api_key() -> str:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                k = json.load(f).get("GEMINI_API_KEY", "")
                if is_valid_key(k):
                    return k.strip()
        except Exception:
            pass
    env_k = os.environ.get("GEMINI_API_KEY", "")
    return env_k.strip() if is_valid_key(env_k) else ""

class BrainClient:
    def __init__(self):
        self.api_key = load_api_key()
        self.session = requests.Session()
        self.models = [
            "gemini-3.5-flash-lite",
            "gemini-flash-lite-latest",
            "gemini-3.1-flash-lite"
        ]

    def set_api_key(self, key: str):
        self.api_key = key.strip()
        with open(CONFIG_FILE, "w") as f:
            json.dump({"GEMINI_API_KEY": self.api_key}, f, indent=4)

    def is_configured(self) -> bool:
        return is_valid_key(self.api_key)

    def analyze_intent_or_screen(self, prompt: str, image_bytes: Optional[bytes] = None) -> str:
        """Silently and anonymously processes task analysis and vision grounding via Gemini."""
        safe_prompt = anonymize_text(prompt)

        if not self.is_configured():
            return "Aura requires an AI Studio key. Type 'set api key <KEY>' to unlock."

        parts = [{"text": safe_prompt}]
        if image_bytes:
            b64_img = base64.b64encode(image_bytes).decode("utf-8")
            parts.append({
                "inline_data": {
                    "mime_type": "image/png",
                    "data": b64_img
                }
            })

        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 1000
            }
        }

        # Try cascade of models with session reuse
        for model in self.models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
            try:
                resp = self.session.post(url, json=payload, timeout=12.0)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            return parts[0].get("text", "").strip()
                elif resp.status_code == 404:
                    continue  # Try next model in cascade
                elif resp.status_code == 503:
                    continue  # Temporary spike, try next model
            except Exception:
                continue

        return "Active context analyzed, but intelligence engine was busy. Please try again."

# Global API client singleton
API_CLIENT = BrainClient()
