import asyncio
import httpx
import os
import random
from relay.router import get_best_provider, PROVIDER_PRIORITY
from relay.health_registry import registry
from relay.models import ChatRequest, ChatResponse
from relay.checkpoint import save_checkpoint

FALLBACK_REPLY = (
    "I'm in limited mode right now — all AI providers are temporarily unavailable. "
    "Your conversation is saved and I'll resume normally as soon as service is restored."
)

# Default models — used only if the user sends no model_overrides
DEFAULT_MODELS = {
    "ollama":      os.getenv("OLLAMA_MODEL",       "qwen3:8b"),
    "truefoundry": os.getenv("TRUEFOUNDRY_MODEL",  "buddy/openai-gpt-oss-120b-free"),
    "openrouter":  os.getenv("OPENROUTER_MODEL",   "openrouter/owl-alpha"),
}

MAX_RETRIES = 2
BASE_BACKOFF = 1.0


def resolve_model(provider: str, request: ChatRequest) -> str:
    """Return the model to use: user override > env default > hardcoded default."""
    overrides = request.model_overrides or {}
    return overrides.get(provider) or DEFAULT_MODELS.get(provider, "")


async def relay_request(
    request: ChatRequest,
    _attempt: int = 0,
) -> ChatResponse:
    save_checkpoint(request.session_id, request.messages)

    provider = get_best_provider(skip=list(PROVIDER_PRIORITY[:_attempt]))

    if provider == "fallback" or _attempt >= len(PROVIDER_PRIORITY):
        return ChatResponse(
            reply=FALLBACK_REPLY,
            provider_used="fallback",
            model_used="none",
            degraded=True,
            degraded_reason="All providers unavailable — safe fallback mode active.",
            session_id=request.session_id,
        )

    model = resolve_model(provider, request)

    for retry in range(MAX_RETRIES + 1):
        try:
            reply = await call_provider(provider, model, request)
            registry.providers[provider].record_success()
            is_degraded = provider != "ollama"
            return ChatResponse(
                reply=reply,
                provider_used=provider,
                model_used=model,
                degraded=is_degraded,
                degraded_reason=(
                    f"Primary provider unavailable, using {provider} as fallback."
                    if is_degraded else None
                ),
                session_id=request.session_id,
            )
        except Exception:
            if retry < MAX_RETRIES:
                backoff = BASE_BACKOFF * (2 ** retry) + random.uniform(0, 0.5)
                await asyncio.sleep(backoff)
            else:
                registry.providers[provider].record_failure()
                return await relay_request(request, _attempt=_attempt + 1)


async def call_provider(provider: str, model: str, request: ChatRequest) -> str:
    messages = [{"role": m.role, "content": m.content} for m in request.messages]

    if provider == "ollama":
        ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                f"{ollama_url}/api/chat",
                json={"model": model, "messages": messages, "stream": False},
            )
            r.raise_for_status()
            data = r.json()
            if "error" in data:
                raise ValueError(f"Ollama error: {data['error']}")
            return data["message"]["content"]

    if provider == "truefoundry":
        token = os.getenv("TRUEFOUNDRY_TOKEN")
        if not token or token == "your_truefoundry_token_here":
            raise ValueError("TRUEFOUNDRY_TOKEN not set or is placeholder")
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                "https://lopezdev.truefoundry.cloud/api/llm/chat/completions",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={"model": model, "messages": messages},
            )
            r.raise_for_status()
            data = r.json()
            if "error" in data:
                raise ValueError(f"TrueFoundry error: {data['error']}")
            if not data.get("choices"):
                raise ValueError(f"TrueFoundry returned no choices: {data}")
            return data["choices"][0]["message"]["content"]

    if provider == "openrouter":
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key or api_key == "your_openrouter_api_key_here":
            raise ValueError("OPENROUTER_API_KEY not set or is placeholder")
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/whoshotu/buddy-relay-care",
                    "X-Title": "BUDDY Relay Care",
                },
                json={"model": model, "messages": messages},
            )
            r.raise_for_status()
            data = r.json()
            if "error" in data:
                raise ValueError(f"OpenRouter error: {data['error']}")
            if not data.get("choices"):
                raise ValueError(f"OpenRouter returned no choices: {data}")
            return data["choices"][0]["message"]["content"]

    raise ValueError(f"Unknown provider: {provider}")
