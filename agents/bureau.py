import asyncio
from uagents import Bureau
from .visual_agent import visual_agent
from .health_agent import health_agent
from .care_agent import care_agent

# Pass addresses to the care agent so it knows where to route requests locally
@care_agent.on_event("startup")
async def store_addresses(ctx):
    ctx.storage.set("visual_agent_address", visual_agent.address)
    ctx.storage.set("health_agent_address", health_agent.address)
    ctx.logger.info(f"Stored visual agent address: {visual_agent.address}")
    ctx.logger.info(f"Stored health agent address: {health_agent.address}")

bureau = Bureau(port=8000, endpoint=["http://127.0.0.1:8000/submit"])
bureau.add(visual_agent)
bureau.add(health_agent)
bureau.add(care_agent)

def get_care_agent_address():
    return care_agent.address

# Function to run the bureau in the background
async def run_bureau():
    await bureau.run_async()
