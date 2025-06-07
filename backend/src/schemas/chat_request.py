from pydantic import BaseModel


class ChatRequest(BaseModel):
    prompt: str
    filename: str
