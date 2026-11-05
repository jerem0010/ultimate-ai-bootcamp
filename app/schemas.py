from typing import Literal
from pydantic import BaseModel, Field


class TaskRequest(BaseModel):
    prompt: str = Field(..., min_length=10)
    model: Literal["GPT", "Claude", "Gemini"]
    max_tokens: int = Field(default=512, ge=1, le=4096)


class TaskResponse(BaseModel):
    task_id: int
    model: Literal["GPT", "Claude", "Gemini"]
    prompt: str
    status: Literal["pending", "running", "completed", "failed"]