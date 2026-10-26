# Local API validation and handoff

No deployment, provisioning, push or commit was performed.
## Project
fpl-cartel-api is a separate sibling of fpl-cartel-web under the task outputs directory. Original Streamlit/model sources remain outside both projects.
## Endpoints
GET /health; GET /team/{team_id}; POST /optimize/team-sheet; POST /optimize/transfers; POST /optimize/transfers/preview; GET /docs; GET /openapi.json.
## Reused unchanged functions

From app.py (extracted into streamlit_rules.py):
- is_free_hit_chip_name
- free_hit_events_from_entry_history
- squad_ids_from_picks_data
- bank_from_picks_data
- get_permanent_squad_before_gw
- is_valid_starting_xi
- optimize_starting_xi
- formation_text
- round_table_values
- calculate_team_sheet
- calculate_multi_gw_team_sheets
- club_rule_allows_transfer
- get_valid_buy_options
- get_projection_score
- add_transfer_upgrade_scores
- calculate_transfer_projection_total

From web_transfers.py (extracted into transfer_rules.py):
- player
- valid_buys
- search_options

All 19 function bodies and relevant constants were checked against the original files. API HTTP transport replaces UI-specific cached FPL fetch wrappers; calculation functions were not changed.
## Data
The API caches the clean export's dataframe and ID lookup by file mtime/size. It parses once per version. Local ignored configuration points at the same public/data/projections.json used by React. The API's portable data/projections.json is an identical independent deployment snapshot. No Excel read, model update or projection calculation occurs per request.
## Live HTTP results
- Local API: http://127.0.0.1:8000
- /health: HTTP 200, exactly {status:ok}.
- /docs and /openapi.json: HTTP 200; Swagger UI loaded in the browser.
- Team 5406: 15 permanent players, 15/15 matched, bank £0.0m, squad source GW8, Free Hit restoration used: False.
- GW9: formation 3-5-2, captain Haaland (ID 411), vice Groß (ID 124). XI 49.54960888 + captain 7.59168111 = 57.14128998.
- Five independent weekly sheets returned for GW9–GW13, with 11 starters/four bench, one GK in XI and one bench GK, one captain/vice, exact exported points and reconciled totals.
- 1-transfer test (GW9–GW13, 4-point hit): Calafiori → Guéhi; gross transfer gain 24.43, net 20.43. All returned options were checked for unique IDs, budget, positions and club limits.
- 2-transfer test (GW9–GW13, 4-point hit): João Pedro → McBurnie; Calafiori → Gabriel; gross transfer gain 51.64, net 47.64. All returned options were checked for unique IDs, budget, positions and club limits.
- 3-transfer test (GW9–GW13, 4-point hit): João Pedro → McBurnie; Calafiori → Gabriel; Thomas → Justin; gross transfer gain 69.28, net 65.28. All returned options were checked for unique IDs, budget, positions and club limits.
- Three-transfer updated preview returned five legal XIs. Original XI horizon total 294.39065756; updated 310.32546716; net XI gain after hit 11.93480960. Transfer gain and XI gain are intentionally separate measures.

## Browser integration
React Team Sheet and Transfers worked via direct HTTP to port 8000, including exact-origin CORS. Transfer recommendations and the shared updated pitch rendered without browser errors. Player Projections remains a static JSON consumer. The same fpl-cartel.team-id localStorage key is preserved.

## Tests/build
- 29 API/provenance tests passed, primarily with mocked FPL responses.
- 27 original model-side adapter/Team Sheet/transfer/Free Hit/gameweek tests passed.
- Seven frontend projection data tests passed.
- npm run build and the frontend artifact audit passed.
- Live tests are separate from the deterministic mocked suite.
- One upstream Starlette TestClient HTTPX deprecation warning remains; it is not a test failure.

## Preservation
SHA-256 checks confirm the six original app.py, projections.py, update_excel.py, gameweek_state.py, web_team_sheet.py and web_transfers.py files are unchanged. No original workbook or export was recalculated or overwritten. The API snapshot was copied, not moved.

## Frontend files changed
src/services/runtime.ts; src/services/api.ts (new); src/services/teamSheet.ts; src/services/transfers.ts; src/pages/TeamSheet.tsx; src/pages/Transfers.tsx; src/types/transfers.ts; vite.config.ts; .env.example; .gitignore and documentation. The ignored .env.development.local contains only the local API URL.

## Start again later
From this API folder run .\Start-Api.ps1, or activate its environment and run uvicorn app.main:app --reload. Run npm run dev from the web folder. The final API is left running locally; no remote service exists.

## Hosting
See DEPLOYMENT_READINESS.md: tested Python 3.12, initially one worker/CPU and 1 GB RAM, Uvicorn ASGI startup, exact ALLOWED_ORIGINS, HTTPS, request/concurrency controls and versioned projection JSON. These are preparation recommendations, not a provisioned or externally verified host.
