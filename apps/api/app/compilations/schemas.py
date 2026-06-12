from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CompilationJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_id: UUID
    paper_id: UUID
    status: str
    pdf_storage_key: str | None
    pdf_url: str | None = None
    log_text: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
