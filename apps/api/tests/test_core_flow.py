from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from types import SimpleNamespace

from app.auth.dependencies import CurrentUserContext, require_current_user
from app.auth.session import MctaiSessionClaims
from app.claude.client import ClaudeMessage
from app.compilations import routes as compilation_routes
from app.db.session import get_session
from app.main import app
from app.papers import routes as paper_routes
from app.papers.schemas import PaperReferenceSearchResult
from app.references import routes as reference_routes
from app.references.pdf import ExtractedReferenceText
from app.storage.client import StoredObject, get_storage_client
from app.templates import routes as template_routes
from fastapi.testclient import TestClient

OWNER_ID = uuid.UUID("11111111-1111-4111-8111-111111111111")
TEMPLATE_ID = uuid.UUID("22222222-2222-4222-8222-222222222222")
PAPER_ID = uuid.UUID("33333333-3333-4333-8333-333333333333")
REFERENCE_ID = uuid.UUID("44444444-4444-4444-8444-444444444444")
CHUNK_ID = uuid.UUID("55555555-5555-4555-8555-555555555555")
JOB_ID = uuid.UUID("66666666-6666-4666-8666-666666666666")
NOW = datetime(2026, 1, 1, tzinfo=UTC)


@dataclass
class FakeSession:
    committed: bool = False

    def commit(self) -> None:
        self.committed = True

    def refresh(self, _: object) -> None:
        return None

    def rollback(self) -> None:
        return None


class FakeStorageClient:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {
            "templates/article.tex": (
                b"\\documentclass{article}\n"
                b"\\begin{document}\n"
                b"Template body\n"
                b"\\end{document}\n"
            )
        }

    def download_bytes(self, relative_key: str) -> bytes:
        return self.objects[relative_key]

    def upload_bytes(
        self,
        relative_key: str,
        data: bytes,
        *,
        content_type: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> StoredObject:
        del content_type, metadata
        self.objects[relative_key] = data
        return StoredObject(
            relative_key=relative_key,
            key=f"app_xianda_wan_90d4_auto_paper_wri_adf0d3/{relative_key}",
            size=len(data),
        )

    def presigned_get_url(self, relative_key: str, *, expires_in: int = 3600) -> str:
        del expires_in
        return f"https://signed.example.test/{relative_key}"

    def delete_object(self, relative_key: str) -> None:
        self.objects.pop(relative_key, None)


class FakeClaudeClient:
    def complete_prompt(self, _: object) -> ClaudeMessage:
        return ClaudeMessage(
            text=(
                "Add a citation to Reference Paper and summarize its finding on "
                "retrieval-augmented drafting."
            ),
            model="claude-test",
            stop_reason="end_turn",
            input_tokens=42,
            output_tokens=24,
            raw={},
        )


def _current_user() -> CurrentUserContext:
    user = SimpleNamespace(
        id=OWNER_ID,
        sub="auth-sub-1",
        email="writer@example.test",
        name="Test Writer",
        picture_url=None,
        created_at=NOW,
        last_seen_at=NOW,
    )
    claims = MctaiSessionClaims(
        sub="auth-sub-1",
        email="writer@example.test",
        email_verified=True,
        name="Test Writer",
        picture=None,
        raw={"sub": "auth-sub-1", "email": "writer@example.test"},
    )
    return CurrentUserContext(user=user, claims=claims, created=False)


def _template() -> SimpleNamespace:
    return SimpleNamespace(
        id=TEMPLATE_ID,
        owner_id=None,
        is_built_in=True,
        name="Article",
        description="Standard article template",
        metadata_json={},
        storage_key="templates/article.tex",
        created_at=NOW,
        updated_at=NOW,
    )


def _paper(title: str = "Core Flow Paper") -> SimpleNamespace:
    return SimpleNamespace(
        id=PAPER_ID,
        owner_id=OWNER_ID,
        title=title,
        latex_source=(
            "\\documentclass{article}\n"
            "\\begin{document}\n"
            "Retrieval augmented writing improves drafting.\n"
            "\\end{document}\n"
        ),
        template_id=TEMPLATE_ID,
        created_at=NOW,
        updated_at=NOW,
    )


def _reference() -> SimpleNamespace:
    chunk = SimpleNamespace(
        id=CHUNK_ID,
        reference_id=REFERENCE_ID,
        chunk_index=0,
        content="Reference Paper shows retrieval improves academic drafting.",
        token_count=8,
        metadata_json={"page": 1},
        created_at=NOW,
    )
    reference = SimpleNamespace(
        id=REFERENCE_ID,
        owner_id=OWNER_ID,
        paper_id=PAPER_ID,
        title="Reference Paper",
        authors=[],
        publication_year=None,
        venue=None,
        doi=None,
        url=None,
        source_type="pdf",
        source_identifier="references/test/reference.pdf",
        abstract=None,
        metadata_json={"page_count": 1},
        created_at=NOW,
        updated_at=NOW,
    )
    reference.chunks = [chunk]
    return reference


def _compile_job(status: str = "pending") -> SimpleNamespace:
    pdf_key = "compilations/test/core-flow.pdf" if status == "succeeded" else None
    return SimpleNamespace(
        id=JOB_ID,
        owner_id=OWNER_ID,
        paper_id=PAPER_ID,
        status=status,
        pdf_storage_key=pdf_key,
        log_text="Output written on core-flow.pdf" if pdf_key else None,
        error_message=None,
        created_at=NOW,
        updated_at=NOW,
        started_at=NOW if status == "succeeded" else None,
        finished_at=NOW if status == "succeeded" else None,
    )


def test_core_flow_auth_template_reference_ai_compile_download(monkeypatch) -> None:
    storage = FakeStorageClient()
    session = FakeSession()
    paper = _paper()
    reference = _reference()
    compile_job = _compile_job()

    def session_dependency() -> FakeSession:
        return session

    app.dependency_overrides[require_current_user] = _current_user
    app.dependency_overrides[get_session] = session_dependency
    app.dependency_overrides[get_storage_client] = lambda: storage

    monkeypatch.setattr(
        template_routes, "get_template_for_user", lambda *args, **kwargs: _template()
    )
    monkeypatch.setattr(
        template_routes, "create_paper_for_owner", lambda *args, **kwargs: paper
    )
    monkeypatch.setattr(
        reference_routes, "get_paper_for_owner", lambda *args, **kwargs: paper
    )
    monkeypatch.setattr(
        reference_routes,
        "extract_pdf_text",
        lambda data: ExtractedReferenceText(
            text="Reference Paper shows retrieval improves academic drafting.",
            page_count=1,
        ),
    )
    monkeypatch.setattr(
        reference_routes,
        "create_reference_from_pdf",
        lambda *args, **kwargs: reference,
    )
    monkeypatch.setattr(
        reference_routes, "run_reference_embedding_job", lambda reference_id: None
    )
    monkeypatch.setattr(
        paper_routes, "get_paper_for_owner", lambda *args, **kwargs: paper
    )
    monkeypatch.setattr(
        paper_routes,
        "_search_reference_context",
        lambda *args, **kwargs: (
            "[Reference Paper] Retrieval improves academic drafting.",
            [
                PaperReferenceSearchResult(
                    reference_id=REFERENCE_ID,
                    reference_title="Reference Paper",
                    chunk_id=CHUNK_ID,
                    chunk_index=0,
                    content=(
                        "Reference Paper shows retrieval improves academic drafting."
                    ),
                    score=0.94,
                    distance=0.06,
                    metadata={"page": 1},
                )
            ],
        ),
    )
    monkeypatch.setattr(paper_routes, "get_claude_client", lambda: FakeClaudeClient())
    monkeypatch.setattr(
        compilation_routes, "get_paper_for_owner", lambda *args, **kwargs: paper
    )
    monkeypatch.setattr(
        compilation_routes,
        "create_compilation_job",
        lambda *args, **kwargs: compile_job,
    )

    def finish_compile_job(job_id: uuid.UUID) -> None:
        assert job_id == JOB_ID
        compile_job.status = "succeeded"
        compile_job.pdf_storage_key = "compilations/test/core-flow.pdf"
        compile_job.log_text = "Output written on core-flow.pdf"
        compile_job.started_at = NOW
        compile_job.finished_at = NOW
        storage.objects[compile_job.pdf_storage_key] = b"%PDF-1.4\ncompiled\n"

    monkeypatch.setattr(compilation_routes, "run_compilation_job", finish_compile_job)
    monkeypatch.setattr(
        compilation_routes,
        "get_compilation_job_for_owner",
        lambda *args, **kwargs: compile_job,
    )

    try:
        client = TestClient(app)

        create_response = client.post(
            f"/api/templates/{TEMPLATE_ID}/papers",
            json={"title": "Core Flow Paper"},
        )
        assert create_response.status_code == 201
        created_paper = create_response.json()
        assert created_paper["id"] == str(PAPER_ID)
        assert created_paper["title"] == "Core Flow Paper"

        upload_response = client.post(
            "/api/references/uploads/pdf",
            data={"title": "Reference Paper", "paper_id": str(PAPER_ID)},
            files={
                "file": (
                    "reference.pdf",
                    b"%PDF-1.4\nfake test pdf\n",
                    "application/pdf",
                )
            },
        )
        assert upload_response.status_code == 201
        uploaded_reference = upload_response.json()
        assert uploaded_reference["reference"]["id"] == str(REFERENCE_ID)
        assert uploaded_reference["chunks"][0]["content"].startswith("Reference Paper")
        assert (
            "references/test/reference.pdf"
            in uploaded_reference["reference"]["source_url"]
        )

        suggestion_response = client.post(
            f"/api/papers/{PAPER_ID}/references/suggestions",
            json={
                "passage": "Retrieval augmented writing improves drafting.",
                "instruction": "Suggest the best citation.",
            },
        )
        assert suggestion_response.status_code == 200
        suggestion = suggestion_response.json()
        assert "Reference Paper" in suggestion["text"]
        assert suggestion["references"][0]["reference_id"] == str(REFERENCE_ID)

        compile_response = client.post(f"/api/papers/{PAPER_ID}/compile")
        assert compile_response.status_code == 202

        job_response = client.get(f"/api/compile-jobs/{JOB_ID}")
        assert job_response.status_code == 200
        job = job_response.json()
        assert job["status"] == "succeeded"
        assert job["pdf_storage_key"] == "compilations/test/core-flow.pdf"
        assert job["pdf_url"].endswith("compilations/test/core-flow.pdf")
        assert storage.download_bytes(job["pdf_storage_key"]).startswith(b"%PDF-")
    finally:
        app.dependency_overrides.clear()
