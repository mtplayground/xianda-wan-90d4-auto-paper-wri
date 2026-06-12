from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_id: UUID | None
    is_built_in: bool
    name: str
    description: str | None
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias="metadata_json",
        serialization_alias="metadata",
    )
    storage_key: str
    created_at: datetime
    updated_at: datetime


class TemplatePaperCreate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
