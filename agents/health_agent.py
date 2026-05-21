from uagents import Agent, Context
from .messages import HealthContextRequest, HealthContextResponse

health_agent = Agent(
    name="health_agent",
    seed="health_agent_seed_12345",
    port=8002,
    endpoint=["http://127.0.0.1:8002/submit"],
)

@health_agent.on_message(model=HealthContextRequest, replies=HealthContextResponse)
async def handle_health_request(ctx: Context, sender: str, msg: HealthContextRequest):
    ctx.logger.info(f"Received health context request for session: {msg.session_id}")
    
    # In a real scenario, this would query a health database or EHR system
    # For now, we simulate the health context returned
    simulated_context = "Health record: Last medication taken 2 hours ago. Heart rate normal. Next medication due in 4 hours."
    
    await ctx.send(sender, HealthContextResponse(context_data=simulated_context))
