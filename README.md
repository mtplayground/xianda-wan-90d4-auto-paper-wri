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
python3 -m pip install -r requirements.txt
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
