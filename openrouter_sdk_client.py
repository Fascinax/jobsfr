"""OpenRouter API wrapper for chat + JSON responses.

This module centralizes OpenRouter session handling so scoring scripts can
focus on prompt/data logic instead of transport/auth details.
"""

import os
import json
from urllib import request, error

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

class OpenRouterError(Exception):
    pass


def _strip_markdown_code_fences(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
    return cleaned

class OpenRouterClient:
    def __init__(self, model: str = "openai/gpt-4.1", timeout_seconds: int = 180):
        self._model = model
        self._timeout_seconds = timeout_seconds

    def chat(self, *, system: str, user: str) -> str:
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise OpenRouterError("OPENROUTER_API_KEY not set in environment")
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        payload = {
            "model": self._model,
            "messages": messages,
            "stream": False,
        }
        req = request.Request(
            OPENROUTER_API_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self._timeout_seconds) as resp:
                body = resp.read().decode("utf-8")
                status = getattr(resp, "status", 200)
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise OpenRouterError(f"OpenRouter API error: {exc.code} {body}") from exc
        except error.URLError as exc:
            raise OpenRouterError(f"OpenRouter request failed: {exc}") from exc

        if status != 200:
            raise OpenRouterError(f"OpenRouter API error: {status} {body}")

        try:
            data = json.loads(body)
        except json.JSONDecodeError as exc:
            preview = body[:300].replace("\n", " ")
            raise OpenRouterError(f"OpenRouter returned invalid JSON. Preview: {preview}") from exc
        choices = data.get("choices", [])
        if not choices:
            raise OpenRouterError("OpenRouter returned no choices")
        content = choices[0]["message"].get("content", "").strip()
        if not content:
            raise OpenRouterError("OpenRouter returned empty content")
        return content

    def chat_json(self, *, system: str, user: str) -> dict:
        output = self.chat(system=system, user=user)
        output = _strip_markdown_code_fences(output)
        try:
            parsed = json.loads(output)
        except json.JSONDecodeError as exc:
            preview = output[:300].replace("\n", " ")
            raise OpenRouterError(f"OpenRouter returned non-JSON output. Preview: {preview}") from exc
        if not isinstance(parsed, dict):
            raise OpenRouterError("OpenRouter JSON output must be an object")
        return parsed
