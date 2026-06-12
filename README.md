# xianda-wan-90d4-auto-paper-wri

LaTeX paper drafting app with templates, reference upload, AI assistance,
semantic retrieval, and PDF compilation.

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

Create local environment variables from the documented example:

```bash
cp .env.example .env
```

Use the provisioned secret values for real deployments; never commit `.env` or
`.env.production`.

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
npm run test:api
npm run typecheck
npm run lint
npm run format:check
```

Run database migrations against PostgreSQL:

```bash
export DATABASE_URL=$(cat /workspace/.database_url)
npm run db:migrate
```

The reference embedding schema requires the PostgreSQL `vector` extension. The
configured database role must have permission to create extensions, or the
extension must already be installed by the database administrator.

Object storage uses the pre-provisioned S3-compatible environment variables
documented in `.env.example`. All object operations prepend `S3_PREFIX` to
relative keys before calling S3.

The initial user schema stores one row per user in `users` and one row per
linked local or OAuth identity in `user_identities`.

Authentication helpers use Argon2 for password hashing and verify the
pre-provisioned `mctai_session` cookie against the myClawTeam JWKS endpoint.
The backend does not issue a second application JWT.

Auth routes under `/api/auth` redirect registration and login to myClawTeam
auth. `/api/auth/me` verifies the `mctai_session` cookie and upserts the user.
Provider OAuth routes under `/api/auth/oauth/{google|github}` delegate to
myClawTeam auth and link the verified session to `user_identities`.
Protected API routes should depend on `app.auth.dependencies.CurrentUser`,
which injects the verified user context and stores it on `request.state`.

## Deployment

Deployment setup, runtime environment, preflight checks, and TeX Live
provisioning are documented in [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

Common production commands:

```bash
npm ci
python3 -m pip install -r requirements.txt
npm run build
npm run deploy:check
npm run db:migrate
npm run start:api
```
