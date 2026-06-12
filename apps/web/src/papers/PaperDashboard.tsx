import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";

import {
  createPaper,
  createPaperFromTemplate,
  deletePaper,
  listPapers,
  listTemplates
} from "./api";
import type { Paper, Template } from "./types";

const starterLatex = String.raw`\section{Introduction}

Start drafting here.
`;

function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(new Date(value));
}

function sourceSummary(source: string): string {
  const compact = source.replace(/\s+/g, " ").trim();
  if (!compact) {
    return "No source yet";
  }
  return compact.length > 130 ? `${compact.slice(0, 130)}...` : compact;
}

export function PaperDashboard() {
  const [papers, setPapers] = useState<Paper[]>([]);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [title, setTitle] = useState("");
  const [latexSource, setLatexSource] = useState(starterLatex);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingTemplates, setIsLoadingTemplates] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [creatingFromTemplateId, setCreatingFromTemplateId] = useState<string | null>(
    null
  );
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [templateError, setTemplateError] = useState<string | null>(null);

  const totalSourceCharacters = useMemo(
    () => papers.reduce((total, paper) => total + paper.latex_source.length, 0),
    [papers]
  );

  useEffect(() => {
    const controller = new AbortController();
    setIsLoading(true);
    setError(null);
    void listPapers(controller.signal)
      .then((paperList) => {
        setPapers(paperList);
      })
      .catch((listError: unknown) => {
        if (controller.signal.aborted) {
          return;
        }
        setError(
          listError instanceof Error ? listError.message : "Could not load papers"
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
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    setIsLoadingTemplates(true);
    setTemplateError(null);
    void listTemplates(controller.signal)
      .then((templateList) => {
        setTemplates(templateList);
      })
      .catch((listError: unknown) => {
        if (controller.signal.aborted) {
          return;
        }
        setTemplateError(
          listError instanceof Error ? listError.message : "Could not load templates"
        );
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setIsLoadingTemplates(false);
        }
      });
    return () => {
      controller.abort();
    };
  }, []);

  async function handleCreatePaper(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsCreating(true);
    setError(null);
    try {
      const createdPaper = await createPaper({
        title,
        latex_source: latexSource
      });
      setPapers((currentPapers) => [createdPaper, ...currentPapers]);
      setTitle("");
      setLatexSource(starterLatex);
    } catch (createError) {
      setError(
        createError instanceof Error ? createError.message : "Could not create paper"
      );
    } finally {
      setIsCreating(false);
    }
  }

  async function handleDeletePaper(paper: Paper) {
    const shouldDelete = window.confirm(`Delete "${paper.title}"?`);
    if (!shouldDelete) {
      return;
    }
    setDeletingId(paper.id);
    setError(null);
    try {
      await deletePaper(paper.id);
      setPapers((currentPapers) =>
        currentPapers.filter((currentPaper) => currentPaper.id !== paper.id)
      );
    } catch (deleteError) {
      setError(
        deleteError instanceof Error ? deleteError.message : "Could not delete paper"
      );
    } finally {
      setDeletingId(null);
    }
  }

  async function handleCreateFromTemplate(template: Template) {
    setCreatingFromTemplateId(template.id);
    setTemplateError(null);
    try {
      const createdPaper = await createPaperFromTemplate(template.id, template.name);
      setPapers((currentPapers) => [createdPaper, ...currentPapers]);
      window.location.href = `/papers/${createdPaper.id}`;
    } catch (createError) {
      setTemplateError(
        createError instanceof Error
          ? createError.message
          : "Could not create paper from template"
      );
    } finally {
      setCreatingFromTemplateId(null);
    }
  }

  return (
    <div className="mt-8 grid gap-4 lg:grid-cols-[0.95fr_1.05fr]">
      <section className="rounded-md border border-zinc-200 bg-white p-5 shadow-sm">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold tracking-normal">New paper</h2>
            <p className="mt-1 text-sm text-zinc-500">
              {papers.length} {papers.length === 1 ? "paper" : "papers"} in this
              workspace
            </p>
          </div>
          <span className="rounded-full bg-rose-100 px-3 py-1 text-xs font-semibold text-rose-800">
            {totalSourceCharacters.toLocaleString()} chars
          </span>
        </div>

        <form
          className="mt-5 grid gap-4"
          onSubmit={(event) => void handleCreatePaper(event)}
        >
          <label className="grid gap-2">
            <span className="text-sm font-medium text-zinc-700">Title</span>
            <input
              className="h-11 rounded-md border border-zinc-300 px-3 text-sm outline-none transition focus:border-teal-600 focus:ring-2 focus:ring-teal-100"
              maxLength={255}
              name="title"
              required
              type="text"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
            />
          </label>
          <label className="grid gap-2">
            <span className="text-sm font-medium text-zinc-700">LaTeX source</span>
            <textarea
              className="min-h-40 resize-y rounded-md border border-zinc-300 px-3 py-3 font-mono text-sm outline-none transition focus:border-teal-600 focus:ring-2 focus:ring-teal-100"
              name="latex_source"
              value={latexSource}
              onChange={(event) => setLatexSource(event.target.value)}
            />
          </label>
          <button
            className="h-11 rounded-md bg-zinc-950 px-4 text-sm font-semibold text-white transition hover:bg-zinc-800 disabled:cursor-not-allowed disabled:bg-zinc-400"
            disabled={isCreating || !title.trim()}
            type="submit"
          >
            {isCreating ? "Creating..." : "+ Create paper"}
          </button>
        </form>

        <div className="mt-6 border-t border-zinc-200 pt-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-base font-semibold tracking-normal">
                Template gallery
              </h2>
              <p className="mt-1 text-sm text-zinc-500">
                Start a paper with uploaded or built-in LaTeX source.
              </p>
            </div>
            {isLoadingTemplates ? (
              <span className="text-sm text-zinc-500">Loading</span>
            ) : (
              <span className="text-sm text-zinc-500">
                {templates.length} {templates.length === 1 ? "template" : "templates"}
              </span>
            )}
          </div>

          {templateError ? (
            <div className="mt-4 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-900">
              {templateError}
            </div>
          ) : null}

          <div className="mt-4 grid gap-3">
            {isLoadingTemplates ? (
              <div className="rounded-md border border-zinc-200 p-4">
                <div className="h-4 w-1/2 rounded bg-zinc-200" />
                <div className="mt-3 h-3 w-full rounded bg-zinc-100" />
              </div>
            ) : null}

            {!isLoadingTemplates && templates.length === 0 ? (
              <div className="rounded-md border border-dashed border-zinc-300 p-4 text-sm text-zinc-600">
                No templates available yet.
              </div>
            ) : null}

            {templates.map((template) => (
              <article
                className="rounded-md border border-zinc-200 p-4 transition hover:border-zinc-300 hover:bg-zinc-50"
                key={template.id}
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="truncate text-sm font-semibold text-zinc-950">
                        {template.name}
                      </h3>
                      <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-xs font-semibold text-zinc-700">
                        {template.is_built_in ? "Built-in" : "Uploaded"}
                      </span>
                    </div>
                    {template.description ? (
                      <p className="mt-2 text-sm leading-6 text-zinc-600">
                        {template.description}
                      </p>
                    ) : null}
                  </div>
                  <button
                    className="rounded-md bg-teal-700 px-3 py-1.5 text-sm font-semibold text-white transition hover:bg-teal-800 disabled:cursor-not-allowed disabled:bg-zinc-400"
                    disabled={creatingFromTemplateId === template.id}
                    type="button"
                    onClick={() => void handleCreateFromTemplate(template)}
                  >
                    {creatingFromTemplateId === template.id ? "Creating..." : "Use"}
                  </button>
                </div>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="rounded-md border border-zinc-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-lg font-semibold tracking-normal">Papers</h2>
          {isLoading ? (
            <span className="text-sm text-zinc-500">Loading</span>
          ) : (
            <span className="text-sm text-zinc-500">{papers.length} total</span>
          )}
        </div>

        {error ? (
          <div className="mt-4 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-900">
            {error}
          </div>
        ) : null}

        <div className="mt-5 grid gap-3">
          {isLoading ? (
            <div className="rounded-md border border-zinc-200 p-4">
              <div className="h-4 w-2/3 rounded bg-zinc-200" />
              <div className="mt-3 h-3 w-full rounded bg-zinc-100" />
              <div className="mt-2 h-3 w-4/5 rounded bg-zinc-100" />
            </div>
          ) : null}

          {!isLoading && papers.length === 0 ? (
            <div className="rounded-md border border-dashed border-zinc-300 p-6 text-center">
              <p className="font-semibold text-zinc-950">No papers yet</p>
              <p className="mt-2 text-sm leading-6 text-zinc-600">
                Create a paper to start building the dashboard.
              </p>
            </div>
          ) : null}

          {papers.map((paper) => (
            <article
              className="rounded-md border border-zinc-200 p-4 transition hover:border-zinc-300 hover:bg-zinc-50"
              key={paper.id}
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <h3 className="truncate text-base font-semibold text-zinc-950">
                    {paper.title}
                  </h3>
                  <p className="mt-1 text-xs text-zinc-500">
                    Updated {formatDate(paper.updated_at)}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <a
                    className="rounded-md border border-zinc-300 px-3 py-1.5 text-sm font-semibold text-zinc-800 transition hover:bg-zinc-100"
                    href={`/papers/${paper.id}`}
                  >
                    Open
                  </a>
                  <button
                    className="rounded-md border border-red-200 px-3 py-1.5 text-sm font-semibold text-red-700 transition hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-60"
                    disabled={deletingId === paper.id}
                    type="button"
                    onClick={() => void handleDeletePaper(paper)}
                  >
                    {deletingId === paper.id ? "Deleting..." : "Delete"}
                  </button>
                </div>
              </div>
              <p className="mt-3 text-sm leading-6 text-zinc-700">
                {sourceSummary(paper.latex_source)}
              </p>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
