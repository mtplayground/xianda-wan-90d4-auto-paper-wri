export class ApiError extends Error {
  readonly code: string | null;
  readonly details: string[];
  readonly status: number;

  constructor(
    message: string,
    options: { status: number; code?: string | null; details?: string[] }
  ) {
    super(message);
    this.name = "ApiError";
    this.status = options.status;
    this.code = options.code ?? null;
    this.details = options.details ?? [];
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function detailMessage(value: unknown): string | null {
  if (typeof value === "string") {
    return value;
  }
  if (!isRecord(value)) {
    return null;
  }
  const message = value.message ?? value.msg;
  if (typeof message !== "string" || !message.trim()) {
    return null;
  }
  const location = value.location ?? value.loc;
  if (typeof location === "string" && location.trim()) {
    return `${location}: ${message}`;
  }
  if (Array.isArray(location) && location.length > 0) {
    return `${location.join(".")}: ${message}`;
  }
  return message;
}

function extractDetailMessages(value: unknown): string[] {
  if (!Array.isArray(value)) {
    const message = detailMessage(value);
    return message ? [message] : [];
  }
  return value
    .map((item) => detailMessage(item))
    .filter((message): message is string => Boolean(message));
}

async function readJsonBody(response: Response): Promise<unknown> {
  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) {
    return null;
  }
  try {
    return await response.json();
  } catch {
    return null;
  }
}

export async function apiErrorFromResponse(
  response: Response,
  fallbackMessage: string
): Promise<ApiError> {
  const body = await readJsonBody(response);
  let code: string | null = null;
  let message = fallbackMessage;
  let details: string[] = [];

  if (isRecord(body) && isRecord(body.error)) {
    if (typeof body.error.code === "string") {
      code = body.error.code;
    }
    if (typeof body.error.message === "string" && body.error.message.trim()) {
      message = body.error.message;
    }
    details = extractDetailMessages(body.error.details);
  } else if (isRecord(body) && typeof body.detail === "string") {
    message = body.detail;
  } else if (isRecord(body) && Array.isArray(body.detail)) {
    details = extractDetailMessages(body.detail);
  }

  const detailSuffix = details.length > 0 ? `: ${details.slice(0, 3).join("; ")}` : "";
  return new ApiError(`${message}${detailSuffix}`, {
    status: response.status,
    code,
    details
  });
}
