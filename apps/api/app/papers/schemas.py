from datetime import datetime
from typing import Any, Literal
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
    reference_query: str | None = Field(default=None, max_length=20_000)
    reference_limit: int = Field(default=5, ge=0, le=10)

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
    reference_query: str | None = Field(default=None, max_length=20_000)
    reference_limit: int = Field(default=5, ge=0, le=10)

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


class PaperReferenceSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=20_000)
    limit: int = Field(default=5, ge=1, le=20)
    context_max_chars: int = Field(default=12_000, ge=500, le=30_000)

    @field_validator("query")
    @classmethod
    def query_must_not_be_blank(cls, value: str) -> str:
        query = value.strip()
        if not query:
            raise ValueError("Query must not be blank")
        return query


class PaperReferenceSearchResult(BaseModel):
    reference_id: UUID
    reference_title: str
    chunk_id: UUID
    chunk_index: int
    content: str
    score: float
    distance: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class PaperReferenceSearchResponse(BaseModel):
    query: str
    context: str
    results: list[PaperReferenceSearchResult]


class PaperCitationSuggestionRequest(BaseModel):
    passage: str = Field(min_length=1, max_length=100_000)
    instruction: str = Field(
        default="Suggest citations and summarize why each source is relevant.",
        max_length=4_000,
    )
    reference_query: str | None = Field(default=None, max_length=20_000)
    reference_limit: int = Field(default=6, ge=1, le=20)
    context_max_chars: int = Field(default=12_000, ge=500, le=30_000)

    @field_validator("passage")
    @classmethod
    def passage_must_not_be_blank(cls, value: str) -> str:
        passage = value.strip()
        if not passage:
            raise ValueError("Passage must not be blank")
        return passage

    @field_validator("instruction")
    @classmethod
    def citation_instruction_must_not_be_blank(cls, value: str) -> str:
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
    reference_context: str
    references: list[PaperReferenceSearchResult] = Field(default_factory=list)
