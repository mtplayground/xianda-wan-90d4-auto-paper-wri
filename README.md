# xianda-wan-90d4-auto-paper-wri

Monorepo scaffold with a React + Tailwind SPA and a FastAPI backend.

## Structure

```text
apps/
  api/    FastAPI backend served by uvicorn on port 8080
  web/    Vite React SPA styled with Tailwind CSS
```

## Development

Install JavaScript dependencies:

```bash
npm install
```

Install Python dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements-dev.txt
```

Run the API:

```bash
npm run dev:api
```

Run the web dev server:

```bash
npm run dev:web
```

Build both scaffolded apps:

```bash
npm run build
```

Run quality checks:

```bash
npm run typecheck
npm run lint
npm run format:check
```

Run database migrations:

```bash
export DATABASE_URL=$(cat /workspace/.database_url)
npm run db:migrate
```

The initial migration enables the PostgreSQL `vector` extension. The configured
database role must have permission to create extensions, or the extension must
already be installed by the database administrator.

Object storage uses the pre-provisioned S3-compatible environment variables:
`S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, `S3_BUCKET`, `S3_PREFIX`,
`S3_ENDPOINT`, `S3_REGION`, and `S3_FORCE_PATH_STYLE`. All object operations
prepend `S3_PREFIX` to relative keys before calling S3.
