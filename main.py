from fastapi import FastAPI
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
    lifespan=lifespan
)

@app.get("/")
def root():
    return {"service": "BUDDY Relay Care", "status": "online"}

@app.get("/health")
def health():
    return registry.get_status()

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    return await relay_request(request)

@app.get("/providers")
def providers():
    return registry.get_all()
