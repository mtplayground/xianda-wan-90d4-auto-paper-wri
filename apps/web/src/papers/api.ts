import type {
  CompilationJob,
  Paper,
  PaperCreatePayload,
  PaperUpdatePayload,
  ReferenceChunk,
  ReferenceItem,
  ReferenceUploadResponse,
  Template
} from "./types";

function isPaper(value: unknown): value is Paper {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.id === "string" &&
    typeof candidate.owner_id === "string" &&
    typeof candidate.title === "string" &&
    typeof candidate.latex_source === "string" &&
    (typeof candidate.template_id === "string" || candidate.template_id === null) &&
    typeof candidate.created_at === "string" &&
    typeof candidate.updated_at === "string"
  );
}

function isTemplate(value: unknown): value is Template {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.id === "string" &&
    (typeof candidate.owner_id === "string" || candidate.owner_id === null) &&
    typeof candidate.is_built_in === "boolean" &&
    typeof candidate.name === "string" &&
    (typeof candidate.description === "string" || candidate.description === null) &&
    typeof candidate.metadata === "object" &&
    candidate.metadata !== null &&
    typeof candidate.storage_key === "string" &&
    typeof candidate.created_at === "string" &&
    typeof candidate.updated_at === "string"
  );
}

function isCompilationJob(value: unknown): value is CompilationJob {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.id === "string" &&
    typeof candidate.owner_id === "string" &&
    typeof candidate.paper_id === "string" &&
    ["pending", "running", "succeeded", "failed"].includes(String(candidate.status)) &&
    (typeof candidate.pdf_storage_key === "string" ||
      candidate.pdf_storage_key === null) &&
    (typeof candidate.pdf_url === "string" || candidate.pdf_url === null) &&
    (typeof candidate.log_text === "string" || candidate.log_text === null) &&
    (typeof candidate.error_message === "string" || candidate.error_message === null) &&
    typeof candidate.created_at === "string" &&
    typeof candidate.updated_at === "string" &&
    (typeof candidate.started_at === "string" || candidate.started_at === null) &&
    (typeof candidate.finished_at === "string" || candidate.finished_at === null)
  );
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isReferenceItem(value: unknown): value is ReferenceItem {
  if (!isRecord(value)) {
    return false;
  }
  return (
    typeof value.id === "string" &&
    typeof value.owner_id === "string" &&
    (typeof value.paper_id === "string" || value.paper_id === null) &&
    typeof value.title === "string" &&
    Array.isArray(value.authors) &&
    (typeof value.publication_year === "number" || value.publication_year === null) &&
    (typeof value.venue === "string" || value.venue === null) &&
    (typeof value.doi === "string" || value.doi === null) &&
    (typeof value.url === "string" || value.url === null) &&
    typeof value.source_type === "string" &&
    (typeof value.source_identifier === "string" || value.source_identifier === null) &&
    (typeof value.source_url === "string" || value.source_url === null) &&
    (typeof value.abstract === "string" || value.abstract === null) &&
    isRecord(value.metadata) &&
    typeof value.created_at === "string" &&
    typeof value.updated_at === "string"
  );
}

function isReferenceChunk(value: unknown): value is ReferenceChunk {
  if (!isRecord(value)) {
    return false;
  }
  return (
    typeof value.id === "string" &&
    typeof value.reference_id === "string" &&
    typeof value.chunk_index === "number" &&
    typeof value.content === "string" &&
    (typeof value.token_count === "number" || value.token_count === null) &&
    isRecord(value.metadata) &&
    typeof value.created_at === "string"
  );
}

function isReferenceUploadResponse(value: unknown): value is ReferenceUploadResponse {
  if (!isRecord(value)) {
    return false;
  }
  return (
    isReferenceItem(value.reference) &&
    Array.isArray(value.chunks) &&
    value.chunks.every(isReferenceChunk) &&
    typeof value.extracted_text_chars === "number"
  );
}

async function parsePaperResponse(response: Response): Promise<Paper> {
  const body: unknown = await response.json();
  if (!isPaper(body)) {
    throw new Error("Paper response had an unexpected shape");
  }
  return body;
}

async function parseCompilationJobResponse(
  response: Response
): Promise<CompilationJob> {
  const body: unknown = await response.json();
  if (!isCompilationJob(body)) {
    throw new Error("Compilation job response had an unexpected shape");
  }
  return body;
}

export async function listTemplates(signal?: AbortSignal): Promise<Template[]> {
  const response = await fetch("/api/templates", {
    credentials: "include",
    headers: { Accept: "application/json" },
    signal
  });
  if (!response.ok) {
    throw new Error(`Template list failed with ${response.status}`);
  }
  const body: unknown = await response.json();
  if (!Array.isArray(body) || !body.every(isTemplate)) {
    throw new Error("Template list response had an unexpected shape");
  }
  return body;
}

export async function createPaperFromTemplate(
  templateId: string,
  title?: string
): Promise<Paper> {
  const response = await fetch(`/api/templates/${templateId}/papers`, {
    body: JSON.stringify({ title: title?.trim() || undefined }),
    credentials: "include",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json"
    },
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(`Template paper creation failed with ${response.status}`);
  }
  return parsePaperResponse(response);
}

export async function listPapers(signal?: AbortSignal): Promise<Paper[]> {
  const response = await fetch("/api/papers", {
    credentials: "include",
    headers: { Accept: "application/json" },
    signal
  });
  if (!response.ok) {
    throw new Error(`Paper list failed with ${response.status}`);
  }
  const body: unknown = await response.json();
  if (!Array.isArray(body) || !body.every(isPaper)) {
    throw new Error("Paper list response had an unexpected shape");
  }
  return body;
}

export async function getPaper(paperId: string, signal?: AbortSignal): Promise<Paper> {
  const response = await fetch(`/api/papers/${paperId}`, {
    credentials: "include",
    headers: { Accept: "application/json" },
    signal
  });
  if (!response.ok) {
    throw new Error(`Paper lookup failed with ${response.status}`);
  }
  return parsePaperResponse(response);
}

export async function createPaper(payload: PaperCreatePayload): Promise<Paper> {
  const response = await fetch("/api/papers", {
    body: JSON.stringify(payload),
    credentials: "include",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json"
    },
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(`Paper creation failed with ${response.status}`);
  }
  return parsePaperResponse(response);
}

export async function updatePaper(
  paperId: string,
  payload: PaperUpdatePayload
): Promise<Paper> {
  const response = await fetch(`/api/papers/${paperId}`, {
    body: JSON.stringify(payload),
    credentials: "include",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json"
    },
    method: "PATCH"
  });
  if (!response.ok) {
    throw new Error(`Paper update failed with ${response.status}`);
  }
  return parsePaperResponse(response);
}

export async function deletePaper(paperId: string): Promise<void> {
  const response = await fetch(`/api/papers/${paperId}`, {
    credentials: "include",
    method: "DELETE"
  });
  if (!response.ok) {
    throw new Error(`Paper deletion failed with ${response.status}`);
  }
}

export async function compilePaper(paperId: string): Promise<CompilationJob> {
  const response = await fetch(`/api/papers/${paperId}/compile`, {
    credentials: "include",
    headers: { Accept: "application/json" },
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(`Paper compilation failed to start with ${response.status}`);
  }
  return parseCompilationJobResponse(response);
}

export async function getCompileJob(
  jobId: string,
  signal?: AbortSignal
): Promise<CompilationJob> {
  const response = await fetch(`/api/compile-jobs/${jobId}`, {
    credentials: "include",
    headers: { Accept: "application/json" },
    signal
  });
  if (!response.ok) {
    throw new Error(`Compilation job lookup failed with ${response.status}`);
  }
  return parseCompilationJobResponse(response);
}

export async function listPaperCompileJobs(
  paperId: string,
  signal?: AbortSignal
): Promise<CompilationJob[]> {
  const response = await fetch(`/api/papers/${paperId}/compile-jobs`, {
    credentials: "include",
    headers: { Accept: "application/json" },
    signal
  });
  if (!response.ok) {
    throw new Error(`Compilation job list failed with ${response.status}`);
  }
  const body: unknown = await response.json();
  if (!Array.isArray(body) || !body.every(isCompilationJob)) {
    throw new Error("Compilation job list response had an unexpected shape");
  }
  return body;
}

export async function listPaperReferences(
  paperId: string,
  signal?: AbortSignal
): Promise<ReferenceItem[]> {
  const response = await fetch(`/api/references/by-paper/${paperId}`, {
    credentials: "include",
    headers: { Accept: "application/json" },
    signal
  });
  if (!response.ok) {
    throw new Error(`Reference list failed with ${response.status}`);
  }
  const body: unknown = await response.json();
  if (!Array.isArray(body) || !body.every(isReferenceItem)) {
    throw new Error("Reference list response had an unexpected shape");
  }
  return body;
}

export async function uploadReferencePdf(
  paperId: string,
  file: File,
  title?: string
): Promise<ReferenceUploadResponse> {
  const formData = new FormData();
  formData.set("file", file);
  formData.set("paper_id", paperId);
  if (title?.trim()) {
    formData.set("title", title.trim());
  }

  const response = await fetch("/api/references/uploads/pdf", {
    body: formData,
    credentials: "include",
    headers: { Accept: "application/json" },
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(`Reference upload failed with ${response.status}`);
  }
  const body: unknown = await response.json();
  if (!isReferenceUploadResponse(body)) {
    throw new Error("Reference upload response had an unexpected shape");
  }
  return body;
}

export async function deleteReference(referenceId: string): Promise<void> {
  const response = await fetch(`/api/references/${referenceId}`, {
    credentials: "include",
    method: "DELETE"
  });
  if (!response.ok) {
    throw new Error(`Reference deletion failed with ${response.status}`);
  }
}
