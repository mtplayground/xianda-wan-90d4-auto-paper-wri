import type { Paper, PaperCreatePayload, Template } from "./types";

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

async function parsePaperResponse(response: Response): Promise<Paper> {
  const body: unknown = await response.json();
  if (!isPaper(body)) {
    throw new Error("Paper response had an unexpected shape");
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

export async function deletePaper(paperId: string): Promise<void> {
  const response = await fetch(`/api/papers/${paperId}`, {
    credentials: "include",
    method: "DELETE"
  });
  if (!response.ok) {
    throw new Error(`Paper deletion failed with ${response.status}`);
  }
}
