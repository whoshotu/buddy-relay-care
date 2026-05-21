from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import asyncio
import json
from uagents.query import query

from relay.health_registry import registry
from relay.router import get_best_provider
from relay.orchestrator import relay_request
from relay.models import ChatRequest, ChatResponse

from agents import run_bureau, get_care_agent_address, get_visual_agent_address, ChatRequestMsg, ChatResponseMsg
from agents.messages import VisualContextRequest, VisualContextResponse
from pydantic import BaseModel
from typing import Optional


@asynccontextmanager
async def lifespan(app: FastAPI):
    registry_task = asyncio.create_task(registry.start_health_checks())
    bureau_task = asyncio.create_task(run_bureau())
    yield
    registry_task.cancel()
    bureau_task.cancel()


app = FastAPI(
    title="BUDDY Relay Care",
    description="Resilient AI care agent with provider failover and circuit breaking",
    version="1.0.0",
    lifespan=lifespan,
)

# Serve the frontend UI
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", include_in_schema=False)
def root():
    return FileResponse("static/index.html")


@app.get("/health")
def health():
    return registry.get_status()


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, response: Response):
    # Delegate to the uAgents Care Agent
    msg = ChatRequestMsg(
        session_id=request.session_id,
        messages=[{"role": m.role, "content": m.content} for m in request.messages]
    )
    
    care_address = get_care_agent_address()
    response_msg = await query(destination=care_address, message=msg, timeout=60.0)
    
    if response_msg:
        data = json.loads(response_msg.decode_payload())
        result = ChatResponse(
            reply=data.get("reply", ""),
            provider_used=data.get("provider_used", ""),
            degraded=data.get("degraded", False),
            degraded_reason=data.get("degraded_reason"),
            session_id=request.session_id
        )
    else:
        result = ChatResponse(
            reply="I'm sorry, my internal systems are taking too long to respond. Please try again.",
            provider_used="fallback",
            degraded=True,
            degraded_reason="Care agent query timed out.",
            session_id=request.session_id
        )

    # Expose degradation state in headers so it's visible in curl/Postman
    response.headers["X-Provider-Used"] = result.provider_used
    response.headers["X-Degraded"] = str(result.degraded).lower()
    if result.degraded_reason:
        response.headers["X-Degraded-Reason"] = result.degraded_reason
    return result



class VisualRequest(BaseModel):
    session_id: str
    image_url: Optional[str] = None


@app.post("/visual")
async def visual(request: VisualRequest):
    """Send an image to the visual agent for YouCam AI skin analysis."""
    msg = VisualContextRequest(
        session_id=request.session_id,
        image_url=request.image_url,
    )
    visual_address = get_visual_agent_address()
    response_msg = await query(destination=visual_address, message=msg, timeout=30.0)

    if response_msg:
        data = json.loads(response_msg.decode_payload())
        return {"session_id": request.session_id, "visual_context": data.get("context_data", "")}
    return JSONResponse(
        status_code=503,
        content={"error": "Visual agent did not respond in time."},
    )


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
