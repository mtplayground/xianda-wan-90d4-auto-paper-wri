from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ReferenceChunkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    reference_id: UUID
    chunk_index: int
    content: str
    token_count: int | None
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias="metadata_json",
        serialization_alias="metadata",
    )
    created_at: datetime


class ReferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_id: UUID
    paper_id: UUID | None
    title: str
    authors: list[dict[str, Any]]
    publication_year: int | None
    venue: str | None
    doi: str | None
    url: str | None
    source_type: str
    source_identifier: str | None
    source_url: str | None = None
    abstract: str | None
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias="metadata_json",
        serialization_alias="metadata",
    )
    created_at: datetime
    updated_at: datetime


class ReferenceUploadResponse(BaseModel):
    reference: ReferenceResponse
    chunks: list[ReferenceChunkResponse]
    extracted_text_chars: int
