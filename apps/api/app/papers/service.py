from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.papers.models import Paper
from app.papers.schemas import PaperCreate, PaperUpdate


def list_papers_for_owner(session: Session, owner_id: UUID) -> list[Paper]:
    statement = (
        select(Paper)
        .where(Paper.owner_id == owner_id)
        .order_by(Paper.updated_at.desc(), Paper.created_at.desc())
    )
    return list(session.scalars(statement))


def get_paper_for_owner(
    session: Session,
    owner_id: UUID,
    paper_id: UUID,
) -> Paper | None:
    statement = select(Paper).where(Paper.id == paper_id, Paper.owner_id == owner_id)
    return session.scalar(statement)


def create_paper_for_owner(
    session: Session,
    owner_id: UUID,
    payload: PaperCreate,
) -> Paper:
    paper = Paper(
        owner_id=owner_id,
        title=payload.title,
        latex_source=payload.latex_source,
        template_id=payload.template_id,
    )
    session.add(paper)
    return paper


def apply_paper_update(paper: Paper, payload: PaperUpdate) -> Paper:
    if "title" in payload.model_fields_set and payload.title is not None:
        paper.title = payload.title
    if "latex_source" in payload.model_fields_set and payload.latex_source is not None:
        paper.latex_source = payload.latex_source
    if "template_id" in payload.model_fields_set:
        paper.template_id = payload.template_id
    return paper
