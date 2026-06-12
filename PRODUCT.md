# xianda-wan-90d4-auto-paper-wri

## What It Is

`xianda-wan-90d4-auto-paper-wri` is an authenticated academic paper workspace
for drafting LaTeX papers, managing references, getting AI writing assistance,
and compiling finished drafts to PDF.

## Current Capabilities

- Authenticated dashboard and editor UI built as a Vite React SPA.
- myClawTeam auth integration via the `mctai_session` cookie; the app does not
  implement Google OAuth directly and does not issue a second app JWT.
- Paper CRUD APIs and editor-side drafting workflows.
- Built-in LaTeX templates seeded by the backend, plus template upload support.
- PDF reference upload to private S3-compatible object storage, PDF text
  extraction, chunking, embedding, and per-paper reference management.
- Semantic search over reference chunks using pgvector.
- Claude-backed endpoints for polishing selected text, continuing drafts, and
  suggesting citations or reference summaries with retrieved reference context.
- Frontend assistant and reference panels for applying AI suggestions in the
  editor.
- Asynchronous LaTeX compilation jobs that run TeX Live and return presigned PDF
  download URLs.
- Consistent JSON API error responses for HTTP, validation, and unexpected
  server failures.
- API tests covering error responses and the core authenticated paper flow.

## Architecture

- Monorepo with `apps/api` for the FastAPI backend and `apps/web` for the React
  frontend.
- FastAPI serves `/api/*` routes and falls back to the built SPA from
  `apps/web/dist`.
- PostgreSQL is the only supported persistent database. Alembic migrations manage
  users, papers, templates, compilation jobs, references, and the pgvector
  extension.
- Object storage uses the S3-style environment variables from `.env.example`.
  Stored object keys are relative keys; the storage client prepends `S3_PREFIX`
  before S3 operations and generates presigned URLs for private reads.
- Claude configuration is environment-driven through Anthropic/Claude variables;
  prompt templates live in the backend.
- PDF compilation shells out to `TEXLIVE_COMMAND`, defaulting to `pdflatex`.

## Operational Conventions

- Run the API on `0.0.0.0:8080` by default.
- Use `npm run db:migrate` for database migrations.
- Use `npm run start:api` for production API startup.
- Use `npm run deploy:check` before deployment to verify required env vars,
  PostgreSQL URL shape, S3 prefix format, local tooling, and TeX Live presence.
- Deployment setup and TeX Live provisioning are documented in
  `docs/DEPLOYMENT.md`.
- Do not use SQLite, local JSON files, in-memory maps, or ephemeral volumes for
  persistent state.
