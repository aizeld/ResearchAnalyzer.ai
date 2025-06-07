from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from datetime import datetime

router = APIRouter(prefix="/conversation", tags=["conversation"])

class ConversationEntry(BaseModel):
    question: str
    answer: str
    file_id: int

class ConversationResponse(BaseModel):
    id: int
    question: str
    answer: str
    timestamp: str
    file_id: int
