# Deployment preparation validation

Completed locally on 26 October 2026. No account creation, GitHub push, Render provisioning or Netlify deployment was performed. Both directories have independent Git repositories on main, without commits or remotes. Review and first commit remain manual.

## Runtime and tests
- Fresh isolated Python 3.12.14 environment (include-system-site-packages=false), installed only requirements.txt from PyPI; pip check: no broken requirements. Production dependencies exclude pytest, Streamlit and Excel readers.
- Uvicorn app.main:app, bind 0.0.0.0, port supplied through PORT, one worker, no reload. Test port 8001; exact local preview origin 127.0.0.1:5180 permitted for this test only.
- Real live FPL Team 5406: 15 players; health/docs/team, five-gameweek Team Sheet, Transfers all HTTP 200. Health approximately 8 ms. Ten transfer recommendations returned. Allowed CORS preflight 200; unapproved origin 400 without allow-origin header.
- One deliberately overlapping browser/shell optimizer request received the existing optimizer-busy HTTP 503; rerun sequentially passed. This is the configured one-slot concurrency protection, not an optimizer calculation change.
- API suite: 33 tests passed, one upstream Starlette TestClient deprecation warning concerning httpx. Frontend: 7 tests passed.
- Production frontend build with temporary VITE_API_BASE_URL pointing at the clean local API passed. Browser direct visits to /, /projections, /team-sheet, /transfers loaded. Team Sheet 5406 displayed 15/15 matches, GW9 total 57.14, 3-5-2. Transfers returned Calafiori to Guehi, net gain 4.93 and updated XI total 58.58. Automatic updated-team preview succeeded. Refresh was exercised; source confirms fetch-only /data/projections.json with no-store.
- Final frontend was rebuilt without the temporary loopback API setting. Build and audit:build passed; six intended output files only, identical projection bytes, no personal paths/credentials/loopback network URL. React Router has two dummy localhost URL-parser bases, not network calls. Netlify must build with the actual Render URL to enable personalized tools; it is intentionally not invented here.
- Hosted Linux execution, actual Netlify rewrites, service capacity, cold starts and hosted access controls await manual deployment. Local preview verified SPA routes and the deploy redirect file was checked; no claim of a live hosted test is made.

## Data and rule preservation
Both projection JSONs have identical bytes and SHA-256, recorded in DATA_VERSION.json. 669 players, 20,070 rows, GW9-38. Model timestamp 2026-10-26T17:28:05.660015+00:00. Existing modelUpdatedAt mismatch protection returns 409. Manifests add byte-level comparison without modifying calculations. The frontend deployment audit now validates its manifest hash.

Backend dataset is data/projections.json relative to the API repository. The ignored local API .env now also uses this packaged path. No production dependency on another local project or Excel exists.

Verified all 19 vendored optimizer/Free Hit/transfer rule functions against original source. The six protected original model/Streamlit files retain their baseline SHA-256 hashes. Projection formulas and model sources were not changed.

## Security and Git audit
Scanned all Git-eligible source/document/config/data files in both repositories for user home paths, username, credential/private-key markers, API keys, client secrets, passwords, token/Discord secret patterns and private/local URLs. No actual credentials or personal filesystem paths were found in Git-eligible files. Legitimate local development loopback URLs and generic placeholders remain documented; Vite proxy and local launch scripts intentionally support local development. Production first-party browser code has no hardcoded local address.

Ignored local frontend .local/settings.json contains personal model/runtime paths; ignored local environment files contain loopback development configuration. These are excluded from Git and dist. Generated environments, node_modules, caches and logs can also contain local paths and are ignored. No legitimate development documentation was removed. Previous readiness reports are labeled historical and link to the current guide.

Both gitignores cover environments, venv, node_modules, dist, Python/pytest caches, Excel, IDE configuration, logs and common credential files while explicitly allowing .env.example. Git-eligible file inventory contains packaged clean JSON and no Excel or private model source beyond the required unchanged extracted optimizer rules. Common credential pattern checks are not a guarantee against every possible secret; staged diffs should still be reviewed before the manual first commit.

CORS initially denies all browser origins when ALLOWED_ORIGINS is blank, then accepts only configured exact origins. CORS is not authentication. No accounts/authentication were added.

## HTTP verification detail

```json
{
  "/health": {
    "status": 200,
    "seconds": 0.008
  },
  "/docs": {
    "status": 200,
    "seconds": 0.001
  },
  "/team/5406": {
    "status": 200,
    "seconds": 0.048,
    "players": 15
  },
  "/optimize/team-sheet": {
    "status": 200,
    "gameweeks": 5,
    "recommendations": 0
  },
  "/optimize/transfers": {
    "status": 200,
    "gameweeks": 5,
    "recommendations": 10
  },
  "http://127.0.0.1:5180": {
    "status": 200,
    "allowOrigin": "http://127.0.0.1:5180"
  },
  "https://unapproved.example": {
    "status": 400,
    "allowOrigin": null
  }
}
```

See DEPLOYMENT.md for the complete A-N sequence, commands and environment reference. First manual action: create an empty GitHub repository named fpl-cartel-api without auto-generated README, license or gitignore.
