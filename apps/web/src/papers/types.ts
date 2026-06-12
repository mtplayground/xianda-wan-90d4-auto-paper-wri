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
