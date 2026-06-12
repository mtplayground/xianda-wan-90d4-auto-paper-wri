from typing import Any
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.templates.models import Template


def list_templates_for_user(session: Session, owner_id: UUID) -> list[Template]:
    statement = (
        select(Template)
        .where(or_(Template.is_built_in.is_(True), Template.owner_id == owner_id))
        .order_by(Template.is_built_in.desc(), Template.name.asc())
    )
    return list(session.scalars(statement))


def create_template_for_owner(
    session: Session,
    owner_id: UUID,
    *,
    name: str,
    description: str | None,
    storage_key: str,
    metadata: dict[str, Any],
) -> Template:
    template = Template(
        owner_id=owner_id,
        is_built_in=False,
        name=name,
        description=description,
        storage_key=storage_key,
        metadata_json=metadata,
    )
    session.add(template)
    return template
