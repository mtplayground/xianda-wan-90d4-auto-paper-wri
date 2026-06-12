# Deployment

This app is a Vite React SPA served by a FastAPI backend. The backend serves the
built frontend from `apps/web/dist` and listens on `0.0.0.0:8080` by default.

## Runtime services

- PostgreSQL 16 or newer is required for all persistent state.
- The `vector` extension is required for reference embeddings. Install it before
  running migrations if the application role cannot create extensions.
- Object storage must be S3-compatible and private. The configured `S3_PREFIX`
  must be prepended to every object key by the application storage client.
- Authentication uses the myClawTeam auth service and the `mctai_session` cookie.
  Do not configure Google OAuth directly in this app.
- Claude/Anthropic credentials are required for AI polish, continuation, and
  citation endpoints.
- TeX Live is required on the API host for PDF compilation.

## Environment

Use `.env.example` as the source of truth for variable names. The app reads the
S3-style object storage variables:

```text
S3_ACCESS_KEY_ID
S3_SECRET_ACCESS_KEY
S3_BUCKET
S3_PREFIX
S3_ENDPOINT
S3_REGION
S3_FORCE_PATH_STYLE
```

`S3_PREFIX` must end with `/`. Store relative object keys in the database; the
backend signs private S3 reads when returning PDFs and reference files to the
browser.

Set `SELF_URL` to the public origin of the deployed app. Login redirects use it
as the `return_to` destination.

## Install

```bash
npm ci
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

For CI or development checks, install the dev requirements instead:

```bash
python3 -m pip install -r requirements-dev.txt
```

## TeX Live provisioning

The compile worker shells out to `TEXLIVE_COMMAND`, which defaults to `pdflatex`.
Install a TeX Live package set that includes at least:

- `pdflatex`
- common LaTeX classes and packages used by uploaded templates
- `latexmk` is optional; the current runner calls `pdflatex` directly

Debian/Ubuntu example:

```bash
apt-get update
apt-get install -y --no-install-recommends \
  texlive-latex-base \
  texlive-latex-recommended \
  texlive-latex-extra \
  texlive-fonts-recommended
```

If `pdflatex` is not the correct command path, set `TEXLIVE_COMMAND` to the full
path. Tune `TEXLIVE_TIMEOUT_SECONDS` and `TEXLIVE_MAX_RUNS` for larger templates.

## Build and migrate

```bash
npm run build
npm run db:migrate
```

If migration fails because the role cannot create `vector`, ask the database
administrator to run:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Then rerun `npm run db:migrate`.

## Preflight

Run the deployment preflight after exporting production env vars:

```bash
npm run deploy:check
```

The preflight checks required environment variables, PostgreSQL URL shape, S3
prefix format, and the presence of the TeX Live command.

## Start

```bash
npm run start:api
```

`scripts/start-api.sh` honors `HOST` and `PORT`, defaulting to `0.0.0.0` and
`8080`. The API serves `/api/*` routes and falls back to the built SPA for
frontend routes.
