import os
from typing import Mapping

from .base import Provider, ProviderError
from .google import Google
from .openrouter import OpenRouter

PROVIDERS = {"google": Google, "openrouter": OpenRouter}


def get_provider(env: Mapping[str, str] = os.environ) -> Provider:
    name = env.get("SF_AI_PROVIDER", "").lower()
    if name not in PROVIDERS:
        raise ProviderError("set SF_AI_PROVIDER to google or openrouter")
    model, key = env.get("SF_AI_MODEL", ""), env.get("SF_AI_API_KEY", "")
    if not model:
        raise ProviderError("set SF_AI_MODEL to a model id from the provider's current list")
    if not key:
        raise ProviderError("set SF_AI_API_KEY")
    return PROVIDERS[name](model, key)
