from uagents import Agent, Context
from .messages import VisualContextRequest, VisualContextResponse

visual_agent = Agent(
    name="visual_agent",
    seed="visual_agent_seed_12345",
    port=8001,
    endpoint=["http://127.0.0.1:8001/submit"],
)

@visual_agent.on_message(model=VisualContextRequest, replies=VisualContextResponse)
async def handle_visual_request(ctx: Context, sender: str, msg: VisualContextRequest):
    ctx.logger.info(f"Received visual context request for session: {msg.session_id}")
    
    # In a real scenario, this would call the Perfect Corp YouCam API
    # For now, we simulate the visual context returned
    simulated_context = "Visual analysis: Patient appears calm, lighting is adequate, no signs of distress. Skin tone is normal."
    
    await ctx.send(sender, VisualContextResponse(context_data=simulated_context))
