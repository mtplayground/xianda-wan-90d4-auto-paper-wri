from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class PaperCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    latex_source: str = Field(default="", max_length=1_000_000)
    template_id: UUID | None = None

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: str) -> str:
        title = value.strip()
        if not title:
            raise ValueError("Title must not be blank")
        return title


class PaperUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    latex_source: str | None = Field(default=None, max_length=1_000_000)
    template_id: UUID | None = None

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        title = value.strip()
        if not title:
            raise ValueError("Title must not be blank")
        return title

    @model_validator(mode="after")
    def at_least_one_field(self) -> "PaperUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self


class PaperResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_id: UUID
    title: str
    latex_source: str
    template_id: UUID | None
    created_at: datetime
    updated_at: datetime
