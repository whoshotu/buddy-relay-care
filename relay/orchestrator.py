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

MAX_RETRIES = 2
BASE_BACKOFF = 1.0


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
            degraded=True,
            degraded_reason="All providers unavailable — safe fallback mode active.",
            session_id=request.session_id,
        )

    for retry in range(MAX_RETRIES + 1):
        try:
            reply = await call_provider(provider, request)
            registry.providers[provider].record_success()
            # degraded only when we had to failover to a non-primary provider
            is_degraded = _attempt > 0
            return ChatResponse(
                reply=reply,
                provider_used=provider,
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


async def call_provider(provider: str, request: ChatRequest) -> str:
    messages = [{"role": m.role, "content": m.content} for m in request.messages]

    if provider == "ollama":
        ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        model = os.getenv("OLLAMA_MODEL", "qwen3:8b")
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
        token = os.getenv("TFY_TOKEN") or os.getenv("TRUEFOUNDRY_TOKEN")
        model = os.getenv("TRUEFOUNDRY_MODEL", "openrouter/z-ai-glm-4.5-air-free")
        if not token:
            raise ValueError("TFY_TOKEN not set")
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                "https://gateway.truefoundry.ai/chat/completions",
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
        model = os.getenv("OPENROUTER_MODEL", "openrouter/owl-alpha")
        if not api_key or api_key == "your_openrouter_api_key_here":
            raise ValueError("OPENROUTER_API_KEY not set")
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
