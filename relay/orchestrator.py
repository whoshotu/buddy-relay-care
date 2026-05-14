import asyncio
import httpx
import os
import random
from relay.router import get_best_provider, PROVIDER_PRIORITY
from relay.health_registry import registry
from relay.models import ChatRequest, ChatResponse
from relay.checkpoint import save_checkpoint
from fastapi.responses import JSONResponse
from fastapi import Response

FALLBACK_REPLY = (
    "I'm in limited mode right now — all AI providers are temporarily unavailable. "
    "Your conversation is saved and I'll resume normally as soon as service is restored."
)

MAX_RETRIES = 2
BASE_BACKOFF = 1.0  # seconds


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
            is_degraded = provider != "ollama"
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
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                "http://localhost:11434/api/chat",
                json={
                    "model": os.getenv("OLLAMA_MODEL", "qwen3:8b"),
                    "messages": messages,
                    "stream": False,
                },
            )
            r.raise_for_status()
            return r.json()["message"]["content"]

    if provider == "truefoundry":
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                "https://lopezdev.truefoundry.cloud/api/llm/chat/completions",
                headers={
                    "Authorization": f"Bearer {os.getenv('TRUEFOUNDRY_TOKEN')}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": os.getenv(
                        "TRUEFOUNDRY_MODEL", "buddy/openai-gpt-oss-120b-free"
                    ),
                    "messages": messages,
                },
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]

    if provider == "claude":
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        response = await client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=1024,
            messages=messages,
        )
        return response.content[0].text

    raise ValueError(f"Unknown provider: {provider}")
