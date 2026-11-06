import re

from .base import ProviderError
from .http import post_json

MODEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


class Google:
    def __init__(self, model: str, key: str):
        model = model.removeprefix("models/")
        if not MODEL.fullmatch(model) or ".." in model:
            raise ProviderError("invalid SF_AI_MODEL")
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        self.key = key

    def complete(self, prompt: str) -> str:
        data = post_json(
            self.url, {"x-goog-api-key": self.key},
            {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0}},
        )
        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError):
            raise ProviderError("unexpected response shape")
        if not isinstance(text, str):
            raise ProviderError("unexpected response shape")
        return text
