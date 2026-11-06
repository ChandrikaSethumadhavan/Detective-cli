from typing import Protocol


class ProviderError(Exception):
    pass


class Provider(Protocol):
    def complete(self, prompt: str) -> str: ...
