import type { AuthProviderName, AuthUser } from "./auth/types";
import { useAuth } from "./auth/useAuth";
import { PaperDashboard } from "./papers/PaperDashboard";

const providerLabels: Record<AuthProviderName, string> = {
  google: "Google",
  github: "GitHub"
};

function ProviderButton({ provider }: { provider: AuthProviderName }) {
  const { login } = useAuth();
  return (
    <button
      className="flex h-11 items-center justify-center gap-3 rounded-md border border-zinc-300 bg-white px-4 text-sm font-semibold text-zinc-900 transition hover:border-zinc-500 hover:bg-zinc-50"
      type="button"
      onClick={() => login(provider, "/dashboard")}
    >
      <span className="flex size-6 items-center justify-center rounded-full border border-zinc-300 text-xs font-bold">
        {providerLabels[provider].slice(0, 1)}
      </span>
      Continue with {providerLabels[provider]}
    </button>
  );
}

function Header() {
  const { status, user } = useAuth();
  return (
    <header className="border-b border-zinc-200 bg-white/90 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-5">
        <a className="text-base font-semibold text-zinc-950" href="/">
          Academic paper workspace
        </a>
        <nav className="flex items-center gap-2">
          {status === "authenticated" && user ? (
            <a
              className="rounded-md bg-zinc-950 px-3 py-2 text-sm font-medium text-white hover:bg-zinc-800"
              href="/dashboard"
            >
              Dashboard
            </a>
          ) : (
            <>
              <a
                className="rounded-md px-3 py-2 text-sm font-medium text-zinc-700 hover:bg-zinc-100"
                href="/login"
              >
                Sign in
              </a>
              <a
                className="rounded-md bg-zinc-950 px-3 py-2 text-sm font-medium text-white hover:bg-zinc-800"
                href="/register"
              >
                Register
              </a>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}

function LoadingView() {
  return (
    <main className="grid min-h-screen place-items-center bg-zinc-50 px-5 text-zinc-900">
      <div className="h-12 w-12 animate-spin rounded-full border-4 border-zinc-200 border-t-teal-600" />
    </main>
  );
}

function AuthErrorBanner() {
  const { error, refresh, status } = useAuth();
  if (status !== "error") {
    return null;
  }
  return (
    <div className="border-b border-red-200 bg-red-50 px-5 py-3 text-sm text-red-900">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3">
        <span>{error ?? "Could not load the current session."}</span>
        <button
          className="rounded-md border border-red-300 px-3 py-1.5 font-medium hover:bg-red-100"
          type="button"
          onClick={() => void refresh()}
        >
          Retry
        </button>
      </div>
    </div>
  );
}

function LandingPage() {
  const { login, register } = useAuth();
  return (
    <main className="bg-zinc-50 text-zinc-950">
      <section className="mx-auto grid min-h-[calc(100vh-4rem)] max-w-6xl items-center gap-10 px-5 py-10 lg:grid-cols-[1.02fr_0.98fr]">
        <div className="max-w-2xl">
          <p className="text-sm font-semibold uppercase tracking-wide text-teal-700">
            Paper drafting, references, and AI assistance
          </p>
          <h1 className="mt-4 text-4xl font-semibold tracking-normal text-zinc-950 sm:text-5xl">
            Academic paper workspace
          </h1>
          <p className="mt-5 text-lg leading-8 text-zinc-700">
            Draft research papers with templates, compilation, references, and writing
            support in one authenticated workspace.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <button
              className="rounded-md bg-zinc-950 px-5 py-3 text-sm font-semibold text-white transition hover:bg-zinc-800"
              type="button"
              onClick={() => login(undefined, "/dashboard")}
            >
              Sign in
            </button>
            <button
              className="rounded-md border border-zinc-300 bg-white px-5 py-3 text-sm font-semibold text-zinc-900 transition hover:border-zinc-500 hover:bg-zinc-50"
              type="button"
              onClick={() => register("/dashboard")}
            >
              Register
            </button>
          </div>
        </div>
        <div className="grid gap-4">
          <div className="rounded-md border border-zinc-200 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between border-b border-zinc-200 pb-4">
              <div>
                <p className="text-sm font-semibold text-zinc-950">Paper draft</p>
                <p className="text-xs text-zinc-500">Methods section</p>
              </div>
              <span className="rounded-full bg-teal-100 px-3 py-1 text-xs font-semibold text-teal-800">
                Synced
              </span>
            </div>
            <div className="mt-5 space-y-3">
              <div className="h-3 w-11/12 rounded bg-zinc-200" />
              <div className="h-3 w-10/12 rounded bg-zinc-200" />
              <div className="h-3 w-8/12 rounded bg-zinc-200" />
            </div>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-md border border-zinc-200 bg-white p-5 shadow-sm">
              <p className="text-sm font-semibold text-zinc-950">References</p>
              <p className="mt-4 text-3xl font-semibold text-teal-700">18</p>
            </div>
            <div className="rounded-md border border-zinc-200 bg-white p-5 shadow-sm">
              <p className="text-sm font-semibold text-zinc-950">Compile</p>
              <p className="mt-4 text-3xl font-semibold text-rose-700">PDF</p>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}

function AuthPage({ mode }: { mode: "login" | "register" }) {
  const { login, register, status } = useAuth();
  const isRegister = mode === "register";

  if (status === "authenticated") {
    return <DashboardPage />;
  }

  return (
    <main className="bg-zinc-50 text-zinc-950">
      <section className="mx-auto grid min-h-[calc(100vh-4rem)] max-w-6xl items-center gap-10 px-5 py-10 lg:grid-cols-[0.9fr_1.1fr]">
        <div className="rounded-md border border-zinc-200 bg-white p-6 shadow-sm">
          <h1 className="text-2xl font-semibold tracking-normal">
            {isRegister ? "Create your workspace" : "Sign in to your workspace"}
          </h1>
          <div className="mt-6 grid gap-3">
            <ProviderButton provider="google" />
            <ProviderButton provider="github" />
          </div>
          <div className="mt-6 border-t border-zinc-200 pt-5">
            <button
              className="w-full rounded-md bg-zinc-950 px-4 py-3 text-sm font-semibold text-white transition hover:bg-zinc-800"
              type="button"
              onClick={() =>
                isRegister ? register("/dashboard") : login(undefined, "/dashboard")
              }
            >
              {isRegister ? "Register with myClawTeam" : "Continue with myClawTeam"}
            </button>
          </div>
          <p className="mt-5 text-sm text-zinc-600">
            {isRegister ? "Already registered?" : "New workspace?"}{" "}
            <a
              className="font-semibold text-teal-700 hover:text-teal-800"
              href={isRegister ? "/login" : "/register"}
            >
              {isRegister ? "Sign in" : "Register"}
            </a>
          </p>
        </div>
        <div className="grid gap-4">
          <div className="rounded-md border border-zinc-200 bg-white p-5 shadow-sm">
            <p className="text-sm font-semibold uppercase tracking-wide text-teal-700">
              Workspace access
            </p>
            <h2 className="mt-3 text-3xl font-semibold tracking-normal text-zinc-950">
              Keep drafts, references, and paper history tied to one account.
            </h2>
            <p className="mt-4 leading-7 text-zinc-700">
              Return to the same research workspace across paper drafts and supporting
              materials.
            </p>
          </div>
          <div className="rounded-md border border-zinc-200 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between gap-4">
              <span className="text-sm font-semibold text-zinc-950">
                Return destination
              </span>
              <span className="rounded-full bg-rose-100 px-3 py-1 text-xs font-semibold text-rose-800">
                /dashboard
              </span>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}

function UserAvatar({ user }: { user: AuthUser }) {
  if (user.picture_url) {
    return (
      <img
        alt=""
        className="size-12 rounded-full border border-zinc-200 object-cover"
        src={user.picture_url}
      />
    );
  }
  return (
    <div className="flex size-12 items-center justify-center rounded-full bg-teal-100 text-base font-semibold text-teal-800">
      {(user.display_name ?? user.email).slice(0, 1).toUpperCase()}
    </div>
  );
}

function DashboardPage() {
  const { user } = useAuth();
  if (!user) {
    return <LandingPage />;
  }

  const displayName = user.display_name ?? user.email;

  return (
    <main className="min-h-[calc(100vh-4rem)] bg-zinc-50 px-5 py-8 text-zinc-950">
      <section className="mx-auto max-w-6xl">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <UserAvatar user={user} />
            <div>
              <p className="text-sm font-medium text-zinc-500">Signed in</p>
              <h1 className="text-2xl font-semibold tracking-normal">{displayName}</h1>
            </div>
          </div>
          <span className="rounded-full bg-teal-100 px-3 py-1 text-sm font-semibold text-teal-800">
            {user.created ? "Registration complete" : "Welcome back"}
          </span>
        </div>

        <PaperDashboard />
      </section>
    </main>
  );
}

function RouterView() {
  const { status } = useAuth();
  const path = window.location.pathname;

  if (status === "loading") {
    return <LoadingView />;
  }

  if (path === "/login") {
    return <AuthPage mode="login" />;
  }

  if (path === "/register") {
    return <AuthPage mode="register" />;
  }

  if (path === "/dashboard") {
    return status === "authenticated" ? <DashboardPage /> : <AuthPage mode="login" />;
  }

  return status === "authenticated" ? <DashboardPage /> : <LandingPage />;
}

export function App() {
  return (
    <div className="min-h-screen bg-zinc-50">
      <Header />
      <AuthErrorBanner />
      <RouterView />
    </div>
  );
}
