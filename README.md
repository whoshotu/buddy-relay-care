# BUDDY Relay Care

> A resilient AI companion for people living with Alzheimer's and dementia — stays calm, helpful, and online even when AI providers fail.

## What It Does

BUDDY is a warm, patient AI care companion built specifically for dementia and Alzheimer's patients. It speaks in short, simple, reassuring sentences and always prioritizes comfort over information.

BUDDY Relay Care adds a full reliability layer underneath — so BUDDY never goes silent, even when cloud providers are down, rate-limited, or overloaded.

### BUDDY's Care Persona
- Short, calm responses (2–4 sentences)
- Never corrects or argues — gently redirects
- Acknowledges feelings before anything else
- Always reassuring, never rushed
- If all AI is unavailable: *"I'm right here with you. You are safe and everything is okay."*

## Failure Handling

| Failure | What BUDDY Does | User Experience |
|---|---|---|
| Provider returns 5xx error | Retries with exponential backoff + jitter | Seamless — slight delay |
| Provider fails after retries | Circuit opens, routes to next provider | Seamless failover |
| All cloud providers down | Fails over to local Ollama model | BUDDY stays online |
| Ollama also down | Safe warm fallback reply | BUDDY stays calm and present |
| Provider recovers | Circuit resets after 60s, resumes primary | Automatic |

## Provider Priority

```
1. TrueFoundry  (primary — openrouter/z-ai/glm-4.5-air:free)
2. OpenRouter   (secondary)
3. Ollama       (local fallback — qwen3:8b)
4. Safe reply   (hardcoded warm message — last resort)
```

## Architecture

```
User (Web Chat UI)
       │
  FastAPI (port 8000)
       │
  ┌────▼─────────────────────────────┐
  │       Relay Orchestrator         │
  │  ┌──────────────────────────┐    │
  │  │  Provider Health Registry│    │
  │  │  Circuit Breaker         │    │
  │  │  Routing Policy Engine   │    │
  │  │  Task Checkpoint Store   │    │
  │  └──────────────────────────┘    │
  └────┬──────────┬──────────┬───────┘
       │          │          │
  TrueFoundry  OpenRouter  Ollama
  (primary)   (secondary) (local)
       │
  uAgents Bureau (visual, health, care agents)
  Almanac registration (testnet)
```

## Stack

- Python + FastAPI
- uAgents / Almanac (agent framework)
- Ollama (local LLM — Qwen3)
- TrueFoundry LLM Gateway (primary provider)
- OpenRouter (secondary provider)
- python-dotenv
- httpx (async HTTP)

## Running Locally

```bash
git clone https://github.com/whoshotu/buddy-relay-care
cd buddy-relay-care
pip install -r requirements.txt
cp .env.example .env   # fill in TFY_TOKEN and OPENROUTER_API_KEY
uvicorn main:app --port 8000
```

Open `http://localhost:8000` for the chat UI.

### Environment Variables

```
TFY_TOKEN=your_truefoundry_token
TFY_MODEL=openrouter/z-ai-glm-4.5-air-free
OPENROUTER_API_KEY=your_openrouter_key
OLLAMA_MODEL=qwen3:8b
```

### Demo Endpoints

```bash
GET  /health                    # provider health status
POST /chat                      # send a message to BUDDY
POST /demo/break/{provider}     # simulate a provider going down
POST /demo/restore/{provider}   # restore a provider
GET  /demo/scenario             # step-by-step demo walkthrough
```

## Hackathon

Built for [DevNetwork AI + ML Hackathon 2026](https://devnetwork-ai-ml-hack-2026.devpost.com)

Sponsor challenge: **TrueFoundry — Resilient Agents**
