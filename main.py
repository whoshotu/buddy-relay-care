from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import asyncio
from relay.health_registry import registry
from relay.router import get_best_provider
from relay.orchestrator import relay_request
from relay.models import ChatRequest, ChatResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(registry.start_health_checks())
    yield
    task.cancel()


app = FastAPI(
    title="BUDDY Relay Care",
    description="Resilient AI care agent with provider failover and circuit breaking",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/")
def root():
    return {"service": "BUDDY Relay Care", "status": "online"}


@app.get("/health")
def health():
    return registry.get_status()


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, response: Response):
    result = await relay_request(request)
    # Expose degradation state in headers so it's visible in curl/Postman
    response.headers["X-Provider-Used"] = result.provider_used
    response.headers["X-Degraded"] = str(result.degraded).lower()
    if result.degraded_reason:
        response.headers["X-Degraded-Reason"] = result.degraded_reason
    return result


@app.get("/providers")
def providers():
    return registry.get_all()


# ── Demo / judging helpers ────────────────────────────────────────────────────

@app.post("/demo/break/{provider}")
def demo_break(provider: str):
    """Force a provider into circuit_open state for live demos."""
    if provider not in registry.providers:
        return JSONResponse(status_code=404, content={"error": f"Unknown provider: {provider}"})
    registry.force_down(provider)
    return {"action": "forced_down", "provider": provider, "status": registry.providers[provider].to_dict()}


@app.post("/demo/restore/{provider}")
def demo_restore(provider: str):
    """Restore a provider to healthy state for live demos."""
    if provider not in registry.providers:
        return JSONResponse(status_code=404, content={"error": f"Unknown provider: {provider}"})
    registry.force_restore(provider)
    return {"action": "restored", "provider": provider, "status": registry.providers[provider].to_dict()}


@app.get("/demo/scenario")
def demo_scenario():
    """Return a suggested demo walkthrough for judges."""
    return {
        "steps": [
            "1. GET /health — see all providers healthy",
            "2. POST /chat — normal request, X-Provider-Used: ollama",
            "3. POST /demo/break/ollama — simulate local LLM going down",
            "4. POST /chat — failover, X-Provider-Used: truefoundry, X-Degraded: true",
            "5. POST /demo/break/truefoundry — simulate second provider failing",
            "6. POST /chat — failover to claude or safe fallback",
            "7. POST /demo/restore/ollama — recovery, next chat returns to primary",
        ]
    }
