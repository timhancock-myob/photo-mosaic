# 0001. Local-first deployment, hosted-ready seams

- **Status:** Accepted
- **Date:** 2026-11-17

## Context

The app can run on the user's own machine or as a hosted service. The choice decides how tile folders are read, where photos and OAuth tokens live, and whether user accounts are needed. The initial system description left this open.

## Decision

v1 is **local-first**: one user, running on their own machine. The backend reads a tile folder by path, photos never leave the machine, and there are no user accounts.

The code keeps **seams** so a hosted deployment later is additive, not a rewrite. Everything that would change for hosting sits behind an interface with a local implementation now:

| Seam | v1 (local) implementation | Hosted implementation later |
|---|---|---|
| Tile source (`source_gateway` provider) | `local_folder` reads a path | `upload` provider (browser upload) |
| Blob storage (`mosaic_api.storage`) | Local disk under `data/` | S3-compatible object storage |
| Metadata DB (`mosaic_api.db`) | SQLite | Postgres |
| Job runner (`mosaic_api.jobs`) | In-process pool | Queue + workers |
| Identity | Single implicit local user | Real auth; `owner_id` already on rows |
| Token storage (`source_gateway.tokens`) | Encrypted file | Secret store / KMS |

## Consequences

- The API binds to `127.0.0.1` by default. The local folder provider only reads under configured allowed roots.
- Data model rows carry an `owner_id` (always the local user in v1), so adding accounts doesn't need a schema migration of every table.
- No hosting, auth or upload work in v1. Google OAuth uses the installed-app (loopback) flow.
- Going hosted later means swapping implementations behind the seams above and adding auth, not restructuring packages.
