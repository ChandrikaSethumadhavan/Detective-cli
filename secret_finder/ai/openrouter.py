import re

from .base import ProviderError
from .http import post_json

MODEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]*")
URL = "https://openrouter.ai/api/v1/chat/completions"


class OpenRouter:
    def __init__(self, model: str, key: str):
        if not MODEL.fullmatch(model) or ".." in model:
            raise ProviderError("invalid SF_AI_MODEL")
        self.model, self.key = model, key

    def complete(self, prompt: str) -> str:
        data = post_json(
            URL, {"Authorization": f"Bearer {self.key}"},
            {"model": self.model, "messages": [{"role": "user", "content": prompt}], "temperature": 0},
        )
        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise ProviderError("unexpected response shape")
        if not isinstance(text, str):
            raise ProviderError("unexpected response shape")
        return text
