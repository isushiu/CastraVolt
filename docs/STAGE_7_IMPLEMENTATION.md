# Stage 7 — adoption dashboard and cached explanations

27 October 2026. Implements the user-approved option 2 using Chart.js 4.6.1, React/TypeScript, FastAPI and PostgreSQL. No change to charger prediction features or model files.

## What the planner can do

- View separate Selangor and Kuala Lumpur monthly registration lines.
- Select states, years and an inclusive timeline period, or align years by calendar month. Apply filters together and reset to defaults.
- Compare only common covered months with one click. October–December 2026 are unavailable, never zero-filled.
- Read selected totals, averages over distinct covered calendar months, peak monthly state counts and same-period previous-year growth. Missing comparison coverage or zero denominator produces an explanation instead of a percentage.
- Expand the accessible monthly table and source/version details.
- Request an optional Groq explanation, then reuse it without another provider call on identical data and filters. Charts are independent of Groq.

## Data and import

Source files in data/ML Data: ev_registration2024.csv, ev_registration2025.csv and vehicles_2026.csv. Scope is electric + motokar + Selangor/W.P. Kuala Lumpur. Rakan Niaga and other states/types/fuels are excluded. These are new registrations, not fleet ownership or charging demand.

Declared coverage: Jan–Dec 2024, Jan–Dec 2025 and Jan–Sep 2026. Dates are explicitly parsed as DD/MM/YYYY for 2024/2025 and ISO for 2026. Valid covered missing months are zero-filled during import; outside coverage is never filled.

Reconciled totals: 2024 2,688; 2025 1,797; 2026 1,916; combined 6,401. There are 66 state/month rows covering 33 distinct calendar months. Snapshot version: b028c5d4e5621e75cf4f6b263e5094e34976ad35b0e3c5a749badbe056f8531d.

The packaged aggregate resource contains per-source hashes and declared coverage, not individual vehicle records. Migration 0008_registration_trends creates registration_source_versions, registration_months and trend_summary_cache, and imports the package. Only one source version is active. Publication uses a transaction and database lock; repeated imports do not duplicate monthly rows.

For a reviewed future import, update the declared source coverage in trends_data.py, then run `.venv\Scripts\python.exe scripts/import_registration_trends.py --source-directory "data/ML Data" --write-package`. Review and commit the package with the scope/coverage change. Running the script without a source directory republishes the packaged version. Raw CSV files are not needed on every app startup or API request.

## API and cache

GET /api/v1/trends accepts states (comma separated), years, comparison_mode, start_month/end_month for timeline, or calendar_month_start/calendar_month_end for year comparisons. All endpoints require a signed-in planner. Invalid/ambiguous ranges are rejected. The response supplies active filters, coverage, source identities, monthly rows, totals, average, peak and per-year/state growth, plus an already cached explanation when available.

POST /api/v1/trends/summary requires CSRF and JSON containing filters and source_version. Metrics are recomputed from the active database snapshot; clients cannot submit facts or arbitrary prompts. Stale source versions are rejected. The server calls only https://api.groq.com/openai/v1/chat/completions with a configurable model, 30-second default timeout, bounded response size and 1,000 completion-token cap. The default model is openai/gpt-oss-20b. No automatic provider retries.

Cache key = SHA256(source version + canonical filters + model + prompt version). Reordering filters shares a cache entry. Successful explanations are shared across planners because the content contains only public aggregates. They persist until the identity changes or an administrator deliberately removes them. Summary generation is explicit; simply viewing charts never invokes Groq.

Pending leases prevent simultaneous requests for the same identity from creating duplicate paid calls. Fresh distinct generations have a separate 15-second per-planner guard; cached reads bypass it. Failed generation uses a short 30-second retry wait, stores no invented explanation and leaves all calculated metrics available. Provider bodies and credentials are not returned or logged. Rendered prose is plain escaped text and labelled AI-generated, with a verification note. LLM facts can still be wrong; displayed numeric metrics always come from deterministic calculations.

## API-key setup

1. Paste your key after CASTRAVOLT_GROQ_API_KEY= in the root .env file. It is ignored by Git and not exposed through Vite.
2. Optionally change CASTRAVOLT_GROQ_MODEL to a model your Groq account permits.
3. Restart via start.cmd, open EV adoption trends and click Generate summary.

The dashboard works without a key. Setup installs the new locked Chart.js dependency; startup applies the migration. Existing processes on 8000/5173 were not stopped or used for QA.

## Verification and limits

Final checks: **43 selected backend tests passed**, **32 frontend tests passed**, and the TypeScript/Vite production build passed. The backend selection covers Stage 7 plus accounts, projects, map and foundation regressions; it is not a claim that missing-model Stage 6 tests pass. Chart.js is loaded separately on the trends route (169 kB minified, about 59 kB gzip) rather than added to every page. Data reconciliation, zero-covered months, missing coverage, filter validation, matching-period growth, idempotent imports, one active version, CSRF/authentication, failed provider behaviour, canonical cache identities, model/prompt/source invalidation and concurrent duplicate generation are tested. Groq transport is verified with a bounded fake response; no real paid API call was made. Real Groq model/account availability remains to be confirmed after configuring the key.

Browser QA uses a disposable PostgreSQL database on ports 8001/5174 with Groq explicitly disabled. Confirmed login, Chart.js timeline, year comparison, common Jan–Sep selection (5,238 total across 27 covered months), source notes and unavailable-key behaviour. Screenshot: ../tmp/stage7-dashboard.png (local ignored verification artifact).

The missing Stage 6 serving model was subsequently restored and verified against all 380 saved held-out predictions. See MODEL_RESTORATION.md. Stage 8 release-readiness work remains.

## References

- Chart.js integration: https://www.chartjs.org/docs/latest/getting-started/integration.html
- Groq API compatibility: https://console.groq.com/docs/openai
- Groq model configuration: https://console.groq.com/docs/model/openai/gpt-oss-20b

## Migration continuity repair

Restored the previously applied 0007_optional_adoption revision and made Stage 7 revision 0008_registration_trends depend on it. The initial Stage 7 migration incorrectly followed 0006 while omitting the existing 0007 file. Databases already stamped with 0007 therefore could not start. Do not stamp over or reset these databases; the restored chain upgrades them normally and preserves prediction adoption history.

## Year-pair display and live Groq repair

The growth panel now displays pairs with previous-year source coverage (2024 → 2025 and 2025 → 2026), omitting the initial 2024 row that previously required unavailable 2023 data. Partial 2026 comparisons still use Jan–Sep in both years. The underlying registration series and totals are unchanged.

A real Groq request failed with HTTP 403 when urllib used its default Python user agent. The same configured key accessed Groq successfully with the CastraVolt/0.1 user agent. Completion requests now send that identifier and Accept: application/json. A real summary subsequently succeeded with the configured model, using only public aggregate facts. No key was printed or stored in source. The request-header regression is covered by a test. This supersedes the earlier note that live Groq calls were untested.
