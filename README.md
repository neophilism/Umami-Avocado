# Umami Avocado

A general-purpose platform for AI-directed scientific research using real laboratories. The first targets are savory food-yeast biomass (M1), yeast extract (M2), and eventually avocado cultivation (A1).

> **Foundation only.** This repository contains software scaffolding, not functional physical-lab integrations. Live lab orders are disabled, no biological experiments have occurred, and no food ingredient has been approved for human consumption.

## Requirements

- Node.js 22, pnpm 9 (via Corepack)
- Python 3.12–3.13, uv
- Docker with Compose plugin (for PostgreSQL and MinIO locally)

## Local development

```sh
corepack enable
corepack pnpm install --no-frozen-lockfile
corepack pnpm dev
# In another terminal
uv run --project services/api uvicorn umami_api.main:app --app-dir services/api --host 127.0.0.1 --port 8000
# In another terminal: inert worker
PYTHONPATH=services/worker uv run --project services/api python -m umami_worker.main
# Local infrastructure
# docker compose -f infra/compose/docker-compose.yml up -d
```

The PostgreSQL/MinIO services are provisioned by Compose but are **not yet wired into the application** (database integration: UA-003; artifact storage: UA-015). Never use these development credentials outside a local machine.

## Quality gates

```sh
node scripts/validate-pr-registry.mjs
corepack pnpm -r typecheck
corepack pnpm -r test
corepack pnpm -r lint
corepack pnpm -r build
uv run --project services/api pytest services/api/tests services/worker/tests
uv run --project services/api ruff check services
```

## Roadmap and boundaries

The single canonical source is [registry/prs.json](registry/prs.json), comprising 30 work units. Read [docs/DEVELOPMENT_PLAN.md](docs/DEVELOPMENT_PLAN.md), [AGENTS.md](AGENTS.md) and [docs/SECURITY.md](docs/SECURITY.md). UI design reference and detailed PR specifications are in the previous architecture package. Vendor APIs and science outcomes are never presumed implemented.
