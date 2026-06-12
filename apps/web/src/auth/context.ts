import { createContext } from "react";

import type { AuthProviderName, AuthStatus, AuthUser } from "./types";

export type AuthContextValue = {
  user: AuthUser | null;
  status: AuthStatus;
  error: string | null;
  login: (provider?: AuthProviderName, returnTo?: string) => void;
  register: (returnTo?: string) => void;
  refresh: () => Promise<void>;
};

export const AuthContext = createContext<AuthContextValue | null>(null);
