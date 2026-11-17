# photo-mosaic

Build a photo mosaic from a base photo and a pool of tile photos (a local folder or Google Photos). Tiles are matched to each grid cell by colour, and neighbouring tiles are blended at their shared edges.

- Quick start: `uv run poe setup && uv run poe dev`, then open http://localhost:5173 ([`docs/runbook.md`](docs/runbook.md))
- Contributing (humans and agents): [`AGENTS.md`](AGENTS.md)
- Architecture: [`docs/architecture.md`](docs/architecture.md)
- Decisions: [`docs/decisions/`](docs/decisions/)
- Original brief and starting docs (frozen): [`initial-docs/`](initial-docs/)

Status: engine and CLI (`uv run poe mosaic BASE TILES_DIR OUT`); no app UI for mosaics yet.
