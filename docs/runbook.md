# Runbook

## Prerequisites

- Python 3.12+ and [uv](https://docs.astral.sh/uv/getting-started/installation/) (`uv python install 3.12` if needed)
- Node 22 and pnpm (`corepack enable`)
- `git`

## First run

```sh
cp .env.example .env   # optional; defaults work
uv run poe setup
uv run poe dev
```

Open http://localhost:5173. The page shows `API: ok` when the API at http://127.0.0.1:8000 is reachable. API docs: http://127.0.0.1:8000/docs.

## Data

Local state lives in `data/` (git-ignored). Delete it to reset.

## Troubleshooting

- `API: unavailable`: check the `dev-api` output; port 8000 may be in use (set `MOSAIC_PORT` in `.env`; `poe dev` points the web proxy at it).
- `poe contracts-check` fails in CI: run `uv run poe client` and commit the changes.

Run `uv run poe` to list every task. `uv run` creates and syncs `.venv/`; activate it (`source .venv/bin/activate`) if you prefer to type `poe dev`.
