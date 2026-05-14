import asyncio
import time
import httpx
from typing import Dict

FAILURE_THRESHOLD = 3
RECOVERY_TIMEOUT = 30
CHECK_INTERVAL = 10

class ProviderHealth:
    def __init__(self, name: str, health_url: str):
        self.name = name
        self.health_url = health_url
        self.status = "unknown"   # healthy | degraded | circuit_open | recovering
        self.failures = 0
        self.last_checked = 0.0
        self.circuit_opened_at = 0.0

    def record_success(self):
        self.failures = 0
        self.status = "healthy"

    def record_failure(self):
        self.failures += 1
        if self.failures >= FAILURE_THRESHOLD:
            self.status = "circuit_open"
            self.circuit_opened_at = time.time()
        else:
            self.status = "degraded"

    def is_available(self) -> bool:
        if self.status == "healthy":
            return True
        if self.status == "circuit_open":
            if time.time() - self.circuit_opened_at > RECOVERY_TIMEOUT:
                self.status = "recovering"
                return True
        if self.status == "recovering":
            return True
        return False

    def to_dict(self):
        return {
            "name": self.name,
            "status": self.status,
            "failures": self.failures,
            "last_checked": self.last_checked,
        }

class HealthRegistry:
    def __init__(self):
        self.providers: Dict[str, ProviderHealth] = {
            "ollama":  ProviderHealth("ollama",  "http://localhost:11434/api/tags"),
            "truefoundry": ProviderHealth("truefoundry", "https://lopezdev.truefoundry.cloud/api/llm/models"),
            "claude":  ProviderHealth("claude",  "https://api.anthropic.com/v1/models"),
        }

    async def check_provider(self, name: str):
        p = self.providers[name]
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(p.health_url)
                if r.status_code < 500:
                    p.record_success()
                else:
                    p.record_failure()
        except Exception:
            p.record_failure()
        p.last_checked = time.time()

    async def start_health_checks(self):
        while True:
            await asyncio.gather(*[
                self.check_provider(name)
                for name in self.providers
            ])
            await asyncio.sleep(CHECK_INTERVAL)

    def get_status(self):
        return {name: p.to_dict() for name, p in self.providers.items()}

    def get_all(self):
        return self.get_status()

registry = HealthRegistry()
