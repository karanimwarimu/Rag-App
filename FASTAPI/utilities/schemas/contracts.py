from typing import Literal, Optional

from pydantic import BaseModel


class SessionContext(BaseModel):
    user_id: Optional[str] = None
    is_authenticated: bool = False


class JobStatus(BaseModel):
    job_id: str
    status: Literal["pending", "processing", "complete", "failed"]
    user_id: Optional[str] = None
