# FPL Cartel Personalized API

A separate FastAPI project wrapping the existing Python squad and optimizer rules. No hosting was provisioned or deployed.

## Requirements
Python 3.12 is the tested runtime. Install a normal Python environment with the packages in requirements.txt. Streamlit, openpyxl, Excel and the projection generator are not runtime dependencies.

## Install
From this directory:
```sh
python -m venv .venv
```
Activate the environment (.venv\Scripts\Activate.ps1 on Windows; source .venv/bin/activate on Linux/macOS), then:
```sh
python -m pip install -r requirements-dev.txt
```

## Run locally
```sh
uvicorn app.main:app --reload
```
Open http://127.0.0.1:8000/health and http://127.0.0.1:8000/docs.
On this Windows workspace, .venv is already installed:
```powershell
.\Start-Api.ps1
```
Keep it running. Use -Reload for development auto-reload. No reload in hosting.

## Configuration
Copy .env.example to ignored .env if desired, or use environment variables. No real secret is needed or provided.

| Variable | Default / purpose |
|---|---|
| PROJECTIONS_PATH | data/projections.json, relative to this API directory, or a server-side absolute path |
| ALLOWED_ORIGINS | Exact comma-separated localhost:5173 and 127.0.0.1:5173 HTTP origins |
| FPL_BASE_URL | Official FPL /api/ origin; server operator config only |
| FPL_METADATA_TTL | 300 seconds |
| FPL_MANAGER_TTL | 60 seconds |
| FPL_TIMEOUT_SECONDS | 10 seconds |
| MAX_REQUEST_BYTES | 16,384 bytes (bounded at configuration time) |
| MAX_OPTIMIZER_CONCURRENCY | 1 per worker; excess work returns 503 with Retry-After |

This workspace's ignored .env points at ../fpl-cartel-web/public/data/projections.json, so the existing model/web refresh also updates API input. A portable copy of the same export is included in data/projections.json for an independent API installation. Neither path comes from an HTTP request.
For later hosting set an exact HTTPS frontend origin in ALLOWED_ORIGINS. Wildcard origins are rejected; credentials are disabled. CORS is not authentication.

## Endpoints
- GET /health — liveness, exactly {"status":"ok"}. This does not claim projection readiness.
- GET /team/{team_id} — 15 permanent squad players, bank, source GW, Free Hit restoration metadata and ID match diagnostics.
- POST /optimize/team-sheet — fixed permanent squad, independently optimized requested gameweeks.
- POST /optimize/transfers — original squad, bank, up to ten options, gross/net transfer gain and updated squad IDs.
- POST /optimize/transfers/preview — revalidate a chosen batch and produce the existing Team Sheet pitch data, original/updated XI totals and net XI gain.
- GET /docs and /openapi.json — generated Swagger/OpenAPI documentation.

Team Sheet request:
```json
{"teamId":5406,"gameweeks":[9,10,11,12,13]}
```
Transfer request:
```json
{"teamId":5406,"gameweeks":[9,10,11,12,13],"numberOfTransfers":1,"bankOverride":null,"transferHit":4,"excludedPlayerIds":[]}
```
These gameweek numbers are examples only. The API validates against its current export. Optional modelUpdatedAt ensures the frontend and API snapshots match.

Responses use captainPlayerId, viceCaptainPlayerId, xiProjection, captainBonus and projectedTotal. The web client maps these fields to its existing pitch components. Extra response metadata includes source/match diagnostics. See /docs for full shapes.

Error codes: invalid/unpublished team or picks 404; malformed/invalid requests 422; stale projection version 409; oversized requests 413; FPL/data unavailable or optimizer busy 503; unexpected optimizer failure 500. Browser errors contain no stack traces or server filesystem paths. If a squad member is missing from projections, GET /team still identifies all 15 players and the missing ID; optimization is blocked with diagnostics.

## Reused rules
app/vendor/streamlit_rules.py contains 16 functions extracted without body changes from the original app.py; app/vendor/transfer_rules.py contains three unchanged helpers from web_transfers.py. Source filenames, SHA-256 and AST hashes are recorded in provenance.json. There are no runtime imports from the original project.
Original files were not changed, moved or deleted.

The extracted functions preserve permanent squad restoration, bank extraction, legal XI constraints, independent weekly optimization, captain scoring, same-position/club/budget rules, model-price conventions, No Transfer and bounded transfer search. New Python response formatting selects the second-highest starter as vice captain and sorts GK first on the bench, matching the existing web adapter.

Verify extraction integrity:
```sh
python scripts/verify_rules.py
python scripts/verify_rules.py --model-dir <original-model-directory>
```
Updates to the source rules require an explicit reviewed re-extraction and new provenance; this API never silently imports changed local source. Tests compare the extracted AST bodies to the recorded hashes.

## Data and performance
ProjectionStore parses the precomputed clean JSON once per file version, caches its dataframe/ID lookup, and checks file mtime/size on access. It reloads an atomic replacement on the next request. All matching uses integer FPL Player ID; no name joins.
Request operations sum/select existing scores only. No projection baseline, weighting, fixture calculation, updater, Excel or model rebuild runs in the API.
FPL metadata/history/picks have short bounded per-worker caches. Upstream failures are not cached as successful data. Manager cache entries expire after 60 seconds. Chip history must be verified; no unchecked fallback is used.
One-transfer search is exhaustive across legal positive buys. Two/three transfer search retains the existing bounded 10-state beam, 24-candidate shortlist and 3 buys per seller. It is not a global-optimality guarantee. Transfers remain immediate fixed-squad changes across the chosen horizon; no future scheduling or chips.
Transfer gains compare summed IN/OUT projections; updated XI gains separately include one captain bonus per week. Hits are charged once for a non-empty batch and never for rolling.

To update a standalone hosted snapshot later:
```sh
python scripts/sync_projections.py --source <clean-web-export.json>
```
Deploy the same version to the frontend and API. A frontend file update does not magically reach an independently hosted API. No automatic synchronization or scheduled model refresh is installed.

## React connection
The web project uses VITE_API_BASE_URL. Its ignored .env.development.local is configured locally:
```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8000
```
Run npm run dev in the web project and use http://127.0.0.1:5173. It now calls FastAPI directly over HTTP, with exact-origin CORS.
Production builds without an API URL keep the static projections-only notice. A later build with a real HTTPS VITE_API_BASE_URL enables personalized routes. Set that origin in API CORS too. This flag does not deploy either application.
The former loopback service on 8765 and its files remain intact for legacy usage; the updated React client uses the FastAPI contract.

## Tests
```sh
python -m pytest -q
```
Tests mock upstream FPL HTTP responses and cover the public endpoints, Free Hit restoration, 15/15 IDs, missing-player diagnostics, independent weekly XIs, captain/vice/bench, transfers, budget/club limits, exclusions, No Transfer, hits, request limits, CORS, errors and provenance.
The installed Starlette TestClient currently emits one upstream HTTPX deprecation warning; tests pass and production HTTP transport works.

Read DEPLOYMENT_READINESS.md and VALIDATION.md for the hosting requirements and delivered test results. Do not deploy without explicit approval.



## Render + Netlify deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for the complete manual sequence and environment settings. No external deployment or push has been performed. See [DATA_VERSION.json](DATA_VERSION.json) for the packaged snapshot identity.
