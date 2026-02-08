"""Model routing helpers for Gemini API calls with fallback rotation."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable, List

from google.genai import Client


DEFAULT_GEMINI_MODELS = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
]


# Example for future providers:
# OPENAI_MODELS= "gpt-4.1-mini,gpt-4.1"
# GROQ_MODELS= "llama-3.1-70b,deepseek-r1"


@dataclass
class ModelRouter:
    api_key: str
    models: List[str]

    @classmethod
    def from_env(cls, api_key_env: str = "GEMINI_API_KEY") -> "ModelRouter":
        api_key = os.getenv(api_key_env)
        if not api_key:
            raise ValueError(f"Missing {api_key_env} in environment.")
        models = _load_models_from_env("GEMINI_MODELS", DEFAULT_GEMINI_MODELS)
        return cls(api_key=api_key, models=models)

    def generate_content(self, prompt: str, preferred_models: Iterable[str] | None = None) -> str:
        client = Client(api_key=self.api_key)
        last_error: Exception | None = None
        model_sequence: List[str] = []
        if preferred_models:
            model_sequence.extend([model for model in preferred_models if model])
        model_sequence.extend([model for model in self.models if model not in model_sequence])
        for model in model_sequence:
            try:
                response = client.models.generate_content(model=model, contents=prompt)
                return response.text
            except Exception as exc:
                last_error = exc
                continue
        raise RuntimeError(f"All Gemini models failed. Last error: {last_error}")


def _load_models_from_env(env_key: str, fallback: Iterable[str]) -> List[str]:
    raw = os.getenv(env_key, "")
    if not raw:
        return list(fallback)
    models = [item.strip() for item in raw.split(",") if item.strip()]
    return models or list(fallback)
