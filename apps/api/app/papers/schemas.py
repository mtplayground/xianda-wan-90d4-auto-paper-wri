from datetime import datetime
from typing import Literal
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


class PaperAiPolishRequest(BaseModel):
    selected_text: str = Field(min_length=1, max_length=100_000)
    surrounding_context: str = Field(default="", max_length=100_000)
    instruction: str = Field(
        default="Improve clarity, grammar, flow, and academic tone.",
        max_length=4_000,
    )
    operation: Literal["polish", "rewrite"] = "polish"

    @field_validator("selected_text")
    @classmethod
    def selected_text_must_not_be_blank(cls, value: str) -> str:
        selected_text = value.strip()
        if not selected_text:
            raise ValueError("Selected text must not be blank")
        return selected_text

    @field_validator("instruction")
    @classmethod
    def instruction_must_not_be_blank(cls, value: str) -> str:
        instruction = value.strip()
        if not instruction:
            raise ValueError("Instruction must not be blank")
        return instruction


class PaperAiContinueRequest(BaseModel):
    draft_context: str = Field(min_length=1, max_length=160_000)
    instruction: str = Field(
        default="Continue the manuscript from the cursor position.",
        max_length=4_000,
    )
    target_length: Literal["short", "medium", "long"] = "medium"

    @field_validator("draft_context")
    @classmethod
    def draft_context_must_not_be_blank(cls, value: str) -> str:
        draft_context = value.strip()
        if not draft_context:
            raise ValueError("Draft context must not be blank")
        return draft_context

    @field_validator("instruction")
    @classmethod
    def continue_instruction_must_not_be_blank(cls, value: str) -> str:
        instruction = value.strip()
        if not instruction:
            raise ValueError("Instruction must not be blank")
        return instruction


class PaperAiResponse(BaseModel):
    text: str
    model: str
    stop_reason: str | None
    input_tokens: int | None
    output_tokens: int | None
