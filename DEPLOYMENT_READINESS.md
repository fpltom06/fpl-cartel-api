> Current deployment preparation: see [DEPLOYMENT.md](DEPLOYMENT.md) and [DEPLOYMENT_VALIDATION.md](DEPLOYMENT_VALIDATION.md). Earlier findings below are retained as historical local validation.

# API deployment readiness — not deployed

## Current status
The FastAPI wrapper is implemented and verified locally. No external service, account, container host, domain, certificate, database or hosting resource was provisioned. The frontend was not deployed.

The API project is self-contained: curated existing rules, HTTP service code, requirements, and a clean precomputed JSON snapshot. No Streamlit runtime, Excel workbook, original Windows directory, model updater, history workbook or projection calculation is needed on the API host.

## Suitable host requirements
- Python 3.12 (tested locally), an ASGI-capable persistent process, and outbound HTTPS access to the public FPL API.
- Start with one CPU, 1 GB RAM and one Uvicorn worker for private testing. This is a conservative starting recommendation, not a measured hosting minimum or load-tested capacity.
- Permit requests lasting at least a few minutes or plan a later job/poll interface. All-remaining-GW optimization can be substantially slower than one-week requests.
- HTTPS termination, process restarts, health checks, logs and environment configuration.
- Read-only access to the current clean projection JSON through a bundled artifact or mounted file. No arbitrary HTTP-provided file path is accepted.
- FastAPI/pandas/Pydantic/httpx/Uvicorn dependencies from requirements.txt. pandas/NumPy wheel support is needed; Python 3.12 is recommended for compatibility.
- No database is required for this phase.

Production startup:
```sh
uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --workers 1
```
Use the provider's assigned port, or an explicitly configured port if it does not supply PORT. Do not use --reload in production. Each worker has its own caches, memory and optimization limit; scale only after measurement.

Reference: [FastAPI manual server deployment](https://fastapi.tiangolo.com/deployment/manually/).

## Required environment and data
- PROJECTIONS_PATH: server-side path to the clean JSON. Default data/projections.json is portable and included.
- ALLOWED_ORIGINS: exact HTTPS Netlify test origin(s), comma-separated. No wildcard. The local defaults allow only the two requested development origins.
- FPL_BASE_URL, metadata/manager TTLs, timeouts, request-size and optimizer-concurrency settings are documented in .env.example.
- No API key or secret is currently required. Actual future secrets must stay in server environment variables, never VITE_ variables or JSON.
- The ignored local .env points at the sibling web project's JSON for convenient local refreshes. This is not the production setting to copy blindly.
- The frontend and API must receive the same projection export/version. The API checks modelUpdatedAt when the browser supplies it.
- Refresh the model separately, copy the clean snapshot, and redeploy or atomically update the API's file. No Excel refresh or model generation runs inside a request.
- Health checks use GET /health. This is a liveness check; a missing/invalid projection file is reported as 503 by data endpoints.

## Frontend connection
Set VITE_API_BASE_URL to the actual HTTPS API base URL at frontend build time. Production personalized routes are enabled when that URL is present. Without it, the static test behavior remains projections-only.

The local development override is ignored and points at port 8000. No localhost URL is hard-coded in first-party production browser source. The Vite proxy is a development fallback only.

CORS allows exact origins and GET/POST/OPTIONS, without credentials. See [FastAPI CORS guidance](https://fastapi.tiangolo.com/tutorial/cors/).

## Boundaries before any later deployment
This phase intentionally has no login. CORS is not authentication: non-browser clients can call a public API. Before exposing it beyond a controlled test, decide API visitor protection and edge rate/concurrency limits along with frontend privacy. A private Netlify frontend does not automatically protect a separate API domain.

A simple synchronous Netlify proxy has a documented 26-second timeout, which is unsuitable for the longest calculations. Use direct HTTPS API access with exact-origin CORS and suitable timeouts, or implement job submission/polling later. No job store or new scheduling behavior was introduced.
Reference: [Netlify proxy limits](https://docs.netlify.com/manage/routing/redirects/rewrites-proxies/).

## Preserved behavior
- 19 extracted function bodies are checked against original-source AST hashes.
- Existing FPL ID/Free Hit/bank/position/club/price/transfer-score/No Transfer rules are reused.
- One normal captain bonus is counted, vice captain and bench do not add points.
- Each selected GW is optimized independently from a fixed squad.
- Original model and Streamlit files remain unchanged.
- Two/three transfers retain the existing bounded sequential search; no global optimum is claimed.
- No projection formulas, historical matching, weighting, penalties, minutes or injury handling were migrated.

## What remains before hosting
1. Explicit approval to select/configure a Python hosting environment.
2. Verify runtime, dependency installation and resources on that host.
3. Configure HTTPS, exact allowed frontend origin, data path/version and process command.
4. Choose access/rate protections appropriate for the private test.
5. Set the frontend API URL and rebuild.
6. Run hosted health/docs, CORS, data-version and Team 5406 smoke tests.
7. Only then approve the external test deployment.

These hosting checks have not been claimed completed locally.

