# Deploy FPL Cartel: API on Render, frontend on Netlify

Prepared locally only. No external repository, account or service has been created; nothing has been pushed or deployed. Follow these steps manually when ready. Each project is its own repository. Commands below run in that project's terminal directory, not their shared parent. Replace angle-bracket placeholders with values you copy; never type the brackets.

## A. Create the API GitHub repository
Sign in to GitHub. Click **+ > New repository**. Name it `fpl-cartel-api`. Select **Private** for source privacy. Leave README, .gitignore and license initialization unchecked. Click **Create repository**. Copy the HTTPS repository URL shown. Source privacy does not make the deployed API or website private.

## B. Push the API
Open a terminal inside `fpl-cartel-api` (the folder containing `requirements.txt` and `app/`). Git is already initialized on `main`, with no commits or remote. Run:

```powershell
git status --short
git add .
git diff --cached --stat
git diff --cached
```
Review the staged files. `data/projections.json` is intended public-facing model output. There must be no `.env`, Excel, venv, personal configuration or credentials. Then run:

```powershell
git commit -m "Prepare FPL Cartel API for Render"
git remote add origin <API_REPOSITORY_HTTPS_URL>
git push -u origin main
```
GitHub may prompt you to authenticate through its credential manager. Do not put a token in a repository file or remote URL.

## C. Create the Render Web Service
Sign in to Render. Click **New + > Web Service**, connect GitHub, grant access to the API repository, and select `fpl-cartel-api`. Use the Git repository option, not a static site or private service. Set:

| Setting | Value |
| --- | --- |
| Runtime / Language | Python 3 |
| Branch | main |
| Root directory | Leave blank (API is repository root) |
| Build command | `python -m pip install -r requirements.txt` |
| Start command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1` |
| Health check path | `/health` |

Choose the region and instance plan you approve. One worker is deliberate: optimizer concurrency and caches are per process. No production capacity benchmark has been performed. Free instances may sleep, so first requests may be slow; this requires hosted testing. Do not add `--reload`, a fixed port, disk mount or model updater. Render supplies `PORT`.

Under **Environment**, set `PYTHON_VERSION=3.12.14` and `PROJECTIONS_PATH=data/projections.json`. Set `ALLOWED_ORIGINS` to an empty string initially; this permits no browser origins while the frontend address is unknown. If the dashboard cannot save a blank value, temporarily use the exact local development origin `http://127.0.0.1:5173`, then replace it at step L. Never use `*`. All other variables may use the defaults below. Click **Deploy Web Service**. Wait for a successful deploy. If health check path was not on the creation form, set it in the service's **Settings > Health Checks** and save.

`render.yaml` records the same service settings for an optional Blueprint workflow; do not create a second service from it after following this manual workflow. Merely having the file does not provision anything. `.python-version` also pins Python 3.12.14.

## D. Test the API health
In Render's service overview, open the service's assigned HTTPS address and append `/health`. Expect `{"status":"ok"}`. Open `/docs`, then use **GET /team/{team_id} > Try it out**, enter `5406`, and execute. Expect 15 players. Health is a fast liveness check; it does not run optimizers, load projections or contact FPL, so also test the team and optimizer routes in Swagger.

## E. Copy the real API URL
Copy the assigned Render service origin exactly, beginning `https://`, with no trailing slash and no `/docs` or `/health`. Save it as your API URL. This document intentionally does not assume an assigned hostname.

## F. Create the frontend GitHub repository
In GitHub, **+ > New repository**. Name it `fpl-cartel-web`, select your preferred source visibility (Private recommended for this test), leave initialization options unchecked, and create it. Copy its HTTPS repository URL.

## G. Prepare VITE_API_BASE_URL
The variable name is `VITE_API_BASE_URL`; its value will be the actual Render origin copied in E. Save that value for Netlify step I. Do not commit a production `.env`. This is a public browser setting, not a secret. Never put API credentials in a `VITE_` variable. Local development remains configured independently through the ignored `.env.development.local`.

## H. Push the frontend
Open a terminal inside `fpl-cartel-web` (containing `package.json`). Run:

```powershell
git status --short
git add .
git diff --cached --stat
git diff --cached
```
Review: no `.env`, `.local`, Excel, credentials, node_modules or dist should be staged. Then:

```powershell
git commit -m "Prepare FPL Cartel frontend for Netlify"
git remote add origin <WEB_REPOSITORY_HTTPS_URL>
git push -u origin main
```

## I. Connect the frontend to Netlify
Sign in to Netlify. Select **Add new project > Import an existing project > GitHub** (older UI may say Add new site). Authorize access to `fpl-cartel-web` and select it. Use branch `main`, leave base/package directories blank, set build command `npm run build`, publish directory `dist`. `netlify.toml` records these settings and Node 22.

Before deploying, expand **Environment variables > Add environment variable** and set `VITE_API_BASE_URL` to the actual Render origin from E. Include **Builds** scope and the Production context if scope/context controls are shown. If the import wizard lacks this field, finish import and immediately go to **Project configuration > Environment variables**, add it, then trigger a new production build before testing personalized tools. Netlify does not obtain this setting from your ignored local `.env`. Changing it requires rebuilding the frontend.

## J. Deploy the frontend
Click **Deploy project** and wait for success. If changing a variable after a build, open **Deploys > Trigger deploy > Deploy project** to rebuild. Do not upload the local `dist` from this preparation: its final safe build has no assigned production API URL yet. Let Netlify build from Git with its environment variable.

## K. Obtain the frontend URL
Copy Netlify's assigned production HTTPS origin from Project overview. Do not copy a deploy-specific preview URL. Public hosting is the default: private GitHub source does not restrict visitors. If private testing is required, configure and verify Netlify visitor access protection available on your plan before sharing the URL. The API currently has no authentication; CORS restricts browser origins, not direct HTTP clients.

## L. Add the exact Netlify origin to Render
Open Render API service **Environment**, edit `ALLOWED_ORIGINS`, paste the exact Netlify HTTPS origin with no trailing slash or path. Multiple origins use a comma-separated list, for example `https://example.netlify.app,https://www.example.com` (illustrative only). No wildcard or wildcard subdomains. Add custom domains individually later. Preview URLs are blocked unless explicitly added.

## M. Apply the API environment change
Use Render **Save, rebuild, and deploy** / **Save and deploy** when offered. If only saved, use **Manual Deploy > Deploy latest commit** so the running process reads the new environment. Wait for live status and retest `/health`. Changing CORS requires an API restart/redeploy, not a frontend rebuild.

## N. Test the deployed application
Directly open and reload `/`, `/projections`, `/team-sheet`, `/transfers`. All must load through the SPA fallback. On Team Sheet enter Team ID `5406`, click **Load Team**, inspect starting XI, captain, bench and multiple gameweeks. On Transfers load 5406, test one transfer and preview its updated XI. Confirm no requests go to localhost or `/api` on Netlify; browser Network should show your Render origin. Inspect errors in browser Network/Console and Render logs if needed. Test Refresh on projections: it fetches deployed JSON only. It cannot run Python, PowerShell, Excel or the model updater.

## Backend environment reference

| Variable | Default / deployment value | Purpose |
| --- | --- | --- |
| PYTHON_VERSION | `3.12.14` on Render | Runtime selection |
| PORT | Render supplies it | Uvicorn bind port; do not set a fixed value |
| PROJECTIONS_PATH | `data/projections.json` | Relative to API project root; packaged file |
| ALLOWED_ORIGINS | Empty initially; exact Netlify origin later | Comma-separated HTTP(S) origins; blank denies browser CORS; unset uses local development defaults |
| FPL_BASE_URL | `https://fantasy.premierleague.com/api/` | Public upstream API; normally leave unchanged |
| FPL_METADATA_TTL | `300` | Metadata cache seconds |
| FPL_MANAGER_TTL | `60` | Manager cache seconds |
| FPL_TIMEOUT_SECONDS | `10` | Upstream timeout seconds |
| MAX_REQUEST_BYTES | `16384` | Request body limit |
| MAX_OPTIMIZER_CONCURRENCY | `1` | Optimizer slots per worker |

No service API keys are needed. `.env.example` documents local defaults; do not upload a real `.env` to Render or Git. The frontend needs only `VITE_API_BASE_URL`; Netlify's `NODE_VERSION=22` is in its configuration file.

## Keep projections synchronized
Frontend: `public/data/projections.json`. Backend: `data/projections.json`. Both contain only precomputed web output. `DATA_VERSION.json` in each repository records SHA-256, modelUpdatedAt, exportedAt, rowCount, player count and gameweeks. Do not change projection calculations. For future updates, run the existing local export workflow, copy the same JSON into both projects (API helper: `python scripts/sync_projections.py --source <EXPORTED_JSON>`), regenerate both manifests with `python scripts/projection_manifest.py <JSON_PATH>`, compare hashes, commit and redeploy both repositories. The frontend sends modelUpdatedAt on optimizer requests and the API rejects mismatches with HTTP 409. Matching timestamps alone do not prove identical bytes: compare manifests too. The website Refresh only fetches the latest already-deployed frontend JSON; it cannot synchronize two Git repositories or deploy data.

## Local verification commands
API: Python 3.12, `python -m venv .venv`, activate it, `python -m pip install -r requirements.txt`, then `uvicorn app.main:app --host 0.0.0.0 --port $env:PORT --workers 1` in PowerShell after setting a test `$env:PORT`. The cloud command uses `$PORT` in Render's shell. For browser tests set `ALLOWED_ORIGINS` to the exact local preview origin. Developer tests additionally use `requirements-dev.txt`.

Frontend: `npm ci`, `npm test`, `npm run build`, `npm run audit:build`. For a temporary local production integration test set `$env:VITE_API_BASE_URL='http://127.0.0.1:8000'`, build and run `npm run preview`. Remove the environment override and rebuild before auditing/shipping local artifacts; the deployment audit intentionally rejects loopback URLs in output. Netlify builds with the real HTTPS origin.

## Official references
- [Render Python version](https://render.com/docs/python-version)
- [Render Web Services](https://render.com/docs/web-services)
- [Render health checks](https://render.com/docs/health-checks)
- [Render Blueprint specification](https://render.com/docs/blueprint-spec)
- [Netlify build settings](https://docs.netlify.com/build/configure-builds/overview/)
- [Netlify environment variables](https://docs.netlify.com/configure-builds/environment-variables)
