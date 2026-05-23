import asyncio
import time
import httpx
import os
from typing import Dict

FAILURE_THRESHOLD = 3
RECOVERY_TIMEOUT = 30
CHECK_INTERVAL = 10

TFY_BASE = "https://gateway.truefoundry.ai/api/llm/openai/v1"


class ProviderHealth:
    def __init__(self, name: str, health_url: str):
        self.name = name
        self.health_url = health_url
        self.state = "unknown"
        self.consecutive_failures = 0
        self.last_checked = 0.0
        self.circuit_opened_at = 0.0

    def record_success(self):
        self.consecutive_failures = 0
        self.state = "healthy"

    def record_failure(self):
        self.consecutive_failures += 1
        if self.consecutive_failures >= FAILURE_THRESHOLD:
            self.state = "circuit_open"
            self.circuit_opened_at = time.time()
        else:
            self.state = "degraded"

    def is_available(self) -> bool:
        if self.state in ("healthy", "unknown"):
            return True
        if self.state == "circuit_open":
            if time.time() - self.circuit_opened_at > RECOVERY_TIMEOUT:
                self.state = "recovering"
                return True
            return False
        if self.state in ("degraded", "recovering"):
            return True
        return False

    def to_dict(self):
        return {
            "name": self.name,
            "state": self.state,
            "consecutive_failures": self.consecutive_failures,
            "last_checked": self.last_checked,
        }


class HealthRegistry:
    def __init__(self):
        self.providers: Dict[str, ProviderHealth] = {
            "ollama": ProviderHealth(
                "ollama", "http://localhost:11434/api/tags"
            ),
            "truefoundry": ProviderHealth(
                "truefoundry",
                f"{TFY_BASE}/models",
            ),
            "openrouter": ProviderHealth(
                "openrouter",
                "https://openrouter.ai/api/v1/models",
            ),
        }

    def _get_headers(self, name: str) -> dict:
        """Read env vars at call time so dotenv is always loaded first."""
        if name == "truefoundry":
            token = (os.getenv("TFY_TOKEN") or os.getenv("TRUEFOUNDRY_TOKEN", "")).strip()
            return {"Authorization": f"Bearer {token}"} if token else {}
        if name == "openrouter":
            key = os.getenv("OPENROUTER_API_KEY", "").strip()
            return {"Authorization": f"Bearer {key}"} if key else {}
        return {}

    async def check_provider(self, name: str):
        p = self.providers[name]
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                r = await client.get(p.health_url, headers=self._get_headers(name))
                # 4xx = reachable but auth/not-found — still counts as up
                # Only 5xx or network errors count as failures
                if r.status_code < 500:
                    p.record_success()
                else:
                    p.record_failure()
        except Exception:
            p.record_failure()
        p.last_checked = time.time()

    async def start_health_checks(self):
        while True:
            await asyncio.gather(
                *[self.check_provider(name) for name in self.providers]
            )
            await asyncio.sleep(CHECK_INTERVAL)

    def get_status(self):
        return {"providers": {name: p.to_dict() for name, p in self.providers.items()}}

    def get_all(self):
        return self.get_status()

    def force_down(self, provider: str):
        if provider in self.providers:
            p = self.providers[provider]
            p.state = "circuit_open"
            p.consecutive_failures = FAILURE_THRESHOLD
            p.circuit_opened_at = time.time()

    def force_restore(self, provider: str):
        if provider in self.providers:
            self.providers[provider].record_success()


registry = HealthRegistry()
