from relay.health_registry import registry

PROVIDER_PRIORITY = ["ollama", "truefoundry", "openrouter"]


def get_best_provider(skip: list = []) -> str:
    for provider in PROVIDER_PRIORITY:
        if provider in skip:
            continue
        if registry.providers[provider].is_available():
            return provider
    return "fallback"
