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

The Helm chart (`deploy/helm`) is self-contained: it stands up PostgreSQL (via the
CloudNativePG operator), RustFS (standalone), the backend, nginx pods that serve the
SPA/docs from RustFS, ingress, and runs DB migrations automatically as a post-install hook.

### Cluster prerequisites (install once, separately — not subcharts)

- **CloudNativePG operator** — provides the `postgresql.cnpg.io` `Cluster` CRD.
- **nginx ingress controller**.
- **cert-manager** + a `ClusterIssuer` — only when `ingress.tls.enabled` (default true).

### Steps

1. Run `uv sync` and commit `uv.lock` before building the Docker image.
2. Build and push the backend image (it now includes Alembic so the migration Job can run):
   ```bash
   docker build -t registry.example.com/recipie-management/backend:TAG apps/backend-api/
   docker push registry.example.com/recipie-management/backend:TAG
   ```
3. Deploy via Helm (chart-managed secrets — override the defaults!):
   ```bash
   helm upgrade --install recipie deploy/helm \
     --set backend.image.tag=TAG \
     --set ingress.apiHost=api.example.com \
     --set ingress.appHost=app.example.com \
     --set ingress.docsHost=docs.example.com \
     --set ingress.s3Host=s3.example.com \
     --set ingress.certManager.clusterIssuer=letsencrypt-prod \
     --set secrets.jwtSecret=... --set secrets.dbPassword=... \
     --set rustfs.rootUser=... --set rustfs.rootPassword=... \
     --set secrets.googleClientId=...
   ```
   The chart creates the CNPG `Cluster`, RustFS, and a backend Secret; post-install Jobs
   then run in order: create the buckets (`recipie`, `recipie-web`, `recipie-docs`),
   run `alembic upgrade head`, and import USDA FoodData Central into the
   `foods`/`food_portions` tables (`usdaImport.enabled`, default true — disable it once
   loaded to skip re-downloading the datasets on every upgrade). To bring your own
   credentials instead, set
   `secrets.create=false` and `secrets.existingSecret=<name>` (the Secret must contain
   `DATABASE_URL`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `JWT_SECRET_KEY`, `GOOGLE_CLIENT_ID`,
   `CORS_ORIGINS`).
4. Build and upload the React SPA to the RustFS `recipie-web` bucket.
5. Build and upload MkDocs to the RustFS `recipie-docs` bucket.

> The `recipie` bucket stays private (recipe images served via presigned URLs through
> `s3Host`); `recipie-web` and `recipie-docs` get a public-read policy so the nginx pods
> can serve them anonymously.

## Ingress hostnames

| Subdomain | Content |
|-----------|---------|
| `api.domain.com` | FastAPI backend |
| `app.domain.com` | React SPA (nginx → RustFS `recipie-web`) |
| `docs.domain.com` | MkDocs site (nginx → RustFS `recipie-docs`) |
| `s3.domain.com` | Public RustFS S3 endpoint (presigned image URLs) |

> Set the four `ingress.*Host` values to your real domains before deploying.
