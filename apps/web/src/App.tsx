export function App() {
  return (
    <main className="min-h-screen bg-zinc-50 text-zinc-950">
      <section className="mx-auto flex min-h-screen max-w-5xl flex-col justify-center px-6 py-16">
        <p className="text-sm font-medium uppercase tracking-wide text-teal-700">
          Repository initialized
        </p>
        <h1 className="mt-4 max-w-3xl text-4xl font-semibold tracking-normal text-zinc-950 sm:text-5xl">
          Frontend and backend scaffolds are ready for feature work.
        </h1>
        <p className="mt-5 max-w-2xl text-lg leading-8 text-zinc-700">
          This React and Tailwind SPA is wired to a FastAPI service under the same
          repository. Future issues can add authentication, papers, templates,
          compilation, references, and AI workflows on top of this structure.
        </p>
        <div className="mt-8 flex flex-wrap gap-3 text-sm font-medium">
          <a
            className="rounded-md bg-zinc-950 px-4 py-2 text-white transition hover:bg-zinc-800"
            href="/api/health"
          >
            API health
          </a>
          <span className="rounded-md border border-zinc-300 px-4 py-2 text-zinc-700">
            React + Tailwind
          </span>
          <span className="rounded-md border border-zinc-300 px-4 py-2 text-zinc-700">
            FastAPI
          </span>
        </div>
      </section>
    </main>
  );
}
