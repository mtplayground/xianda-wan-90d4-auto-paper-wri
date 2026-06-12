export type Paper = {
  id: string;
  owner_id: string;
  title: string;
  latex_source: string;
  template_id: string | null;
  created_at: string;
  updated_at: string;
};

export type PaperCreatePayload = {
  title: string;
  latex_source: string;
  template_id?: string | null;
};

export type PaperUpdatePayload = {
  title?: string;
  latex_source?: string;
  template_id?: string | null;
};

export type Template = {
  id: string;
  owner_id: string | null;
  is_built_in: boolean;
  name: string;
  description: string | null;
  metadata: Record<string, unknown>;
  storage_key: string;
  created_at: string;
  updated_at: string;
};

export type CompilationJob = {
  id: string;
  owner_id: string;
  paper_id: string;
  status: "pending" | "running" | "succeeded" | "failed";
  pdf_storage_key: string | null;
  pdf_url: string | null;
  log_text: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  finished_at: string | null;
};

export type ReferenceItem = {
  id: string;
  owner_id: string;
  paper_id: string | null;
  title: string;
  authors: Array<Record<string, unknown>>;
  publication_year: number | null;
  venue: string | null;
  doi: string | null;
  url: string | null;
  source_type: string;
  source_identifier: string | null;
  source_url: string | null;
  abstract: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type ReferenceChunk = {
  id: string;
  reference_id: string;
  chunk_index: number;
  content: string;
  token_count: number | null;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type ReferenceUploadResponse = {
  reference: ReferenceItem;
  chunks: ReferenceChunk[];
  extracted_text_chars: number;
};

export type ReferenceSearchResult = {
  reference_id: string;
  reference_title: string;
  chunk_id: string;
  chunk_index: number;
  content: string;
  score: number;
  distance: number;
  metadata: Record<string, unknown>;
};

export type AiAssistantResponse = {
  text: string;
  model: string;
  stop_reason: string | null;
  input_tokens: number | null;
  output_tokens: number | null;
  reference_context: string;
  references: ReferenceSearchResult[];
};

export type PolishPaperPayload = {
  selected_text: string;
  surrounding_context?: string;
  instruction?: string;
  operation?: "polish" | "rewrite";
  reference_query?: string;
  reference_limit?: number;
};

export type ContinuePaperPayload = {
  draft_context: string;
  instruction?: string;
  target_length?: "short" | "medium" | "long";
  reference_query?: string;
  reference_limit?: number;
};

export type CitationSuggestionPayload = {
  passage: string;
  instruction?: string;
  reference_query?: string;
  reference_limit?: number;
  context_max_chars?: number;
};
