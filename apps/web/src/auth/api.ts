import type { AuthUser } from "./types";
import { apiErrorFromResponse } from "../apiErrors";

function isAuthUser(value: unknown): value is AuthUser {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.id === "string" &&
    typeof candidate.email === "string" &&
    typeof candidate.email_verified === "boolean" &&
    (typeof candidate.display_name === "string" || candidate.display_name === null) &&
    (typeof candidate.picture_url === "string" || candidate.picture_url === null) &&
    typeof candidate.created === "boolean"
  );
}

export async function fetchCurrentUser(signal?: AbortSignal): Promise<AuthUser | null> {
  const response = await fetch("/api/auth/me", {
    credentials: "include",
    headers: { Accept: "application/json" },
    signal
  });

  if (response.status === 401) {
    return null;
  }

  if (!response.ok) {
    throw await apiErrorFromResponse(response, "Could not verify authentication");
  }

  const body: unknown = await response.json();
  if (!isAuthUser(body)) {
    throw new Error("Auth check returned an unexpected response");
  }

  return body;
}
