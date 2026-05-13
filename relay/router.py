from relay.health_registry import registry

PROVIDER_PRIORITY = ["ollama", "openai", "claude"]

def get_best_provider() -> str:
    for name in PROVIDER_PRIORITY:
        p = registry.providers.get(name)
        if p and p.is_available():
            return name
    return "fallback"
