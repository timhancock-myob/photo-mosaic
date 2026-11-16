# Photo Mosaic Application: System Description

2026-11-17

## 1. Purpose and scope

A web application that builds a photo mosaic. The user picks a **base photo**, supplies a pool of **tile photos** (a private folder or Google Photos), chooses a **grid size** (e.g. 20x20, 50x50), and the system replaces each grid cell of the base with the tile photo whose colour profile fits best, especially around the cell edges.

This document describes the system only. It contains no code.

**Core (must have)**
1. Pick a base photo.
2. Connect a tile source (private folder or Google Photos) holding hundreds of photos.
3. Overlay a consistent grid on the base.
4. Match each cell to the best tile by colour profile, weighted toward the edges.
5. Simple GUI.

**Optional extras (designed for, built later)**
1. Rescale / crop tiles.
2. Swap a tile and see suggested alternatives.
3. No tile used twice.

## 2. Architecture overview

Four layers, each separable and independently testable.

| Layer | Technology | Responsibility |
|---|---|---|
| Frontend | React + TypeScript (Vite) | Wizard UI, grid preview, mosaic viewer, tile swapping |
| Mosaic API | FastAPI | Projects, jobs, mosaic results, image serving. No image maths. |
| Core engine | Pure Python library (NumPy, SciPy, scikit-image, Pillow) | Feature extraction, matching, assignment, rendering. No web dependencies. |
| Source Gateway | FastAPI (own router or own service) | One interface over third-party and local photo sources |

Supporting pieces: a job runner for long tasks, SQLite for metadata (Postgres later), and a file cache for thumbnails and features.

The Core engine is a plain importable package. The API calls it; so could a CLI or a notebook. That keeps the science testable without a server and lets the API layer be swapped or scaled without touching the maths.

```
React SPA  <--REST + SSE-->  Mosaic API  --calls-->  mosaic_core (library)
                                  |
                                  +--calls-->  Source Gateway  -->  Local folder
                                  |                            -->  Google Photos Picker API
                                  +--> Job runner, SQLite, file cache
```

## 3. User flow

1. **Base**: upload a photo. The UI shows it with its dimensions.
2. **Tiles**: choose a source (Local folder or Google Photos). The UI shows import and indexing progress, then a count of usable tiles.
3. **Grid**: a slider or presets set columns (e.g. 20, 50, 100). Rows are derived from the base aspect ratio so cells stay square. A live grid overlay on the base shows the grain. A readout shows *cells vs tiles available* and warns if the no-reuse option cannot be satisfied.
4. **Generate**: a progress bar, then the mosaic appears in a zoomable viewer.
5. **Refine (extras)**: click a cell to see alternatives, swap, crop, re-export.
6. **Export**: download a full-resolution image.

## 4. Core engine

### 4.1 Tile preparation (indexing)
Run once per tile source, cached by tile id and content hash.

- Decode, apply EXIF orientation, convert to sRGB. Support JPEG, PNG and HEIC (via pillow-heif). Use JPEG draft-mode decoding for speed.
- Centre-crop to the cell aspect ratio (square by default) and store a small working thumbnail (e.g. 64x64) plus a display thumbnail (e.g. 256 px).
- Compute a **colour signature** in CIELAB (perceptually uniform, so distances mean something):
  - mean Lab of the centre region
  - mean Lab of four edge strips (top, right, bottom, left)
  - optionally four corner patches
- Store the signature as a small float vector (about 15 to 27 dimensions) in a NumPy array on disk.

### 4.2 Base preparation
- Crop the base so its pixel size is an exact multiple of the grid (no ragged edge cells).
- Split into cells and compute the same signature for each cell using the same regions.

### 4.3 Matching
- Distance between a cell and a tile is a **weighted sum of colour differences (Delta E)** across regions. Edge regions get a higher weight than the centre, which implements "especially around the edges". Weights are configurable.
- Compute a full cost matrix (cells x tiles) with vectorised NumPy or SciPy `cdist`. Even 100x100 cells against 2,000 tiles is about 20 million entries, which is trivial. A KD-tree is unnecessary at this scale.
- Baseline mode: each cell takes its lowest-cost tile (reuse allowed).

### 4.4 No-reuse mode (extra)
A hard constraint changes the problem into an **assignment problem**, solved optimally with the Hungarian algorithm (`scipy.optimize.linear_sum_assignment`) on the cost matrix.

Important constraint: unique tiles need **tiles >= cells**. With a few hundred tiles, a 20x20 grid (400 cells) may work, but 50x50 (2,500 cells) cannot. The system therefore supports a **maximum-uses-per-tile** setting: replicate each tile column k times (k = ceil(cells / tiles)) before solving. Values of 1 give true uniqueness; larger values give fair reuse. A softer alternative is a reuse penalty plus a minimum distance between repeats of the same tile, to avoid visible clustering.

### 4.5 Alternatives and swaps (extra)
The cost matrix already holds the ranking for every cell, so "top N alternatives for this cell" is a sort of one row. In no-reuse mode, alternatives that are already placed are flagged, and swapping offers either a pairwise exchange or a re-solve of the remainder.

### 4.6 Crop and rescale (extra)
Each assignment stores a crop window (x, y, scale) on the tile. Defaults are centre crop. Optionally, evaluate several candidate crop windows per tile during matching, which improves fit at modest cost. Smart cropping using face or saliency detection (OpenCV) avoids cutting off heads in people photos.

### 4.7 Optional colour blending
Mosaics commonly blend each tile slightly toward its cell colour (a tint of 0 to 30 percent) to improve resemblance at coarse grids. Expose as a "mosaic fidelity" slider. Off by default, so tiles stay true to the originals.

### 4.8 Rendering
Full-resolution output is composed from original-resolution tiles, not from thumbnails, so the export is crisp. Output dimensions are chosen by the user (e.g. cell size in pixels). Memory is handled by rendering in row bands for very large outputs.

## 5. Source Gateway (third-party layer)

A small API with one interface and several providers, so the Mosaic API never knows where photos came from.

Provider interface (conceptual): authenticate or register, enumerate items, return item metadata (id, filename, size, timestamp), return bytes at a requested size, release resources.

### 5.1 Local / private folder
The browser cannot hand a server a filesystem path in a hosted deployment. Two options:

- **Local-first deployment (recommended for v1):** the user runs the app on their own machine. The backend reads a folder path directly, which is fastest and keeps photos private.
- **Hosted deployment:** the browser uploads the folder (via a directory input or the File System Access API) and the backend stores it temporarily with a clear deletion policy.

### 5.2 Google Photos
This is the most constrained part of the system and shapes the design.

- Google changed its Photos APIs effective **31 March 2025**. The Library API read scopes (`photoslibrary.readonly`, `photoslibrary.sharing`, `photoslibrary`) were removed, and the Library API now only reaches photos and videos **created by your own app**. Calls depending on the removed scopes return `403 PERMISSION_DENIED`.
- The replacement for reading a user's own library is the **Google Photos Picker API** (`photospicker.googleapis.com`). The user selects items in a Google-hosted picker (individual items, whole albums, or a search of their library). The app cannot silently enumerate the library.
- Flow: OAuth 2.0 with scope `photospicker.mediaitems.readonly`, then create a session (returns a `pickerUri`), send the user to that URI, poll the session until media items are set, then list picked items. Each item has a `baseUrl` from which bytes are fetched, with size parameters such as `=w2048-h1024`.
- Picked item ids are described as persistent across sessions, but `baseUrl` links should be treated as short-lived: download and cache promptly. Quotas and exact expiry should be confirmed in the current docs before build.

Product implication: "connect to Google Photos" really means "pick an album or selection of a few hundred photos". The UI should say so and use a clear "Select photos in Google Photos" step, with the app importing the selection into its own cache.

Gateway responsibilities for Google: OAuth callback handling, encrypted token storage, session creation and polling, download-and-cache of picked items, and token revocation on disconnect.

## 6. Mosaic API (FastAPI)

REST plus server-sent events for job progress. Pydantic models give a typed OpenAPI schema, from which a TypeScript client is generated for React.

| Area | Endpoints (illustrative) |
|---|---|
| Projects | `POST /projects`, `GET /projects/{id}` |
| Base image | `PUT /projects/{id}/base` (upload), `GET /projects/{id}/base` |
| Sources | `GET /sources/providers`, `POST /sources/local`, `POST /sources/google/sessions`, `GET /sources/google/sessions/{sid}` |
| Tile sets | `POST /tilesets/{id}/index` (job), `GET /tilesets/{id}`, `GET /tiles/{tid}/thumb` |
| Jobs | `GET /jobs/{id}`, `GET /jobs/{id}/events` (SSE progress) |
| Mosaics | `POST /projects/{id}/mosaics` (grid and options, returns job), `GET /mosaics/{id}` (cell to tile assignment as JSON) |
| Refine | `GET /mosaics/{id}/cells/{r}/{c}/alternatives`, `PATCH /mosaics/{id}/cells/{r}/{c}` (tile and crop) |
| Export | `POST /mosaics/{id}/export` (job), `GET /exports/{id}` |

Design choice: the API returns the **assignment grid as data** (cell to tile id, crop, score), not a finished image. The browser composes the preview from cached tile thumbnails, so swaps and crops appear instantly with no server round trip. The server only renders the full-resolution export.

## 7. Jobs and performance

- Indexing hundreds of photos and rendering exports are slow, so they run as background jobs reporting progress.
- v1: a process pool inside the API process. Later: a queue (arq or Celery with Redis) and separate workers, with no change to the Core engine.
- Matching itself is fast (vectorised); decoding images dominates. Cache everything by content hash so re-runs with a different grid reuse tile features. Signatures for edge-weight changes can be recomputed from stored thumbnails.

## 8. Data model (conceptual)

- **Project**: id, base image reference, created time.
- **TileSource**: id, provider type, display name, auth reference.
- **Tile**: id, source id, external id, content hash, width, height, thumbnail path, signature vector path.
- **Mosaic**: id, project id, grid (columns, rows), matching options (edge weight, reuse limit, blend), status, summary score.
- **Assignment**: mosaic id, row, column, tile id, crop window, match score, `user_override` flag.

Metadata in SQLite (SQLAlchemy or SQLModel). Images and arrays in a file cache. Migration to Postgres plus object storage is a configuration change.

## 9. Frontend (React)

- Vite, React and TypeScript. TanStack Query for server state, a small store (Zustand) for UI state.
- Four-step wizard: Base, Tiles, Grid, Result.
- Grid step: HTML canvas or SVG overlay on the base, updating live as the slider moves.
- Result step: canvas viewer with pan and zoom (OpenSeadragon, or custom canvas for full control), hover shows the cell, click opens a side panel with alternatives, crop controls and a swap button.
- Generated API client from OpenAPI keeps the frontend and API in sync.
- Accessibility and responsiveness basics: keyboard-operable controls, readable on a laptop; mobile is secondary.

## 10. Technology summary

| Concern | Choice |
|---|---|
| Language | Python 3.12+ |
| Numerics | NumPy, SciPy (`cdist`, `linear_sum_assignment`) |
| Colour | scikit-image (Lab conversion, Delta E) |
| Imaging | Pillow, pillow-heif; OpenCV only if smart crop is added |
| API | FastAPI, Pydantic, httpx, SSE |
| Google auth | google-auth, Authlib or google-auth-oauthlib |
| Storage | SQLite then Postgres; local disk then S3-compatible |
| Frontend | React, TypeScript, Vite, TanStack Query |
| Testing | pytest with synthetic images (solid colours, gradients) and golden-image tests; Playwright for the UI |

## 11. Build phases

1. **Engine first:** Core library plus a notebook. Index a folder, match, render. Tune weights and signature design by eye. Metric: mean Delta E per cell.
2. **MVP app:** FastAPI plus React wizard, local folder, reuse allowed, export.
3. **Google Photos:** Picker flow in the Source Gateway.
4. **Extras:** alternatives and swap, then no-reuse (Hungarian), then crop and rescale.

## 12. Risks and open questions

1. **Deployment model:** local app or hosted service? This decides how folders are read, how privacy is handled and how much auth is needed. Recommendation: local-first for v1.
2. **Tiles vs cells:** with hundreds of tiles, fine grids need reuse. Decide the default policy (limit uses, penalty, spacing).
3. **Google Photos UX:** the picker model means selection, not silent library access. Confirm this is acceptable.
4. **Visual quality:** centre-cropping can cut faces. Smart crop is an extra but may matter sooner than expected.
5. **Privacy:** tile photos are personal. Define what is stored, for how long, and a clear delete option. Encrypt stored OAuth tokens.
6. **Large outputs:** very big exports need banded rendering and a size cap.
7. **Google API details:** confirm current quotas, `baseUrl` lifetime and OAuth verification requirements for the Picker scope before committing to a hosted launch.

## Sources

- [Updates to the Google Photos APIs](https://developers.google.com/photos/support/updates)
- [Get started with the Picker API](https://developers.google.com/photos/picker/guides/get-started-picker)
- [Picker API REST reference](https://developers.google.com/photos/picker/reference/rest)
- [Google Photos authorization scopes](https://developers.google.com/photos/overview/authorization)
