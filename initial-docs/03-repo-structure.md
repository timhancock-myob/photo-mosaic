# Suggested Repository Structure

2026-11-17

This document proposes the layout of the `photo-mosaic` repository. It follows the architecture in `system-description.md`: a pure Python core library, a FastAPI Mosaic API, a separate Source Gateway, and a React front end. It describes structure only, with no code.

## 1. Guiding principles

1. **One repo, several packages (a monorepo).** The pieces are developed together and versioned together. Splitting into repos would add friction with no benefit at this size.
2. **Dependencies point inward.** The core library depends on nothing web-related. The API depends on the core. The web app depends only on the API's published contract. Nothing depends on the web app.
3. **The API contract is a build artifact.** FastAPI generates an OpenAPI schema, and the React client is generated from it. The two sides cannot drift silently.
4. **Third-party code stays behind the gateway.** Nothing outside the Source Gateway knows Google exists.
5. **Everything runs with one command** locally, and CI runs the same commands.

## 2. Top-level layout

```
photo-mosaic/
├── README.md                  What it is, quick start, link to docs
├── CLAUDE.md                  Conventions for AI-assisted work (optional)
├── LICENSE
├── .gitignore
├── .editorconfig
├── Makefile                   Single entry point: setup, dev, test, lint, openapi, build
├── pyproject.toml             Python workspace root (uv workspace) and shared tool config
├── uv.lock
├── docker-compose.yml         Optional: API, gateway, web in one go
├── .env.example               All settings, no secrets
├── .github/
│   └── workflows/             ci.yml (lint, test, build), later release.yml
├── initial-docs/              Original brief, system description, this document
├── docs/                      Living documentation (see section 7)
├── packages/
│   ├── mosaic_core/           Pure Python library (the science)
│   ├── mosaic_api/            FastAPI Mosaic API
│   └── source_gateway/        FastAPI Source Gateway and providers
├── web/                       React + TypeScript front end
├── contracts/                 Generated OpenAPI schemas (committed)
├── scripts/                   Dev helpers (generate client, seed sample data)
├── notebooks/                 Experiments for tuning matching
├── samples/                   Small, licence-clean test images
└── data/                      Local cache and database (git-ignored)
```

## 3. `packages/mosaic_core` (the engine)

The most important package. No FastAPI, no HTTP, no database. It can be used from a notebook or a command line.

```
packages/mosaic_core/
├── pyproject.toml
├── README.md
├── src/mosaic_core/
│   ├── __init__.py            Public API only: what other packages may import
│   ├── imaging/               Decode, EXIF orientation, sRGB, thumbnails, cropping
│   ├── features/              Colour signatures (Lab centre, edges, corners)
│   ├── grid/                  Grid maths: cell sizes, base cropping, cell iteration
│   ├── matching/
│   │   ├── cost.py            Weighted Delta E cost matrix
│   │   ├── greedy.py          Reuse allowed, best tile per cell
│   │   ├── assignment.py      No-reuse and max-uses via Hungarian algorithm
│   │   └── alternatives.py    Ranked alternatives per cell
│   ├── render/                Preview data, full-resolution banded rendering, blending
│   ├── models.py              Plain dataclasses: Tile, Signature, Grid, Assignment, Options
│   └── cli.py                 Optional: build a mosaic from two folders, no server
└── tests/
    ├── unit/                  Synthetic images (solid colours, gradients)
    ├── golden/                Reference outputs for regression checks
    └── conftest.py
```

Notes:
- `matching/` is split by strategy so the extras (no-reuse, alternatives) are added as new files, not edits to the baseline.
- `models.py` holds pure data types shared with the API, which avoids duplicate definitions.
- Only names exported in `__init__.py` are public. Other packages must not import from sub-modules.

## 4. `packages/source_gateway` (third-party layer)

One interface, several providers. Runs as its own FastAPI app, or is mounted into the Mosaic API at first and split later.

```
packages/source_gateway/
├── pyproject.toml
├── src/source_gateway/
│   ├── app.py                 FastAPI app and routers
│   ├── interface.py           Provider contract: connect, list, metadata, fetch bytes, disconnect
│   ├── providers/
│   │   ├── local_folder.py    Reads a folder path (local-first mode)
│   │   ├── upload.py          Browser upload (hosted mode)
│   │   └── google_photos/
│   │       ├── oauth.py       OAuth flow and token handling
│   │       ├── picker.py      Sessions, polling, picked items
│   │       └── client.py      HTTP client (httpx), retries, quotas
│   ├── registry.py            Which providers are enabled
│   ├── tokens.py              Encrypted token storage
│   └── schemas.py             Pydantic request and response models
└── tests/
    ├── unit/
    └── fakes/                 In-memory fake provider and recorded Google responses
```

Notes:
- Adding another source (Dropbox, iCloud, S3) means adding one file under `providers/` and registering it.
- Google tests use recorded responses and fakes. Real Google calls are never made in CI.

## 5. `packages/mosaic_api` (application API)

Thin by design. It owns projects, jobs, persistence and HTTP. It calls the core for maths and the gateway for photos.

```
packages/mosaic_api/
├── pyproject.toml
├── src/mosaic_api/
│   ├── main.py                App factory, middleware, CORS, startup
│   ├── settings.py            Environment-driven configuration
│   ├── routers/               projects, sources, tilesets, jobs, mosaics, exports
│   ├── schemas/               Pydantic models (the public contract)
│   ├── services/              Use-case logic: index tiles, build mosaic, swap tile, export
│   ├── jobs/                  Runner, progress events (SSE), worker entry point
│   ├── db/
│   │   ├── models.py          SQLModel or SQLAlchemy tables
│   │   ├── session.py
│   │   └── migrations/        Alembic
│   ├── storage/               File cache for thumbnails, signatures, exports
│   └── clients/
│       └── gateway.py         Typed client for the Source Gateway
└── tests/
    ├── unit/
    ├── api/                   FastAPI TestClient tests per router
    └── integration/           API + core + fake gateway, end to end
```

Layering inside the package: `routers` call `services`; `services` call `mosaic_core`, `db`, `storage` and `clients`. Routers never touch the database or the core directly.

## 6. `web` (React front end)

```
web/
├── package.json
├── vite.config.ts
├── tsconfig.json
├── index.html
├── src/
│   ├── main.tsx
│   ├── app/                   Routing, providers, layout
│   ├── api/
│   │   ├── generated/         Client generated from contracts/ (git-ignored or committed, pick one)
│   │   └── hooks.ts           TanStack Query hooks wrapping the client
│   ├── features/
│   │   ├── base-photo/        Step 1: choose base photo
│   │   ├── tile-source/       Step 2: folder or Google Photos picker flow
│   │   ├── grid/              Step 3: grid size and live overlay
│   │   ├── mosaic-viewer/     Step 4: canvas viewer, pan and zoom
│   │   └── refine/            Extras: alternatives, swap, crop
│   ├── components/            Shared UI pieces (buttons, progress, dialogs)
│   ├── state/                 Small UI store (Zustand)
│   └── lib/                   Canvas helpers, formatting
├── public/
└── tests/
    ├── unit/                  Vitest and Testing Library
    └── e2e/                   Playwright, run against the API with fake sources
```

Organising by feature (one folder per wizard step) keeps each screen self-contained and matches the user flow.

## 7. Documentation layout

```
initial-docs/                  Frozen snapshot of the starting material
├── 01-original-brief.md
├── 02-system-description.md
└── 03-repo-structure.md       This document

docs/                          Living documentation, updated as the system changes
├── architecture.md            Current architecture (starts as the system description)
├── decisions/                 Architecture decision records, one short file each
│   └── 0001-local-first-deployment.md
├── api.md                     Pointer to contracts/ and how to regenerate
├── matching-algorithm.md      Signature design, weights, tuning notes
├── google-photos.md           Picker flow, quotas, OAuth setup
└── runbook.md                 How to run, configure, troubleshoot
```

`initial-docs/` is kept as a historical record and is not edited. Changes go into `docs/`, with significant choices recorded as decision records.

## 8. Contracts and generated code

- `contracts/mosaic-api.openapi.json` and `contracts/source-gateway.openapi.json` are exported from the running apps by a script and committed.
- CI regenerates them and fails if the committed copy is out of date. That makes any API change visible in the pull request.
- The TypeScript client in `web/src/api/generated/` is produced from these files.

## 9. Tooling and standards

| Concern | Choice |
|---|---|
| Python versions and workspace | Python 3.12+, `uv` workspace across the three packages |
| Python lint and format | Ruff |
| Python types | mypy or pyright, strict on `mosaic_core` |
| Python tests | pytest, with coverage |
| Web build | Vite, pnpm |
| Web lint, format, types | ESLint, Prettier, `tsc` |
| Web tests | Vitest, Playwright |
| Hooks | pre-commit (Ruff, Prettier, secret scan) |
| CI | GitHub Actions: Python job, web job, contract check |
| Dependency updates | Dependabot or Renovate |

`Makefile` targets (names only): `setup`, `dev`, `test`, `lint`, `openapi`, `client`, `build`, `clean`.

## 10. Git workflow

- `main` is always releasable. Work happens on short-lived branches and merges by pull request.
- Conventional commit messages (`feat:`, `fix:`, `docs:`) so a changelog can be generated later.
- A pull request template with a short checklist: tests added, contract regenerated, docs updated.
- `CODEOWNERS` can be added if more people join.

## 11. Git-ignored and local-only

`data/` (cache, SQLite database, exports), `.env`, `node_modules/`, Python virtual environments, build output, and any real photos. Only `samples/` images with a clear licence are committed.

## 12. Growth path

The layout is built so the likely changes are additions rather than rewrites:

- **Hosted deployment:** switch the database to Postgres, the file cache to object storage and the job runner to a queue with workers. Only `mosaic_api/db`, `storage` and `jobs` change.
- **Gateway split into its own service:** it already has its own app and client, so this is a deployment change.
- **New photo sources:** one new file under `providers/`.
- **Command-line or desktop use:** build on `mosaic_core` directly.
- **Extras (crop, swap, no-reuse):** new files under `matching/`, `render/` and `web/features/refine/`.

## 13. Suggested first commits

1. Repository scaffolding: README, licence, `.gitignore`, `Makefile`, CI skeleton, `initial-docs/`.
2. `mosaic_core` with grid and feature extraction, tested on synthetic images.
3. Baseline matching and rendering, with a small CLI.
4. `mosaic_api` skeleton with projects and jobs, and the first generated OpenAPI contract.
5. `web` skeleton with the wizard steps wired to the generated client.
6. `source_gateway` with the local folder provider.
7. Google Photos Picker provider.
8. Extras, in the order from the system description.

## 14. Open choices

1. **Package manager:** `uv` is proposed for Python. Poetry or plain pip are workable alternatives.
2. **Generated client committed or not:** committing it makes review easier; not committing it avoids noisy diffs. Either works if CI checks it.
3. **Gateway as a separate service from day one, or mounted in the API first:** mounting first is simpler; the package boundary keeps the later split cheap.
4. **Docker:** useful for hosted deployment, optional for local-first use.
