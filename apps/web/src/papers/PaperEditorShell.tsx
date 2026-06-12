import { useEffect, useMemo, useState } from "react";

import { getPaper } from "./api";
import type { Paper } from "./types";

function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(new Date(value));
}

function countLines(source: string): number {
  if (!source) {
    return 0;
  }
  return source.split(/\r\n|\r|\n/).length;
}

function EditorLoadingView() {
  return (
    <div className="grid min-h-[34rem] place-items-center rounded-md border border-zinc-200 bg-white p-8 shadow-sm">
      <div className="grid gap-4 text-center">
        <div className="mx-auto h-12 w-12 animate-spin rounded-full border-4 border-zinc-200 border-t-teal-600" />
        <p className="text-sm font-medium text-zinc-600">Loading paper</p>
      </div>
    </div>
  );
}

function EditorErrorView({ message }: { message: string }) {
  return (
    <div className="rounded-md border border-red-200 bg-red-50 p-5 text-red-900">
      <p className="text-sm font-semibold">Could not open paper</p>
      <p className="mt-2 text-sm leading-6">{message}</p>
      <a
        className="mt-4 inline-flex rounded-md border border-red-300 px-3 py-2 text-sm font-semibold hover:bg-red-100"
        href="/dashboard"
      >
        Back to dashboard
      </a>
    </div>
  );
}

function PreviewPlaceholder({ paper }: { paper: Paper }) {
  return (
    <div className="flex min-h-[34rem] flex-col rounded-md border border-zinc-200 bg-white shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-zinc-200 px-5 py-4">
        <div>
          <h2 className="text-base font-semibold text-zinc-950">PDF preview</h2>
          <p className="mt-1 text-xs text-zinc-500">Compilation wiring lands later</p>
        </div>
        <span className="rounded-full bg-zinc-100 px-3 py-1 text-xs font-semibold text-zinc-700">
          Preview shell
        </span>
      </div>
      <div className="grid flex-1 place-items-center bg-zinc-100 p-4">
        <div className="flex aspect-[8.5/11] w-full max-w-md flex-col border border-zinc-300 bg-white p-8 shadow-sm">
          <div className="border-b border-zinc-200 pb-5 text-center">
            <p className="text-xl font-semibold leading-7 text-zinc-950">
              {paper.title}
            </p>
            <p className="mt-2 text-xs text-zinc-500">Draft preview</p>
          </div>
          <div className="mt-7 space-y-3">
            <div className="h-3 w-full rounded bg-zinc-200" />
            <div className="h-3 w-11/12 rounded bg-zinc-200" />
            <div className="h-3 w-10/12 rounded bg-zinc-200" />
            <div className="h-3 w-full rounded bg-zinc-200" />
            <div className="h-3 w-8/12 rounded bg-zinc-200" />
          </div>
          <div className="mt-auto grid gap-2 border-t border-zinc-200 pt-4 text-xs text-zinc-500">
            <span>Source characters: {paper.latex_source.length.toLocaleString()}</span>
            <span>Source lines: {countLines(paper.latex_source).toLocaleString()}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export function PaperEditorShell({ paperId }: { paperId: string }) {
  const [paper, setPaper] = useState<Paper | null>(null);
  const [sourceDraft, setSourceDraft] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setIsLoading(true);
    setError(null);
    void getPaper(paperId, controller.signal)
      .then((loadedPaper) => {
        setPaper(loadedPaper);
        setSourceDraft(loadedPaper.latex_source);
      })
      .catch((loadError: unknown) => {
        if (controller.signal.aborted) {
          return;
        }
        setError(
          loadError instanceof Error ? loadError.message : "Could not load paper"
        );
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setIsLoading(false);
        }
      });
    return () => {
      controller.abort();
    };
  }, [paperId]);

  const sourceStats = useMemo(
    () => ({
      characters: sourceDraft.length,
      lines: countLines(sourceDraft)
    }),
    [sourceDraft]
  );

  if (isLoading) {
    return <EditorLoadingView />;
  }

  if (error || !paper) {
    return <EditorErrorView message={error ?? "Paper was not found"} />;
  }

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <a
            className="text-sm font-semibold text-teal-700 hover:text-teal-800"
            href="/dashboard"
          >
            Back to dashboard
          </a>
          <h1 className="mt-3 text-2xl font-semibold tracking-normal text-zinc-950">
            {paper.title}
          </h1>
          <p className="mt-1 text-sm text-zinc-500">
            Updated {formatDate(paper.updated_at)}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <span className="rounded-full bg-teal-100 px-3 py-1 text-xs font-semibold text-teal-800">
            {sourceStats.lines.toLocaleString()} lines
          </span>
          <span className="rounded-full bg-rose-100 px-3 py-1 text-xs font-semibold text-rose-800">
            {sourceStats.characters.toLocaleString()} chars
          </span>
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(24rem,0.85fr)]">
        <section className="flex min-h-[34rem] flex-col rounded-md border border-zinc-200 bg-white shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-zinc-200 px-5 py-4">
            <div>
              <h2 className="text-base font-semibold text-zinc-950">LaTeX source</h2>
              <p className="mt-1 text-xs text-zinc-500">
                Draft edits stay local for now
              </p>
            </div>
            <span className="rounded-full bg-zinc-100 px-3 py-1 text-xs font-semibold text-zinc-700">
              Editor shell
            </span>
          </div>
          <textarea
            aria-label="LaTeX source"
            className="min-h-[30rem] flex-1 resize-none border-0 bg-white p-5 font-mono text-sm leading-6 text-zinc-900 outline-none"
            spellCheck={false}
            value={sourceDraft}
            onChange={(event) => setSourceDraft(event.target.value)}
          />
        </section>

        <PreviewPlaceholder paper={{ ...paper, latex_source: sourceDraft }} />
      </div>
    </div>
  );
}
