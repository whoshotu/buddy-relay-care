from relay.health_registry import registry

PROVIDER_PRIORITY = ["openrouter", "truefoundry", "ollama"]


def get_best_provider(skip: list = []) -> str:
    for provider in PROVIDER_PRIORITY:
        if provider in skip:
            continue
        if registry.providers[provider].is_available():
            return provider
    return "fallback"
