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
