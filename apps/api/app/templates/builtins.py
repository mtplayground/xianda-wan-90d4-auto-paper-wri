from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.storage.client import ObjectStorageClient
from app.templates.models import Template

BUILTIN_SOURCE_DIR = Path(__file__).with_name("builtin_sources")
BUILTIN_STORAGE_PREFIX = "templates/built-ins"


@dataclass(frozen=True)
class BuiltinTemplate:
    name: str
    description: str
    filename: str
    category: str

    @property
    def relative_key(self) -> str:
        return f"{BUILTIN_STORAGE_PREFIX}/{self.filename}"


BUILTIN_TEMPLATES = (
    BuiltinTemplate(
        name="Article",
        description="General academic article with abstract, sections, and references.",
        filename="article.tex",
        category="article",
    ),
    BuiltinTemplate(
        name="IEEE-style Conference",
        description="Two-column conference manuscript scaffold using IEEEtran.",
        filename="ieee_conference.tex",
        category="conference",
    ),
    BuiltinTemplate(
        name="Review Manuscript",
        description=(
            "Structured literature review draft with synthesis-oriented sections."
        ),
        filename="review_manuscript.tex",
        category="review",
    ),
)


def seed_builtin_templates(session: Session, storage: ObjectStorageClient) -> None:
    for template_def in BUILTIN_TEMPLATES:
        source_bytes = (BUILTIN_SOURCE_DIR / template_def.filename).read_bytes()
        stored_object = storage.upload_bytes(
            template_def.relative_key,
            source_bytes,
            content_type="application/x-tex",
        )
        metadata = {
            "builtin": True,
            "category": template_def.category,
            "content_type": "application/x-tex",
            "original_filename": template_def.filename,
            "size": stored_object.size,
        }
        template = session.scalar(
            select(Template).where(
                Template.is_built_in.is_(True),
                Template.name == template_def.name,
            )
        )
        if template is None:
            session.add(
                Template(
                    owner_id=None,
                    is_built_in=True,
                    name=template_def.name,
                    description=template_def.description,
                    storage_key=stored_object.relative_key,
                    metadata_json=metadata,
                )
            )
        else:
            template.description = template_def.description
            template.storage_key = stored_object.relative_key
            template.metadata_json = metadata
    session.commit()
