import asyncio
from uagents import Agent, Context
from .messages import (
    ChatRequestMsg,
    ChatResponseMsg,
    VisualContextRequest,
    VisualContextResponse,
    HealthContextRequest,
    HealthContextResponse,
)
from relay.models import ChatRequest
from relay.orchestrator import relay_request

care_agent = Agent(
    name="care_agent",
    seed="care_agent_seed_12345",
    port=8003,
    endpoint=["http://127.0.0.1:8003/submit"],
)

# Replace these with the actual addresses of the agents running in the bureau
VISUAL_AGENT_ADDRESS = "agent1qd6z8eutn0l9l7ss6ntg9y865m2t4f8cvn7y8k8zft3w7ssq68cvsxxwqqv" # Dummy addresses, replaced dynamically if possible, or queried
HEALTH_AGENT_ADDRESS = "agent1qvyksq4l3m0c7cwt7n4dpxv5awez7ssxgmhwzls4wqcxm5v92z4sgrw8e0x"

@care_agent.on_event("startup")
async def setup_addresses(ctx: Context):
    # In a real setup, you might use the Almanac to find these agents.
    # For a local bureau, we can inject the addresses from the bureau directly,
    # or just use the local addresses if they are known.
    pass

@care_agent.on_message(model=ChatRequestMsg, replies=ChatResponseMsg)
async def handle_chat_request(ctx: Context, sender: str, msg: ChatRequestMsg):
    ctx.logger.info(f"Received chat request from {sender} for session {msg.session_id}")
    
    visual_context = ""
    health_context = ""

    # In a full implementation, we would query the other agents here.
    # For a local script, we can query them using ctx.send and wait, but uagents doesn't
    # natively support blocking send_and_receive in handlers easily without custom futures.
    # To keep it simple and robust, we assume the bureau has initialized the addresses 
    # in the agent's storage or we use hardcoded addresses.
    
    # We retrieve the actual addresses from storage where Bureau placed them
    visual_address = ctx.storage.get("visual_agent_address")
    health_address = ctx.storage.get("health_agent_address")

    if visual_address:
        try:
            visual_resp = await ctx.send_and_receive(visual_address, VisualContextRequest(session_id=msg.session_id))
            if isinstance(visual_resp, VisualContextResponse):
                visual_context = visual_resp.context_data
        except Exception as e:
            ctx.logger.error(f"Failed to get visual context: {e}")

    if health_address:
        try:
            health_resp = await ctx.send_and_receive(health_address, HealthContextRequest(session_id=msg.session_id))
            if isinstance(health_resp, HealthContextResponse):
                health_context = health_resp.context_data
        except Exception as e:
            ctx.logger.error(f"Failed to get health context: {e}")
            
    # Inject contexts into the messages
    messages = msg.messages.copy()
    context_msg = f"[SYSTEM_CONTEXT] {visual_context} | {health_context}"
    
    # Insert system context message before the latest user message or at the end
    if len(messages) > 0 and messages[-1]['role'] == 'user':
        messages.insert(-1, {"role": "system", "content": context_msg})
    else:
        messages.append({"role": "system", "content": context_msg})
        
    # Build Relay Request
    from relay.models import Message
    relay_msg = ChatRequest(
        session_id=msg.session_id,
        messages=[Message(**m) for m in messages]
    )
    
    # Call the Resilience Layer
    ctx.logger.info("Routing request through Resilience Layer...")
    relay_result = await relay_request(relay_msg)
    
    # Send response back to the requester (FastAPI)
    await ctx.send(sender, ChatResponseMsg(
        reply=relay_result.reply,
        provider_used=relay_result.provider_used,
        degraded=relay_result.degraded,
        degraded_reason=relay_result.degraded_reason
    ))
