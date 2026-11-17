# 0005. Distribution: developer setup only for v1

- **Status:** Accepted; commands amended by [0006](0006-poe-task-runner.md)
- **Date:** 2026-11-17

## Context

Local-first (ADR 0001) means the user runs the app themselves. Options ranged from a developer setup to a one-command Python install, a Docker image, or a desktop installer.

## Decision

v1 is run from a clone with **`make setup && make dev`**. This requires Python 3.12+ with `uv`, and Node with `pnpm`. There is no packaged distribution yet.

## Consequences

- `README.md` and `docs/runbook.md` document the prerequisites and the two commands. `make dev` starts the API and the Vite dev server together.
- Nothing prevents packaging later. The React build can be served by FastAPI as static files, giving a single `uvx`-installable process or a Docker image. That is a new ADR when needed.
- End users who aren't developers can't run v1. Acceptable for now.
