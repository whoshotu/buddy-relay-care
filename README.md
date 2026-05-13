# BUDDY Relay Care

> A resilient voice-first AI care assistant that stays calm, helpful, and context-aware even when tools, local models, or hosted AI providers fail.

## What It Does

BUDDY Relay Care is built on top of BUDDY — a voice-first assistant for dementia patients — and extends it with a reliability layer that handles failure gracefully at every level.

When an MCP server goes down, a local LLM crashes, or OpenAI/Claude brown out under load, BUDDY Relay Care:
- Classifies the failure type
- Switches to the next healthy provider
- Preserves full conversation and task state
- Tells the user in plain language what changed and what it can still do

## Failure Scenarios Handled

| Failure | Agent Behavior | User Message |
|---|---|---|
| MCP tool error | Model retries with corrected args | "That tool had an issue, retrying..." |
| MCP server down | Circuit opens, fallback path used | "Tool server offline, continuing without it." |
| Local LLM down | Failover to hosted provider | "Using backup model — still here." |
| OpenAI rate limited | Exponential backoff + jitter | "Primary model busy, retrying with delay." |
| Claude overloaded | Bounded retries, then reroute | "Switching to backup provider." |
| Full outage | Safe local fallback mode | "Limited mode active, I'm still here." |

## Architecture

```
User (Voice / Chat)
       │
  BUDDY Interface (Alexa / Web)
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
   Ollama     OpenAI     Claude
  (local)   (backup)  (tertiary)
       │
  YouCam Visual Care Module
  (Perfect Corp API)
```

## Stack

- Python + FastAPI
- uAgents / Almanac (BUDDY agent framework)
- Ollama (local LLM — Qwen3, GLM)
- OpenAI API
- Anthropic Claude API
- MCP (Model Context Protocol)
- Perfect Corp / YouCam API
- Docker
- AWS Lambda + DynamoDB (voice + memory)
- TrueFoundry (cloud deployment)

## Deployment

Deployed on TrueFoundry at `lopezdev.truefoundry.cloud`.

```bash
# Local development
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

## Hackathon

Built for [DevNetwork AI + ML Hackathon 2026](https://devnetwork-ai-ml-hack-2026.devpost.com)

Sponsor challenges:
- TrueFoundry — Resilient Agents
- Perfect Corp — YouCam Visual AI
