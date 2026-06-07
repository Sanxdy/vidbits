from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class Job(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    url: str
    status: str = Field(default="pending")
    progress: float = Field(default=0.0)
    error_message: Optional[str] = Field(default=None)
    source_path: Optional[str] = Field(default=None)
    output_path: Optional[str] = Field(default=None)
    selected_start: Optional[float] = Field(default=None)
    selected_end: Optional[float] = Field(default=None)
    hook_title: Optional[str] = Field(default=None)
    template_name: str = Field(default="clean")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
