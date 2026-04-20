from pydantic import BaseModel, model_validator, Field
from typing import Optional
from datetime import datetime, timezone


class BenchmarkResult(BaseModel):
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    event: str
    level: str
    model: str
    prompt: str
    request_id: str
    status: str  # "success" or "failed"
    error: Optional[str] = None

    response: Optional[str] = None
    ttft: Optional[float] = None
    total_latency: Optional[float] = None
    tps: Optional[float] = None
    tokens: Optional[int] = None

    @model_validator(mode="after")
    def check_consistency(self):
        if self.status == "success":
            if self.ttft is None or self.total_latency is None or self.tps is None or self.tokens is None:
                raise ValueError("Success must include all performance metrics")

        if self.status == "failed":
            if self.error is None:
                raise ValueError("Failed status must include error message")

        return self