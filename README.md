# BUDDY Relay Care

> A resilient AI companion for people living with Alzheimer's and dementia.  
> When cloud providers go down, BUDDY automatically fails over — without losing conversation context and without showing the patient an error screen.

Built for the [DevNetwork AI + ML Hackathon 2026](https://devnetwork-ai-ml-hack-2026.devpost.com) TrueFoundry Resilient Agents challenge.

---

## The Problem

Dementia patients rely on AI assistants daily. When those assistants go offline mid-conversation, the result isn't just an inconvenience — it's confusion and broken trust for someone who can't troubleshoot an error screen.

**BUDDY Relay Care ensures that never happens.**

---

## Live Demo — 60-Second Judge Walkthrough

```bash
# 1. Clone and start
git clone https://github.com/whoshotu/buddy-relay-care
cd buddy-relay-care
cp .env.example .env   # add your TFY_TOKEN and OPENROUTER_API_KEY
pip install -r requirements.txt
uvicorn main:app --port 8000
```

Open **http://localhost:8000** for the chat UI.

Then in a second terminal, run the failover demo:

```bash
# See all providers healthy
curl http://localhost:8000/health

# Normal chat — responds via TrueFoundry
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hi, where am I?", "history": []}'

# Kill TrueFoundry — watch BUDDY fail over to OpenRouter seamlessly
curl -X POST http://localhost:8000/demo/break/truefoundry
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hi, where am I?", "history": []}'
# X-Provider-Used: openrouter, X-Degraded: true

# Kill OpenRouter too — BUDDY falls back to local Ollama
curl -X POST http://localhost:8000/demo/break/openrouter
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hi, where am I?", "history": []}'

# Kill everything — BUDDY returns a warm safe message, never an error
curl -X POST http://localhost:8000/demo/break/ollama
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hi, where am I?", "history": []}'
# reply: "I'm right here with you. You are safe and everything is okay."

# Restore all providers
curl -X POST http://localhost:8000/demo/restore/truefoundry
curl -X POST http://localhost:8000/demo/restore/openrouter
curl -X POST http://localhost:8000/demo/restore/ollama
```

Or get the full step list from the API itself:
```bash
curl http://localhost:8000/demo/scenario
```

---

## BUDDY's Care Persona

Every response — regardless of which AI provider is running underneath — goes through BUDDY's dementia care persona:

- **Short and simple** — 2 to 4 sentences max
- **Feelings first** — acknowledges emotions before anything else
- **Never corrects or argues** — gently redirects instead
- **Always calm** — no technical jargon, no rushed answers
- **Last resort fallback** — if all AI is unavailable, BUDDY says: *"I'm right here with you. You are safe and everything is okay."*

The system prompt is injected into every provider request from one place: `relay/orchestrator.py`.

---

## Failure Handling

| Failure | What Happens | Patient Experience |
|---|---|---|
| Provider 5xx error | Retries with exponential backoff + jitter | Slight delay, seamless |
| Provider fails after retries | Circuit opens, routes to next provider | Seamless failover |
| All cloud providers down | Falls over to local Ollama model | BUDDY stays online |
| Ollama also down | Returns warm hardcoded fallback | BUDDY stays calm and present |
| Provider recovers | Circuit resets after 60s, resumes primary | Automatic |

---

## Provider Priority

```
1. TrueFoundry   (primary  — openrouter/z-ai/glm-4.5-air:free)
2. OpenRouter    (secondary)
3. Ollama        (local fallback — qwen3:8b)
4. Safe reply    (hardcoded warm message — last resort)
```

---

## Architecture

```
User (Web Chat UI)
       │
  FastAPI (port 8000)
       │
  ┌────▼──────────────────────────────┐
  │       Relay Orchestrator          │
  │  ┌────────────────────────────┐   │
  │  │  Provider Health Registry  │   │
  │  │  Circuit Breaker           │   │
  │  │  Routing Policy Engine     │   │
  │  │  Task Checkpoint Store     │   │
  │  │  BUDDY Care System Prompt  │   │
  │  └────────────────────────────┘   │
  └────┬────────────┬──────────┬──────┘
       │            │          │
  TrueFoundry  OpenRouter  Ollama
  (primary)   (secondary)  (local)
       │
  uAgents Bureau
  (care + visual agents, Almanac testnet)
```

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Chat UI |
| `GET` | `/health` | Provider health status |
| `POST` | `/chat` | Send a message to BUDDY |
| `GET` | `/providers` | All provider states |
| `POST` | `/demo/break/{provider}` | Force a provider down (demo) |
| `POST` | `/demo/restore/{provider}` | Restore a provider (demo) |
| `GET` | `/demo/scenario` | Full demo walkthrough steps |

Response headers on `/chat`:
- `X-Provider-Used` — which provider answered
- `X-Degraded` — `true` if primary was bypassed
- `X-Degraded-Reason` — human-readable reason

---

## Environment Variables

```bash
TFY_TOKEN=your_truefoundry_token
TFY_MODEL=openrouter/z-ai-glm-4.5-air-free
OPENROUTER_API_KEY=your_openrouter_key
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:8b
```

Copy `.env.example` to `.env` and fill in your keys.

---

## Stack

- **Python + FastAPI** — API and relay layer
- **TrueFoundry LLM Gateway** — primary cloud provider
- **OpenRouter** — secondary cloud provider
- **Ollama (Qwen3:8b)** — local fallback model
- **uAgents / Almanac** — care and visual agent framework (testnet)
- **httpx** — async provider calls
- **Docker** — containerized deployment

---

## Project Structure

```
buddy-relay-care/
├── main.py                  # FastAPI app, routes, demo endpoints
├── relay/
│   ├── orchestrator.py      # BUDDY persona + provider failover logic
│   ├── router.py            # Provider priority and selection
│   ├── health_registry.py   # Circuit breaker + health tracking
│   ├── checkpoint.py        # Conversation state persistence
│   └── models.py            # Pydantic request/response models
├── agents/                  # uAgents care and visual agents
├── static/                  # Chat UI (served at /)
├── Dockerfile
├── truefoundry.yaml
└── .env.example
```
