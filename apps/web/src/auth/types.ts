export type AuthStatus = "loading" | "authenticated" | "anonymous" | "error";

export type AuthProviderName = "google" | "github";

export type AuthUser = {
  id: string;
  email: string;
  email_verified: boolean;
  display_name: string | null;
  picture_url: string | null;
  created: boolean;
};
