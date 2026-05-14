from relay.health_registry import registry
from typing import List

PROVIDER_PRIORITY = ["ollama", "truefoundry", "claude"]


def get_best_provider(skip: List[str] = []) -> str:
    for name in PROVIDER_PRIORITY:
        if name in skip:
            continue
        p = registry.providers.get(name)
        if p and p.is_available():
            return name
    return "fallback"
