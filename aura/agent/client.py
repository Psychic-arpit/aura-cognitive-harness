"""
aura.agent.client - Gemini API Client with multi-turn conversation support.
Adds generate_chat() for full conversation history alongside single-shot generate().
"""

import os
import json
import base64
import getpass
import re
import requests
from typing import Optional, List, Dict

CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "brain", "config.json")


def anonymize_text(text: str) -> str:
    try:
        user = getpass.getuser()
        if user and len(user) > 2:
            text = re.sub(re.escape(user), "user", text, flags=re.IGNORECASE)
    except Exception:
        pass
    text = re.sub(r"[A-Za-z]:\\[Uu]sers\\[^\\]+\\", "~/", text)
    text = re.sub(r"[A-Za-z]:/[Uu]sers/[^/]+/", "~/", text)
    text = re.sub(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "<ip>", text)
    text = re.sub(r"(AIzaSy[A-Za-z0-9_-]+|AQ\.[A-Za-z0-9_-]+)", "<token>", text)
    return text


def is_valid_key(key: str) -> bool:
    if not key:
        return False
    k = key.strip()
    return k.startswith("AIzaSy") or k.startswith("AQ.")


def load_key() -> str:
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


class AgentClient:
    def __init__(self):
        self.api_key = load_key()
        self.session = requests.Session()
        self.models = [
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-1.5-flash",
        ]

    def set_key(self, key: str):
        self.api_key = key.strip()
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump({"GEMINI_API_KEY": self.api_key}, f, indent=4)

    def is_configured(self) -> bool:
        return is_valid_key(self.api_key)

    def generate(self, prompt: str, image_bytes: Optional[bytes] = None, max_tokens: int = 1200) -> str:
        """Single-shot generation (backward compat)."""
        return self.generate_chat(
            system="",
            turns=[{"role": "user", "text": prompt}],
            image_bytes=image_bytes,
            max_tokens=max_tokens
        )

    def generate_chat(
        self,
        system: str,
        turns: List[Dict[str, str]],
        image_bytes: Optional[bytes] = None,
        max_tokens: int = 1200
    ) -> str:
        """
        Multi-turn conversation call.
        turns = [{"role": "user"|"model", "text": "..."}]
        system injected as a leading user→model exchange so it's always in context.
        image_bytes attached to the last user turn only.
        """
        if not self.is_configured():
            return "AURA needs a Gemini API key. Type: set api key <KEY>"

        contents = []

        # Inject system prompt as a silent prolog exchange
        if system:
            safe_sys = anonymize_text(system)
            contents.append({"role": "user", "parts": [{"text": f"[SYSTEM]\n{safe_sys}"}]})
            contents.append({"role": "model", "parts": [{"text": "Understood. I am AURA."}]})

        for i, turn in enumerate(turns):
            role = turn["role"]   # "user" or "model"
            text = anonymize_text(turn["text"])
            is_last = (i == len(turns) - 1)

            parts: list = [{"text": text}]
            if is_last and image_bytes and role == "user":
                b64 = base64.b64encode(image_bytes).decode("utf-8")
                parts.append({"inline_data": {"mime_type": "image/png", "data": b64}})

            contents.append({"role": role, "parts": parts})

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": max_tokens
            }
        }

        for model in self.models:
            url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"{model}:generateContent?key={self.api_key}"
            )
            try:
                resp = self.session.post(url, json=payload, timeout=15.0)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts_out = candidates[0].get("content", {}).get("parts", [])
                        if parts_out:
                            return parts_out[0].get("text", "").strip()
                elif resp.status_code in (404, 503):
                    continue
            except Exception:
                continue

        return "Cognitive engine unavailable — check network or API key."


CLIENT = AgentClient()
