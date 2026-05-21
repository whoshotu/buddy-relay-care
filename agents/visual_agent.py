import os
import httpx
from uagents import Agent, Context
from .messages import VisualContextRequest, VisualContextResponse

visual_agent = Agent(
    name="visual_agent",
    seed="visual_agent_seed_12345",
    port=8001,
    endpoint=["http://127.0.0.1:8001/submit"],
)

YOUCAM_API_KEY = os.getenv("YOUCAM_API_KEY")
YOUCAM_API_SECRET = os.getenv("YOUCAM_API_SECRET")
YOUCAM_API_BASE = "https://yce-api-01.makeupar.com"


async def get_youcam_access_token() -> str | None:
    """Obtain a short-lived access token from the YouCam API."""
    if not YOUCAM_API_KEY or not YOUCAM_API_SECRET:
        return None
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{YOUCAM_API_BASE}/auth/v1/token",
            json={"api_key": YOUCAM_API_KEY, "api_secret": YOUCAM_API_SECRET},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get("access_token")


async def analyze_with_youcam(image_url: str, token: str) -> str:
    """Send an image URL to the YouCam Skin Analysis endpoint and return a summary."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{YOUCAM_API_BASE}/sbskin/v1/skin_analysis",
            headers={"Authorization": f"Bearer {token}"},
            json={"image_url": image_url},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

    # Build a human-readable summary from the API response
    overall = data.get("overall_score", "N/A")
    concerns = data.get("concerns", [])
    concern_str = ", ".join(concerns) if concerns else "none detected"
    return (
        f"YouCam Skin Analysis — Overall score: {overall}/100. "
        f"Concerns: {concern_str}."
    )


@visual_agent.on_message(model=VisualContextRequest, replies=VisualContextResponse)
async def handle_visual_request(ctx: Context, sender: str, msg: VisualContextRequest):
    ctx.logger.info(f"Received visual context request for session: {msg.session_id}")

    image_url = getattr(msg, "image_url", None)

    if YOUCAM_API_KEY and YOUCAM_API_SECRET and image_url:
        try:
            token = await get_youcam_access_token()
            if token:
                visual_context = await analyze_with_youcam(image_url, token)
                ctx.logger.info("YouCam analysis successful.")
            else:
                raise ValueError("Failed to obtain YouCam access token.")
        except Exception as exc:
            ctx.logger.error(f"YouCam API error: {exc}")
            visual_context = (
                "Visual analysis unavailable (API error). "
                "Patient status could not be assessed visually."
            )
    else:
        # Graceful fallback when credentials or image are not present
        visual_context = (
            "Visual analysis: Patient appears calm, lighting is adequate, "
            "no signs of distress. Skin tone is normal. "
            "(Simulated — set YOUCAM_API_KEY and YOUCAM_API_SECRET in .env to enable live analysis.)"
        )
        ctx.logger.warning(
            "YouCam credentials or image_url missing; using simulated visual context."
        )

    await ctx.send(sender, VisualContextResponse(context_data=visual_context))
