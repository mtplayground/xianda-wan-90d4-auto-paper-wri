import { useCallback, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import { fetchCurrentUser } from "./api";
import { AuthContext } from "./context";
import type { AuthContextValue } from "./context";
import type { AuthProviderName, AuthStatus, AuthUser } from "./types";

function safeReturnPath(returnTo?: string): string {
  const fallback = `${window.location.pathname}${window.location.search}`;
  const candidate = returnTo ?? fallback;
  if (!candidate.startsWith("/") || candidate.startsWith("/api")) {
    return "/";
  }
  return candidate;
}

function redirectToAuth(path: string, returnTo?: string): void {
  const url = new URL(path, window.location.origin);
  url.searchParams.set("return_to", safeReturnPath(returnTo));
  window.location.assign(url.toString());
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setStatus("loading");
    setError(null);
    try {
      const currentUser = await fetchCurrentUser();
      setUser(currentUser);
      setStatus(currentUser ? "authenticated" : "anonymous");
    } catch (authError) {
      setUser(null);
      setStatus("error");
      setError(
        authError instanceof Error
          ? authError.message
          : "Could not load the current session"
      );
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    setStatus("loading");
    setError(null);
    void fetchCurrentUser(controller.signal)
      .then((currentUser) => {
        setUser(currentUser);
        setStatus(currentUser ? "authenticated" : "anonymous");
      })
      .catch((authError: unknown) => {
        if (controller.signal.aborted) {
          return;
        }
        setUser(null);
        setStatus("error");
        setError(
          authError instanceof Error
            ? authError.message
            : "Could not load the current session"
        );
      });
    return () => {
      controller.abort();
    };
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      status,
      error,
      login(provider?: AuthProviderName, returnTo?: string) {
        const path = provider
          ? `/api/auth/oauth/${provider}/redirect`
          : "/api/auth/login";
        redirectToAuth(path, returnTo);
      },
      register(returnTo?: string) {
        redirectToAuth("/api/auth/register", returnTo);
      },
      refresh
    }),
    [error, refresh, status, user]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
