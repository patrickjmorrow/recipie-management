# Recipie Management — Dev Guide

## Prerequisites

- [uv](https://docs.astral.sh/uv/getting-started/installation/) — Python package manager
- Docker + Docker Compose
- Node.js 20+
- (Optional) `helm` for k8s work

## First-time setup

```bash
# Install Python deps and generate uv.lock (required before docker build)
cd apps/backend-api && uv sync

# Install frontend deps
cd apps/web-app && npm install

# Install MkDocs
pip install mkdocs-material
```

## Local development

### Start backing services (Postgres + RustFS)

```bash
docker compose -f deploy/docker-compose.yml up -d postgres rustfs rustfs-init
```

### Run database migrations

```bash
cd apps/backend-api
uv run alembic upgrade head
```

### Run the backend

```bash
cd apps/backend-api
uv run uvicorn app.main:app --reload
# API at http://localhost:8000
# Swagger UI at http://localhost:8000/docs
```

### Run the frontend

```bash
cd apps/web-app
npm run dev
# App at http://localhost:5173
# /api requests are proxied to the backend automatically
```

### Preview docs

```bash
cd docs
mkdocs serve
# Docs at http://localhost:8000 (mkdocs default)
```

### Run everything via Docker Compose (backend included)

```bash
docker compose -f deploy/docker-compose.yml up --build
```

> The frontend is **not** a compose service. Run `npm run dev` locally for Vite HMR.

## Alembic (migrations)

```bash
cd apps/backend-api

# Generate a new migration after changing models
uv run alembic revision --autogenerate -m "describe change"

# Apply migrations
uv run alembic upgrade head

# Roll back one step
uv run alembic downgrade -1
```

## Architecture

| Layer | Tech | Local | Production |
|-------|------|-------|------------|
| Backend API | FastAPI + asyncpg | `uvicorn --reload` | k8s Deployment via Helm |
| Database | PostgreSQL 16 | Docker Compose | External Postgres cluster |
| Blob storage | RustFS (S3-compatible) | RustFS (Docker Compose) | External RustFS cluster |
| Frontend SPA | Vite + React | `npm run dev` | Static files in RustFS bucket |
| Docs | MkDocs Material | `mkdocs serve` | Static files in RustFS docs bucket |
| Ingress | nginx | n/a | nginx ingress controller |

## Production deployment

1. Run `uv sync` and commit `uv.lock` before building the Docker image.
2. Build and push the backend image:
   ```bash
   docker build -t registry.example.com/recipie-management/backend:TAG apps/backend-api/
   docker push registry.example.com/recipie-management/backend:TAG
   ```
3. Build and upload the React SPA to the RustFS `recipie` bucket.
4. Build and upload MkDocs to the RustFS `recipie-docs` bucket.
5. Deploy via Helm:
   ```bash
   helm upgrade --install recipie deploy/helm \
     --set image.tag=TAG \
     --set existingSecret=recipie-secrets
   ```
6. Create the `recipie-secrets` k8s Secret with `DATABASE_URL`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`.

## Ingress hostnames

| Subdomain | Content |
|-----------|---------|
| `api.domain.com` | FastAPI backend |
| `app.domain.com` | React SPA (from RustFS) |
| `docs.domain.com` | MkDocs site (from RustFS) |

> Update `deploy/helm/values.yaml` with your actual domain names before deploying.
> The `app` and `docs` ingress rules in `templates/ingress.yaml` are placeholders —
> configure them to proxy to your RustFS bucket endpoints once the cluster is wired up.
