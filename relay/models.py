from pydantic import BaseModel, model_validator
from typing import Optional, List


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    session_id: Optional[str] = "demo"
    messages: Optional[List[Message]] = None
    task_id: Optional[str] = None
    message: Optional[str] = None
    history: Optional[List[Message]] = []

    @model_validator(mode="after")
    def resolve_messages(self):
        if not self.messages:
            msgs = list(self.history or [])
            if self.message:
                msgs.append(Message(role="user", content=self.message))
            self.messages = msgs
        return self


class ChatResponse(BaseModel):
    reply: str
    provider_used: str
    degraded: bool
    degraded_reason: Optional[str] = None
    session_id: str
