# Best Squad

Local implementation, 29 October 2026. No commit, push or hosted deployment performed by the agent.

POST `/optimize/best-squad` accepts:

```json
{"gameweek":9,"budget":100.0,"banned_player_ids":[],"modelUpdatedAt":"COPY_CURRENT_EXPORT_TIMESTAMP"}
```

`gameweek` must exist in the projection export. Budget is 95.0-115.0 million in 0.1 increments (default 100). Bans contain unique numeric Player IDs from the current export, not names. The optional modelUpdatedAt field retains the existing 409 mismatch protection. No manager Team ID or FPL upstream lookup is needed.

Response includes `players` (15), `startingXI` (11), `bench` (4), `captain`, `captainPlayerId`, `viceCaptainPlayerId`, `formation`, `squadCost`, `budget`, `squadProjection`, `xiProjection`, `captainBonus`, `projectedTotal`, `gameweek`, and `modelUpdatedAt`. Players include IDs, names, club, position, price, fixture and projected points.

The original Streamlit `build_best_squad`, SciPy and PuLP solver functions, candidate normalization and filtering were copied without changing their ASTs into `app/vendor/best_squad_rules.py`. SciPy 1.17.1 is a required production dependency and is the selected solver; the unchanged optional PuLP fallback is retained but not needed/installed. Source fingerprints are recorded in provenance.json and verified against the original app.py. Total verified extracted functions: 24 (the existing 19 plus 5 Best Squad functions).

The original single-gameweek objective maximizes the sum of projected points for all 15 players subject to exact position counts, club maximum and budget. It does not directly optimize the XI-plus-captain objective over every possible 15. The existing verified Team Sheet functions subsequently optimize XI and captain within the selected squad. The page explicitly explains this distinction. Bench GK is first, then the three outfield players in descending projected points. Displayed GW points exclude bench and add captain projection once to base XI points.

Errors: 422 invalid controls/IDs or no legal squad, 409 projection version mismatch, 503 existing concurrency gate or projection data unavailable. Existing error envelope, request-size limit and CORS middleware apply. No new environment variables or deployment commands are needed; Render installs the added SciPy requirement through its existing build command.

Frontend `/best-squad` uses the established API URL configuration and shared PlayerCard/Pitch. The optional forwardFirst pitch prop changes only Best Squad; Team Sheet and transfer previews retain their existing order. Search results and ban chips show Name (Club, Position), keyed by Player ID. Changing controls removes stale results. Budget slider and number input share state. Error/loading states and mobile layout match existing styles. Captaincy and Multi-GW Planner were removed from navigation and coming-soon names; the generic not-found route handles their old URLs.

Validation: all 49 backend tests and 9 frontend tests pass, including existing Team Sheet and Transfers regressions. API tests cover real-export budgets 95/100/105/115, bans, duplicate names, structure, club maximum, exact XI/bench membership, budget, captain scoring, infeasibility, request validation and version mismatch. Real-export objectives and XI values match the unchanged Streamlit functions; provenance comparison confirms the copied function bodies match the original source. One pre-existing Starlette TestClient deprecation warning remains. Frontend service contract/error tests pass, TypeScript and Vite build pass, deployment artifact audit passes. The updated requirements install into the isolated Python environment and pip check passes.

Live local HTTP: GET /team/5406, POST /optimize/team-sheet and POST /optimize/transfers returned 200 after the changes. Browser: default 100m squad, ban Haaland and rebuild, ordered pitch/bench, removed-route not-found pages, mobile 390px with document width exactly 390px. No hosted production test was performed.

| Budget | Squad cost | Squad projection | XI + captain |
| --- | --- | --- | --- |
| 95.0 | 94.8 | 71.71 | 62.74 |
| 100.0 | 99.8 | 73.59 | 64.01 |
| 105.0 | 104.9 | 74.57 | 64.99 |
| 115.0 | 115.0 | 75.40 | 65.25 |

These are GW9 results from the packaged export, not new projections. Projection JSONs, manifests and all six protected original model/Streamlit source files remain unchanged.

Deploy backend before frontend so the new API route is available when users open the new page. Retain the currently working Render CORS and Netlify VITE_API_BASE_URL settings. User performs all GitHub pushes. If continuous deployment is enabled, those pushes can trigger Render/Netlify builds; wait for the backend update to complete first.
