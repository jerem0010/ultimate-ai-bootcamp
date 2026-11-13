from typing import Literal
from datetime import datetime

from pydantic import BaseModel, Field


class TaskRequest(BaseModel):
    prompt: str = Field(..., min_length=10)

    model: Literal["GPT", "Claude", "Gemini"]

    max_tokens: int = Field(
        default=512,
        ge=1,
        le=4096,
    )


class TaskResponse(BaseModel):
    task_id: int
    model: Literal["GPT", "Claude", "Gemini"]
    prompt: str
    max_tokens: int

    status: Literal[
        "pending",
        "running",
        "completed",
        "failed",
    ]

    result: str | None = None
    created_at: datetime
    updated_at: datetime


TaskStatus = Literal["pending", "running", "completed", "failed"]


class TaskPage(BaseModel):
    items: list[TaskResponse]
    next_cursor: int | None = None
