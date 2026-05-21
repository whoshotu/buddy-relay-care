from pydantic import BaseModel
from typing import List, Dict, Optional

# Messages for communication with Care Agent
class ChatRequestMsg(BaseModel):
    session_id: str
    messages: List[Dict[str, str]]

class ChatResponseMsg(BaseModel):
    reply: str
    provider_used: str
    degraded: bool
    degraded_reason: Optional[str]

# Messages for Visual Agent
class VisualContextRequest(BaseModel):
    session_id: str

class VisualContextResponse(BaseModel):
    context_data: str

# Messages for Health Agent
class HealthContextRequest(BaseModel):
    session_id: str

class HealthContextResponse(BaseModel):
    context_data: str
