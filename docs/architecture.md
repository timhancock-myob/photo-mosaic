# Photo Mosaic: Architecture

Living document. Started from `initial-docs/02-system-description.md`, updated with the decisions in [`decisions/`](decisions/) and the fixes from the initial docs review. When this file and `initial-docs/` disagree, this file wins.

## 1. Purpose and scope

A **local-first** web app (ADR 0001) that builds a photo mosaic:

1. The user picks a **base photo**.
2. The user supplies a pool of **tile photos**: a local folder, or a selection from Google Photos.
3. The user sets a grid of **columns x rows** (ADR 0002).
4. The engine assigns a tile to every cell. Each tile must fit its cell's colour, and **neighbouring tiles must blend into each other at their shared edges** (ADR 0003).
5. The user views, refines and exports the result.

**Core:** steps 1–5 with a simple GUI, local folder source, free reuse (ADR 0004), and full-resolution export.

**Extras (designed for, built later):** crop and rescale tiles; swap a tile from ranked alternatives; reuse policies "even spread" and "no repeats"; colour blending; Google Photos source.

**Distribution:** developer setup only, `uv run poe setup && uv run poe dev` (ADR 0005, task runner per ADR 0006).

## 2. Architecture

| Layer | Package | Technology | Responsibility |
|---|---|---|---|
| Frontend | `web/` | React, TypeScript, Vite | Wizard UI, grid overlay, mosaic viewer, refine panel |
| Mosaic API | `packages/mosaic_api` | FastAPI | Projects, tile sets, jobs, mosaics, export. No image maths. |
| Core engine | `packages/mosaic_core` | NumPy, SciPy, scikit-image, Pillow | Decode, features, matching, rendering. No web or DB dependencies. |
| Source Gateway | `packages/source_gateway` | FastAPI router (mounted in the API for v1) | One provider interface over local folders and Google Photos |

```
React SPA ──REST (+ polling)──▶ Mosaic API ──calls──▶ mosaic_core
                                   │
                                   ├──calls──▶ source_gateway ──▶ local_folder
                                   │           (mounted router)  ──▶ google_photos (Picker API)
                                   │
                                   └──▶ jobs (in-process pool), SQLite, file cache (data/)
```

**v1 simplifications.** These keep v1 small; the package boundaries keep each one cheap to upgrade later.
- The gateway is mounted as a router in the API process, not a separate service.
- Job progress is polled (`GET /jobs/{id}`), not streamed with SSE.
- Tables are created at startup and Alembic waits until the schema settles.
- The generated TypeScript client stays: it is cheap and prevents the frontend and API drifting apart.

**Hosted-ready seams** (ADR 0001). Tile source, blob storage, metadata DB, job runner, identity and token storage each sit behind an interface with a local implementation.

**Gateway to engine data path.** Providers write original files into the shared file cache (`data/tiles/<tileset>/<content-hash>.<ext>`) and return metadata. The indexer reads from the cache. Bytes never travel over HTTP between our own components.

## 3. User flow

1. **Base**: upload a photo; show it with its dimensions.
2. **Tiles**: choose a source.
   - *Local folder*: type a path, or browse under the configured allowed roots (a browser can't hand over a filesystem path).
   - *Google Photos*: "Select photos in Google Photos" opens the Google picker. Max 2,000 items per selection.
   The UI shows import and indexing progress, then the number of usable tiles and the number skipped, with reasons.
3. **Grid**: set columns and rows. Rows are pre-filled for square cells. A live overlay on the base shows the grid. A readout shows "N cells / M tiles" and warns about extreme cell aspect ratios (ADR 0002).
4. **Generate**: progress bar, then the result in a zoomable viewer.
5. **Refine (extras)**: click a cell to see ranked alternatives, swap, crop, and re-optimise the neighbourhood.
6. **Export**: choose cell size in px and format; download.

## 4. Core engine (`mosaic_core`)

### 4.1 Decoding (shared by base and tiles)
- Apply EXIF orientation. Convert to sRGB using the embedded ICC profile (`PIL.ImageCms`); iPhone HEIC is Display P3.
- Formats: JPEG (draft-mode decode for speed), PNG, HEIC (`pillow-heif`).
- Keep Pillow's decompression-bomb guard (`MAX_IMAGE_PIXELS`) and enforce a file size limit.

### 4.2 Tile indexing
Runs once per tile set. Cached by content hash.
- Skip, and record a reason for: videos, unreadable or corrupt files, images below a minimum size.
- Store a **working thumbnail** (e.g. 128 px on the short side, uncropped) and a **display thumbnail** (e.g. 256 px).
- Compute a **perceptual hash** (e.g. dHash) to detect near-duplicates such as bursts and edited copies. Near-duplicates are collapsed by default.
- Signatures depend on the cell aspect ratio (ADR 0002), so they are computed per `(tile, aspect)` on first use and cached, not at index time.

### 4.3 Signatures
All in CIELAB.
- **Fit signature:** the tile, cropped to the cell aspect ratio, downsampled to a small `g x g` Lab grid (e.g. 4x4 to 8x8). This keeps structure, so a cell that is dark on one side and light on the other doesn't match a flat grey tile. It is a superset of the "centre plus edges" scheme in the initial docs.
- **Edge strips:** for each side (top, right, bottom, left), the mean Lab of `s` segments along a thin border strip. Used for the seam term.
- **Base cells:** the base is **resampled** to `(cols * g, rows * g)`, not cropped, and split into the same `g x g` grids.

### 4.4 Distance
- The colour difference is **CIE76** (Euclidean in Lab), so it vectorises with `scipy.spatial.distance.cdist` or plain NumPy. CIEDE2000 can be added later for the final ranking if tuning shows it helps.
- `fit(cell, tile)` is the mean CIE76 difference across the `g x g` grid points. It can be weighted, e.g. heavier at the border.

### 4.5 Matching (ADR 0003)
Objective:

```
total_cost(A) = Σ fit(cell, A[cell])
              + λ_seam * Σ_adjacent seam(A[c1], A[c2], side)
              + λ_self * Σ_adjacent [A[c1] == A[c2]]
```

1. **Candidates:** compute the `cells x tiles` fit matrix (100x100 cells x 2,000 tiles is 20M float32 values, about 80 MB). Keep the top-K tiles per cell.
2. **Initialise:** each cell takes its best-fit tile.
3. **Improve:** iterated conditional modes over the grid. For each cell, pick the candidate that minimises fit plus seams with its current neighbours. Repeat until there is no improvement or the iteration cap is hit. Simulated annealing is an option if needed.
4. **Report:** mean fit ΔE, mean seam ΔE, and number of distinct tiles used.

Matching is located in `mosaic_core/matching/`, split by strategy (`candidates.py`, `local_search.py`, `policies.py`).

### 4.6 Reuse policies (ADR 0004)
- **Free (default):** no cap. `λ_self` discourages adjacent repeats.
- **Even spread (extra):** at most `ceil(cells / tiles)` uses per tile, plus a minimum spacing between repeats, enforced inside local search.
- **No repeats (extra):** at most one use per tile; requires `tiles >= cells`. Initialise with the Hungarian algorithm on the fit matrix (`scipy.optimize.linear_sum_assignment`), then improve seams with swap-only local search. That keeps the constraint while optimising seams. Above about 5,000 cells the Hungarian initialisation is replaced by a greedy one, to bound memory and time.

### 4.7 Alternatives and swaps (extra)
- Alternatives for a cell are ranked by `fit + seams with current neighbours`. They are recomputed on request from cached signatures; the full cost matrix is not stored.
- A swap sets `user_override` on that cell. "Re-optimise neighbourhood" runs local search on the surrounding cells, with overridden cells pinned.

### 4.8 Crop and rescale (extra)
Each assignment stores a crop window `(x, y, scale)` on the tile; the default is centre crop. Smart crop (face or saliency detection) is a later extra.

### 4.9 Colour blending (extra)
An optional "fidelity" slider blends each tile toward its cell colour, 0–30%. Off by default.

### 4.10 Rendering
- The export is composed from **original-resolution** tiles held in the cache, never from thumbnails.
- The output size is `cols * cell_px` by `rows * cell_px`. It is rendered in row bands to bound memory.
- Formats: JPEG (max 65,535 px per side) or PNG. Output pixels are capped by a setting.

## 5. Source Gateway (`source_gateway`)

Provider interface: `connect`, `list_items`, `fetch_to_cache(item) -> CachedFile`, `disconnect`.

### 5.1 Local folder (v1)
- Reads only under `ALLOWED_ROOTS`, which defaults to the user's home Pictures folder and is configurable.
- Rejects path traversal and symlinks that escape a root.
- Copies or hard-links originals into the cache, so the source folder changing later doesn't break a mosaic.

### 5.2 Google Photos (Phase 3)
Uses the **Picker API**. Read access to a user's library through the Library API ended on 31 March 2025.
- **Flow:**
  1. OAuth with scope `photospicker.mediaitems.readonly`, using the installed-app loopback flow.
  2. `sessions.create` returns a `pickerUri`. Set `pickingConfig.maxItemCount` (max 2,000).
  3. The user picks photos in Google's UI.
  4. Poll `sessions.get` until `mediaItemsSet`.
  5. Page through `mediaItems.list`.
- **Download everything at import time, at full resolution.** Access to picked items ends at the session's `expireTime`. Each `baseUrl` lasts 60 minutes and needs an OAuth bearer token on every request. Nothing can be re-fetched later, so originals must be in the cache before the session expires, or the full-resolution export breaks.
- Delete the session after import. Revoke tokens on disconnect. Tokens are stored encrypted (`source_gateway.tokens`).
- **Setup:** a Google Cloud project owned by the maintainer, an OAuth client of type "Desktop app", and test users while the app is in testing mode. Verification is only needed for a wider or hosted launch.

## 6. Mosaic API (`mosaic_api`)

REST with Pydantic models. The OpenAPI schema is committed to `contracts/`, and the TypeScript client is generated from it.

| Area | Endpoints (illustrative) |
|---|---|
| Projects | `POST /projects`, `GET /projects/{id}` |
| Base | `PUT /projects/{id}/base`, `GET /projects/{id}/base` |
| Sources | `GET /sources/providers`, `POST /sources/local/browse`, `POST /sources/google/sessions`, `GET /sources/google/sessions/{sid}` |
| Tile sets | `POST /tilesets` (from a source, returns job), `GET /tilesets/{id}`, `GET /tilesets/{id}/skipped`, `GET /tiles/{tid}/thumb` |
| Jobs | `GET /jobs/{id}` (status, progress, error), `POST /jobs/{id}/cancel` |
| Mosaics | `POST /projects/{id}/mosaics` (tile set, grid, options; returns job), `GET /mosaics/{id}` (assignment grid as JSON) |
| Refine | `GET /mosaics/{id}/cells/{r}/{c}/alternatives`, `PATCH /mosaics/{id}/cells/{r}/{c}`, `POST /mosaics/{id}/reoptimise` |
| Export | `POST /mosaics/{id}/exports` (cell px, format; returns job), `GET /exports/{id}` |

The API returns the **assignment grid as data**. The browser composes the preview from display thumbnails, and loads higher-resolution tile images on demand when zoomed past thumbnail resolution. The server renders only the export.

## 7. Jobs

- Indexing, matching and export run as background jobs in an in-process pool. Each job has persisted status and progress, and supports cancellation.
- On restart, jobs that were running are marked `interrupted`; the user can retry them.
- Hosted later: a queue (arq or Celery) with separate workers, behind the same `jobs` interface.

## 8. Data model

All rows carry `owner_id`, which is the single local user in v1 (ADR 0001).

- **Project**: id, owner_id, base_image_path, base_width, base_height, created_at.
- **TileSource**: id, owner_id, provider (`local_folder` | `google_photos`), display_name, config (path or session id), auth_ref.
- **TileSet**: id, owner_id, source_id, status, tile_count, skipped_count, created_at.
- **Tile**: id, tileset_id, external_id, content_hash, phash, width, height, original_path, thumb_path, skip_reason (nullable).
- **Mosaic**: id, project_id, tileset_id, cols, rows, options (λ_seam, λ_self, reuse policy, blend), status, mean_fit_de, mean_seam_de, distinct_tiles.
- **Assignment**: mosaic_id, row, col, tile_id, crop (x, y, scale), fit_cost, user_override.
- **Job**: id, kind (`index` | `match` | `export`), target_id, status, progress, error, created_at, finished_at.
- **Export**: id, mosaic_id, cell_px, format, path, width, height.

Metadata lives in SQLite (SQLModel); images and arrays live in the file cache under `data/`.

## 9. Frontend (`web/`)

- Vite, React, TypeScript. TanStack Query for server state; local component state until a store is needed.
- Wizard steps: Base, Tiles, Grid, Generate, Result (Refine and Export happen in the Result step).
- The grid overlay is drawn on a canvas over the base.
- Result viewer: a canvas with pan and zoom, composed from thumbnails. Clicking a cell opens the refine panel.
- Keyboard-operable controls; designed for a laptop screen.

## 10. Security and privacy (local-first)

- The API binds to `127.0.0.1`. CORS allows only the dev server origin.
- Folder access is limited to the allowed roots (5.1). Uploads are size-limited and decoded with the bomb guard on (4.1).
- Photos and tokens stay on the machine under `data/`. A "Delete tile set" action removes cached originals and thumbnails.
- Secrets live in `.env` (git-ignored). `.env.example` lists every setting.

## 11. Testing and quality

- **Unit tests:** synthetic images (solid colours, gradients, split cells) for decode, signatures, fit, seam and local search.
- **Golden tests:** a small committed set of licence-clean images, with reference outputs and a tolerance on mean ΔE.
- **Tuning set:** a few hundred real, licence-clean photos fetched by `scripts/fetch-sample-tiles`, not committed. *(Source to be confirmed.)*
- **API tests:** FastAPI `TestClient` with the fake provider.
- **E2E tests:** Playwright against the API with the fake provider.
- **Google:** recorded responses only; CI never calls Google.

Initial targets, to be confirmed after the engine spike:

| Metric | Target |
|---|---|
| Index 500 tiles (JPEG, about 12 MP) | < 60 s |
| Match 50x50 with 500 tiles | < 10 s |
| Export 50x50 at 100 px per cell | < 30 s |
| Default export cap | 200 MP |

## 12. Build phases

1. **Foundation:** repo scaffold, CI, pre-commit, `AGENTS.md`.
2. **Engine:** decode, index, signatures, matching (fit + seams), render. Notebook for tuning `λ` values by eye. CLI that builds a mosaic from two folders.
3. **MVP app:** API and wizard UI, local folder source, free reuse, export.
4. **Google Photos:** Picker provider.
5. **Extras:** alternatives and swap, reuse policies, crop, blending.

## 13. Open questions

1. Source for the licence-clean tuning photo set.
2. Confirm the performance targets in §11 after the engine spike.
3. Default `λ_seam` and `λ_self`, and whether simulated annealing is needed beyond iterated conditional modes. Settle by tuning.
