# 0006. Task runner: poe tasks in pyproject.toml, no Makefile

- **Status:** Accepted
- **Date:** 2026-11-17
- **Amends:** [0005](0005-developer-setup-distribution.md) (setup commands only)

## Context

ADR 0005 named `make setup && make dev` as the entry point. The project already uses uv, which creates and syncs a virtual environment in `.venv/`. A Makefile adds a second tool (and a Windows gap) just to give commands short names.

## Decision

Developer tasks are [Poe the Poet](https://poethepoet.natn.io/) tasks under `[tool.poe.tasks]` in the root `pyproject.toml`, run through the uv-managed venv: **`uv run poe setup && uv run poe dev`**. Poe is a dev dependency, so `uv run` installs it on first use. There is no Makefile.

## Consequences

- Prerequisites shrink to uv, Node and pnpm; `make` is no longer needed.
- `uv run poe` lists every task with its help text. With the venv activated, `poe <task>` works directly.
- `poe dev` runs `scripts/dev.py`, which starts the API and Vite together and stops both on Ctrl-C. `MOSAIC_PORT` comes from the environment or `.env`.
- CI, `AGENTS.md`, the runbook and the PR template use the poe task names.
