# AGENTS.md

Guidance for anyone (human or AI) working in this repo. Read `docs/architecture.md` and `docs/decisions/` before changing behaviour.

## Commands

| Task | Command |
| --- | --- |
| Install everything + git hooks | `make setup` |
| Run API (:8000) + web (:5173) | `make dev` |
| Tests | `make test` |
| Lint + format check | `make lint` |
| Type check | `make typecheck` |
| Regenerate OpenAPI + TS client | `make client` |
| Check contracts are committed | `make contracts-check` |

Requires Python 3.12+ with [uv](https://docs.astral.sh/uv/) and Node 22 with pnpm (`corepack enable`).

## Layout

- `packages/mosaic_core` – pure engine (NumPy/SciPy/scikit-image/Pillow). No FastAPI, DB, HTTP or filesystem-walking code. Strict mypy.
- `packages/source_gateway` – tile-source providers (local folder, later Google Photos) behind one provider interface; exposes a FastAPI router.
- `packages/mosaic_api` – FastAPI app; mounts the gateway router. Layering: routers → services → (core | db | storage | clients). Routers never touch core directly.
- `web/` – React + TypeScript + Vite. Talks to the API only through the generated types in `web/src/api/generated/` via `web/src/api/client.ts`; the dev server proxies `/api` to the API.
- `contracts/` – generated OpenAPI schema. Never hand-edit.
- `docs/decisions/` – ADRs. `initial-docs/` is frozen.

## Rules

- Other packages import only names exported from a package's `__init__.py`.
- Local-first, hosted-ready (ADR 0001): access photos, blobs, DB, jobs and tokens through interfaces; every row carries `owner_id`.
- API binds to `127.0.0.1`. Folder reads must stay inside allowed roots (no `..` or symlink escapes).
- Never commit real photos, `data/`, `.env` or credentials. Google Photos is tested with fakes/recorded responses.
- Python: Ruff (line length 100), type hints everywhere. TypeScript: strict, ESLint + Prettier.

## Definition of done

1. Tests added/updated; `make lint typecheck test` passes.
2. If the API changed: `make client` and commit `contracts/` and `web/src/api/generated/` (CI runs `make contracts-check`).
3. `docs/architecture.md` updated if behaviour changed; new ADR for significant decisions.
4. Pre-commit hooks pass (`uv run pre-commit run --all-files`).
