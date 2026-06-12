import { useEffect, useMemo, useRef, useState } from "react";

import {
  compilePaper,
  continuePaperText,
  deleteReference,
  getCompileJob,
  getPaper,
  listPaperReferences,
  polishPaperText,
  suggestPaperCitations,
  updatePaper,
  uploadReferencePdf
} from "./api";
import type {
  AiAssistantResponse,
  CompilationJob,
  Paper,
  ReferenceItem
} from "./types";

const POLL_INTERVAL_MS = 1800;
const MAX_REFERENCE_PDF_BYTES = 30 * 1024 * 1024;

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

function isJobActive(job: CompilationJob | null): boolean {
  return job?.status === "pending" || job?.status === "running";
}

function compileStatusLabel(job: CompilationJob | null): string {
  if (!job) {
    return "Not compiled";
  }
  if (job.status === "pending") {
    return "Queued";
  }
  if (job.status === "running") {
    return "Compiling";
  }
  if (job.status === "succeeded") {
    return "Ready";
  }
  return "Failed";
}

function metadataString(metadata: Record<string, unknown>, key: string): string | null {
  const value = metadata[key];
  return typeof value === "string" && value.trim() ? value : null;
}

function metadataNumber(metadata: Record<string, unknown>, key: string): number | null {
  const value = metadata[key];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function validateReferencePdf(file: File): string | null {
  const isPdf =
    file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
  if (!isPdf) {
    return "Reference upload must be a PDF file.";
  }
  if (file.size === 0) {
    return "Reference PDF must not be empty.";
  }
  if (file.size > MAX_REFERENCE_PDF_BYTES) {
    return "Reference PDF must be 30 MB or smaller.";
  }
  return null;
}

function surroundingText(source: string, start: number, end: number): string {
  const contextStart = Math.max(0, start - 5000);
  const contextEnd = Math.min(source.length, end + 5000);
  return source.slice(contextStart, contextEnd);
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

function PdfPreviewPanel({
  compileError,
  isStartingCompile,
  job,
  onCompile,
  paper
}: {
  compileError: string | null;
  isStartingCompile: boolean;
  job: CompilationJob | null;
  onCompile: () => void;
  paper: Paper;
}) {
  const isActive = isJobActive(job);
  const canOpenPdf = job?.status === "succeeded" && job.pdf_url;
  const jobLog = job?.log_text?.trim();
  const jobError = job?.error_message?.trim();

  return (
    <div className="flex min-h-[34rem] flex-col rounded-md border border-zinc-200 bg-white shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-zinc-200 px-5 py-4">
        <div>
          <h2 className="text-base font-semibold text-zinc-950">PDF preview</h2>
          <p className="mt-1 text-xs text-zinc-500">
            {job ? `Last job: ${job.id.slice(0, 8)}` : "Compile the current source"}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span
            className={[
              "rounded-full px-3 py-1 text-xs font-semibold",
              job?.status === "succeeded"
                ? "bg-teal-100 text-teal-800"
                : job?.status === "failed"
                  ? "bg-red-100 text-red-800"
                  : isActive
                    ? "bg-amber-100 text-amber-800"
                    : "bg-zinc-100 text-zinc-700"
            ].join(" ")}
          >
            {compileStatusLabel(job)}
          </span>
          <button
            className="h-9 rounded-md bg-zinc-950 px-3 text-sm font-semibold text-white transition hover:bg-zinc-800 disabled:cursor-not-allowed disabled:bg-zinc-400"
            disabled={isStartingCompile || isActive || !paper.latex_source.trim()}
            type="button"
            onClick={onCompile}
          >
            {isStartingCompile ? "Starting..." : isActive ? "Compiling..." : "Compile"}
          </button>
        </div>
      </div>

      {compileError ? (
        <div className="border-b border-red-200 bg-red-50 px-5 py-3 text-sm text-red-900">
          {compileError}
        </div>
      ) : null}

      <div className="grid flex-1 place-items-center bg-zinc-100 p-4">
        {canOpenPdf ? (
          <iframe
            className="h-[34rem] w-full rounded-md border border-zinc-300 bg-white shadow-sm"
            src={job.pdf_url ?? undefined}
            title={`${paper.title} PDF preview`}
          />
        ) : (
          <div className="flex aspect-[8.5/11] w-full max-w-md flex-col border border-zinc-300 bg-white p-8 shadow-sm">
            <div className="border-b border-zinc-200 pb-5 text-center">
              <p className="text-xl font-semibold leading-7 text-zinc-950">
                {paper.title}
              </p>
              <p className="mt-2 text-xs text-zinc-500">
                {isActive ? "Waiting for compiled PDF" : "No compiled PDF yet"}
              </p>
            </div>
            <div className="mt-7 space-y-3">
              <div className="h-3 w-full rounded bg-zinc-200" />
              <div className="h-3 w-11/12 rounded bg-zinc-200" />
              <div className="h-3 w-10/12 rounded bg-zinc-200" />
              <div className="h-3 w-full rounded bg-zinc-200" />
              <div className="h-3 w-8/12 rounded bg-zinc-200" />
            </div>
            <div className="mt-auto grid gap-2 border-t border-zinc-200 pt-4 text-xs text-zinc-500">
              <span>
                Source characters: {paper.latex_source.length.toLocaleString()}
              </span>
              <span>
                Source lines: {countLines(paper.latex_source).toLocaleString()}
              </span>
            </div>
          </div>
        )}
      </div>

      {job?.status === "failed" ? (
        <div className="border-t border-red-200 bg-white">
          <div className="border-b border-red-100 px-5 py-3">
            <p className="text-sm font-semibold text-red-900">LaTeX error log</p>
            {jobError ? <p className="mt-1 text-sm text-red-800">{jobError}</p> : null}
          </div>
          <pre className="max-h-72 overflow-auto whitespace-pre-wrap p-5 font-mono text-xs leading-5 text-zinc-800">
            {jobLog || "Compilation failed before TeX produced a log."}
          </pre>
        </div>
      ) : null}
    </div>
  );
}

function ReferencePanel({ paperId }: { paperId: string }) {
  const [references, setReferences] = useState<ReferenceItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [deletingReferenceId, setDeletingReferenceId] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [titleDraft, setTitleDraft] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setIsLoading(true);
    setError(null);
    void listPaperReferences(paperId, controller.signal)
      .then(setReferences)
      .catch((loadError: unknown) => {
        if (controller.signal.aborted) {
          return;
        }
        setError(
          loadError instanceof Error ? loadError.message : "Could not load references"
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

  async function handleUpload() {
    if (!selectedFile || isUploading) {
      return;
    }
    const validationError = validateReferencePdf(selectedFile);
    if (validationError) {
      setError(validationError);
      return;
    }
    setIsUploading(true);
    setError(null);
    try {
      const uploaded = await uploadReferencePdf(paperId, selectedFile, titleDraft);
      setReferences((current) => [uploaded.reference, ...current]);
      setSelectedFile(null);
      setTitleDraft("");
    } catch (uploadError) {
      setError(
        uploadError instanceof Error
          ? uploadError.message
          : "Could not upload reference"
      );
    } finally {
      setIsUploading(false);
    }
  }

  async function handleDelete(referenceId: string) {
    if (deletingReferenceId) {
      return;
    }
    setDeletingReferenceId(referenceId);
    setError(null);
    try {
      await deleteReference(referenceId);
      setReferences((current) =>
        current.filter((reference) => reference.id !== referenceId)
      );
    } catch (deleteError) {
      setError(
        deleteError instanceof Error
          ? deleteError.message
          : "Could not delete reference"
      );
    } finally {
      setDeletingReferenceId(null);
    }
  }

  return (
    <section className="rounded-md border border-zinc-200 bg-white shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-zinc-200 px-5 py-4">
        <div>
          <h2 className="text-base font-semibold text-zinc-950">References</h2>
          <p className="mt-1 text-xs text-zinc-500">
            {isLoading
              ? "Loading sources"
              : `${references.length.toLocaleString()} linked to this paper`}
          </p>
        </div>
        <span className="rounded-full bg-zinc-100 px-3 py-1 text-xs font-semibold text-zinc-700">
          Library
        </span>
      </div>

      <div className="grid gap-3 border-b border-zinc-200 p-5">
        <input
          aria-label="Reference title"
          className="h-10 rounded-md border border-zinc-300 px-3 text-sm outline-none focus:border-teal-600"
          placeholder="Reference title"
          type="text"
          value={titleDraft}
          onChange={(event) => setTitleDraft(event.target.value)}
        />
        <input
          aria-label="Reference PDF"
          className="block w-full text-sm text-zinc-700 file:mr-3 file:h-10 file:rounded-md file:border-0 file:bg-zinc-950 file:px-3 file:text-sm file:font-semibold file:text-white hover:file:bg-zinc-800"
          type="file"
          accept="application/pdf,.pdf"
          onChange={(event) => {
            const file = event.currentTarget.files?.item(0) ?? null;
            setSelectedFile(file);
            setError(file ? validateReferencePdf(file) : null);
          }}
        />
        <button
          className="h-10 rounded-md bg-zinc-950 px-3 text-sm font-semibold text-white transition hover:bg-zinc-800 disabled:cursor-not-allowed disabled:bg-zinc-400"
          disabled={!selectedFile || isUploading}
          type="button"
          onClick={() => void handleUpload()}
        >
          {isUploading ? "Uploading..." : "Upload PDF"}
        </button>
      </div>

      {error ? (
        <div className="border-b border-red-200 bg-red-50 px-5 py-3 text-sm text-red-900">
          {error}
        </div>
      ) : null}

      <div className="max-h-[28rem] overflow-auto">
        {isLoading ? (
          <div className="p-5 text-sm text-zinc-500">Loading references</div>
        ) : references.length === 0 ? (
          <div className="p-5 text-sm leading-6 text-zinc-500">
            No references linked yet.
          </div>
        ) : (
          <ul className="divide-y divide-zinc-200">
            {references.map((reference) => {
              const originalFile = metadataString(
                reference.metadata,
                "original_filename"
              );
              const pageCount = metadataNumber(reference.metadata, "page_count");
              const embeddingStatus =
                metadataString(reference.metadata, "embedding_status") ?? "queued";
              return (
                <li className="grid gap-3 p-5" key={reference.id}>
                  <div>
                    <p className="text-sm font-semibold leading-5 text-zinc-950">
                      {reference.title}
                    </p>
                    <p className="mt-1 text-xs text-zinc-500">
                      {originalFile ?? "PDF reference"}
                      {pageCount ? ` - ${pageCount.toLocaleString()} pages` : ""}
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded-full bg-teal-100 px-2.5 py-1 text-xs font-semibold text-teal-800">
                      {embeddingStatus}
                    </span>
                    {reference.source_url ? (
                      <a
                        className="rounded-md border border-zinc-300 px-3 py-1.5 text-xs font-semibold text-zinc-800 hover:bg-zinc-50"
                        href={reference.source_url}
                        rel="noreferrer"
                        target="_blank"
                      >
                        Open PDF
                      </a>
                    ) : null}
                    <button
                      className="rounded-md border border-red-200 px-3 py-1.5 text-xs font-semibold text-red-700 hover:bg-red-50 disabled:cursor-not-allowed disabled:text-red-300"
                      disabled={deletingReferenceId === reference.id}
                      type="button"
                      onClick={() => void handleDelete(reference.id)}
                    >
                      {deletingReferenceId === reference.id ? "Deleting..." : "Delete"}
                    </button>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </section>
  );
}

type AssistantAction = "polish" | "continue" | "cite";

function AssistantPanel({
  cursorIndex,
  onInsert,
  paperId,
  selectedText,
  selectionEnd,
  selectionStart,
  sourceDraft
}: {
  cursorIndex: number;
  onInsert: (start: number, end: number, text: string) => void;
  paperId: string;
  selectedText: string;
  selectionEnd: number;
  selectionStart: number;
  sourceDraft: string;
}) {
  const [action, setAction] = useState<AssistantAction>("polish");
  const [instruction, setInstruction] = useState("");
  const [referenceQuery, setReferenceQuery] = useState("");
  const [targetLength, setTargetLength] = useState<"short" | "medium" | "long">(
    "medium"
  );
  const [result, setResult] = useState<AiAssistantResponse | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const hasSelection = selectedText.trim().length > 0;
  const actionLabel =
    action === "polish" ? "Polish" : action === "continue" ? "Continue" : "Cite";

  async function runAssistant() {
    if (isRunning) {
      return;
    }
    setIsRunning(true);
    setError(null);
    setResult(null);
    try {
      if (action === "polish") {
        if (!hasSelection) {
          throw new Error("Select text in the editor before polishing");
        }
        const response = await polishPaperText(paperId, {
          selected_text: selectedText,
          surrounding_context: surroundingText(
            sourceDraft,
            selectionStart,
            selectionEnd
          ),
          instruction: instruction.trim() || undefined,
          operation: "polish",
          reference_query: referenceQuery.trim() || undefined,
          reference_limit: 5
        });
        setResult(response);
        return;
      }

      if (action === "continue") {
        const draftContext = sourceDraft.slice(0, cursorIndex).trim();
        if (!draftContext) {
          throw new Error("Place the cursor after some draft text before continuing");
        }
        const response = await continuePaperText(paperId, {
          draft_context: draftContext,
          instruction: instruction.trim() || undefined,
          target_length: targetLength,
          reference_query: referenceQuery.trim() || undefined,
          reference_limit: 5
        });
        setResult(response);
        return;
      }

      const passage = (
        hasSelection
          ? selectedText
          : surroundingText(sourceDraft, cursorIndex, cursorIndex)
      ).trim();
      if (!passage) {
        throw new Error("Select a passage or place the cursor near draft text");
      }
      const response = await suggestPaperCitations(paperId, {
        passage,
        instruction: instruction.trim() || undefined,
        reference_query: referenceQuery.trim() || undefined,
        reference_limit: 6,
        context_max_chars: 12000
      });
      setResult(response);
    } catch (assistantError) {
      setError(
        assistantError instanceof Error
          ? assistantError.message
          : "AI assistant request failed"
      );
    } finally {
      setIsRunning(false);
    }
  }

  function insertAtCursor() {
    if (!result) {
      return;
    }
    onInsert(cursorIndex, cursorIndex, result.text);
  }

  function replaceSelection() {
    if (!result || !hasSelection) {
      return;
    }
    onInsert(selectionStart, selectionEnd, result.text);
  }

  function appendToDraft() {
    if (!result) {
      return;
    }
    const separator =
      sourceDraft.endsWith("\n") || sourceDraft.length === 0 ? "" : "\n\n";
    onInsert(sourceDraft.length, sourceDraft.length, `${separator}${result.text}`);
  }

  return (
    <section className="rounded-md border border-zinc-200 bg-white shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-zinc-200 px-5 py-4">
        <div>
          <h2 className="text-base font-semibold text-zinc-950">AI assistant</h2>
          <p className="mt-1 text-xs text-zinc-500">
            {hasSelection
              ? `${selectedText.length.toLocaleString()} selected characters`
              : `Cursor at ${cursorIndex.toLocaleString()}`}
          </p>
        </div>
        <span className="rounded-full bg-zinc-100 px-3 py-1 text-xs font-semibold text-zinc-700">
          Draft tools
        </span>
      </div>

      <div className="grid gap-4 p-5">
        <div className="grid grid-cols-3 overflow-hidden rounded-md border border-zinc-300">
          {(["polish", "continue", "cite"] as const).map((value) => (
            <button
              className={[
                "h-10 text-sm font-semibold transition",
                action === value
                  ? "bg-zinc-950 text-white"
                  : "bg-white text-zinc-700 hover:bg-zinc-50"
              ].join(" ")}
              key={value}
              type="button"
              onClick={() => setAction(value)}
            >
              {value === "polish"
                ? "Polish"
                : value === "continue"
                  ? "Continue"
                  : "Cite"}
            </button>
          ))}
        </div>

        {action === "continue" ? (
          <label className="grid gap-2 text-sm font-medium text-zinc-700">
            Length
            <select
              className="h-10 rounded-md border border-zinc-300 bg-white px-3 text-sm outline-none focus:border-teal-600"
              value={targetLength}
              onChange={(event) =>
                setTargetLength(event.target.value as "short" | "medium" | "long")
              }
            >
              <option value="short">Short</option>
              <option value="medium">Medium</option>
              <option value="long">Long</option>
            </select>
          </label>
        ) : null}

        <label className="grid gap-2 text-sm font-medium text-zinc-700">
          Instruction
          <textarea
            className="min-h-20 resize-y rounded-md border border-zinc-300 p-3 text-sm leading-5 outline-none focus:border-teal-600"
            placeholder={
              action === "polish"
                ? "Tighten the prose and keep LaTeX commands intact"
                : action === "continue"
                  ? "Continue with methods details"
                  : "Prioritize citations that support this claim"
            }
            value={instruction}
            onChange={(event) => setInstruction(event.target.value)}
          />
        </label>

        <label className="grid gap-2 text-sm font-medium text-zinc-700">
          Reference query
          <input
            className="h-10 rounded-md border border-zinc-300 px-3 text-sm outline-none focus:border-teal-600"
            placeholder="Optional search terms for references"
            type="text"
            value={referenceQuery}
            onChange={(event) => setReferenceQuery(event.target.value)}
          />
        </label>

        <button
          className="h-10 rounded-md bg-zinc-950 px-3 text-sm font-semibold text-white transition hover:bg-zinc-800 disabled:cursor-not-allowed disabled:bg-zinc-400"
          disabled={isRunning || (action === "polish" && !hasSelection)}
          type="button"
          onClick={() => void runAssistant()}
        >
          {isRunning ? "Working..." : `Run ${actionLabel}`}
        </button>
      </div>

      {error ? (
        <div className="border-t border-red-200 bg-red-50 px-5 py-3 text-sm text-red-900">
          {error}
        </div>
      ) : null}

      {result ? (
        <div className="border-t border-zinc-200">
          <div className="grid gap-3 p-5">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-sm font-semibold text-zinc-950">Result</p>
              <span className="text-xs text-zinc-500">{result.model}</span>
            </div>
            <pre className="max-h-72 overflow-auto whitespace-pre-wrap rounded-md border border-zinc-200 bg-zinc-50 p-3 font-mono text-xs leading-5 text-zinc-900">
              {result.text}
            </pre>
            <div className="flex flex-wrap gap-2">
              <button
                className="rounded-md bg-teal-700 px-3 py-2 text-xs font-semibold text-white hover:bg-teal-800 disabled:cursor-not-allowed disabled:bg-zinc-300"
                disabled={!hasSelection}
                type="button"
                onClick={replaceSelection}
              >
                Replace selection
              </button>
              <button
                className="rounded-md border border-zinc-300 px-3 py-2 text-xs font-semibold text-zinc-800 hover:bg-zinc-50"
                type="button"
                onClick={insertAtCursor}
              >
                Insert at cursor
              </button>
              <button
                className="rounded-md border border-zinc-300 px-3 py-2 text-xs font-semibold text-zinc-800 hover:bg-zinc-50"
                type="button"
                onClick={appendToDraft}
              >
                Append
              </button>
            </div>
          </div>

          {result.references.length > 0 ? (
            <div className="border-t border-zinc-200 p-5">
              <p className="text-sm font-semibold text-zinc-950">Reference matches</p>
              <ul className="mt-3 grid gap-3">
                {result.references.slice(0, 4).map((reference) => (
                  <li
                    className="rounded-md border border-zinc-200 p-3 text-xs leading-5 text-zinc-600"
                    key={reference.chunk_id}
                  >
                    <p className="font-semibold text-zinc-900">
                      {reference.reference_title}
                    </p>
                    <p className="mt-1">
                      Chunk {reference.chunk_index} - score {reference.score.toFixed(3)}
                    </p>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}

export function PaperEditorShell({ paperId }: { paperId: string }) {
  const [paper, setPaper] = useState<Paper | null>(null);
  const [sourceDraft, setSourceDraft] = useState("");
  const [selectionRange, setSelectionRange] = useState({ end: 0, start: 0 });
  const [isLoading, setIsLoading] = useState(true);
  const [isStartingCompile, setIsStartingCompile] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [compileError, setCompileError] = useState<string | null>(null);
  const [compileJob, setCompileJob] = useState<CompilationJob | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setIsLoading(true);
    setError(null);
    void getPaper(paperId, controller.signal)
      .then((loadedPaper) => {
        setPaper(loadedPaper);
        setSourceDraft(loadedPaper.latex_source);
        setSelectionRange({ end: 0, start: 0 });
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

  const selectedText = sourceDraft.slice(selectionRange.start, selectionRange.end);

  useEffect(() => {
    const activeJob = compileJob;
    if (
      activeJob === null ||
      (activeJob.status !== "pending" && activeJob.status !== "running")
    ) {
      return;
    }
    const jobId = activeJob.id;
    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => {
      void getCompileJob(jobId, controller.signal)
        .then((job) => {
          setCompileJob(job);
          if (job.status === "failed") {
            setCompileError(job.error_message ?? "Compilation failed");
          } else if (job.status === "succeeded" && !job.pdf_url) {
            setCompileError("Compilation finished, but the PDF is not available.");
          } else if (job.status === "succeeded") {
            setCompileError(null);
          }
        })
        .catch((pollError: unknown) => {
          if (controller.signal.aborted) {
            return;
          }
          setCompileError(
            pollError instanceof Error
              ? pollError.message
              : "Could not refresh compilation status"
          );
        });
    }, POLL_INTERVAL_MS);
    return () => {
      controller.abort();
      window.clearTimeout(timeoutId);
    };
  }, [compileJob]);

  async function handleCompile() {
    if (!paper || isStartingCompile || isJobActive(compileJob)) {
      return;
    }
    setIsStartingCompile(true);
    setCompileError(null);
    try {
      const updatedPaper = await updatePaper(paper.id, {
        latex_source: sourceDraft
      });
      setPaper(updatedPaper);
      const job = await compilePaper(updatedPaper.id);
      setCompileJob(job);
    } catch (compileStartError) {
      setCompileError(
        compileStartError instanceof Error
          ? compileStartError.message
          : "Could not start compilation"
      );
    } finally {
      setIsStartingCompile(false);
    }
  }

  function updateSelectionFromTextarea() {
    const textarea = textareaRef.current;
    if (!textarea) {
      return;
    }
    setSelectionRange({
      end: textarea.selectionEnd,
      start: textarea.selectionStart
    });
  }

  function insertAssistantText(start: number, end: number, text: string) {
    setSourceDraft((current) => {
      const next = `${current.slice(0, start)}${text}${current.slice(end)}`;
      return next;
    });
    const cursor = start + text.length;
    setSelectionRange({ end: cursor, start: cursor });
    window.requestAnimationFrame(() => {
      const textarea = textareaRef.current;
      if (!textarea) {
        return;
      }
      textarea.focus();
      textarea.setSelectionRange(cursor, cursor);
    });
  }

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
              <p className="mt-1 text-xs text-zinc-500">Saved before each compile</p>
            </div>
            <span className="rounded-full bg-zinc-100 px-3 py-1 text-xs font-semibold text-zinc-700">
              Editor shell
            </span>
          </div>
          <textarea
            ref={textareaRef}
            aria-label="LaTeX source"
            className="min-h-[30rem] flex-1 resize-none border-0 bg-white p-5 font-mono text-sm leading-6 text-zinc-900 outline-none"
            spellCheck={false}
            value={sourceDraft}
            onChange={(event) => {
              setSourceDraft(event.target.value);
              window.requestAnimationFrame(updateSelectionFromTextarea);
            }}
            onClick={updateSelectionFromTextarea}
            onKeyUp={updateSelectionFromTextarea}
            onSelect={updateSelectionFromTextarea}
          />
        </section>

        <div className="grid gap-4">
          <AssistantPanel
            cursorIndex={selectionRange.end}
            paperId={paper.id}
            selectedText={selectedText}
            selectionEnd={selectionRange.end}
            selectionStart={selectionRange.start}
            sourceDraft={sourceDraft}
            onInsert={insertAssistantText}
          />
          <PdfPreviewPanel
            compileError={compileError}
            isStartingCompile={isStartingCompile}
            job={compileJob}
            paper={{ ...paper, latex_source: sourceDraft }}
            onCompile={() => void handleCompile()}
          />
          <ReferencePanel paperId={paper.id} />
        </div>
      </div>
    </div>
  );
}
