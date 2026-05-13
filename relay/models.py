from pydantic import BaseModel
from typing import Optional, List

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    session_id: str
    messages: List[Message]
    task_id: Optional[str] = None

class ChatResponse(BaseModel):
    reply: str
    provider_used: str
    degraded: bool
    degraded_reason: Optional[str] = None
    session_id: str
