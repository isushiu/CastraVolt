# CastraVolt

Urban EV infrastructure planning for Kuala Lumpur and Selangor.

## Current state

Stage 2 adds individual accounts: registration/verification/resend, login/logout, password recovery/reset, protected workspace routes, PostgreSQL-backed rate limits and hashed opaque sessions. Argon2id hashes passwords. Verification/reset tokens are hashed at rest, single-use and expire after 60/30 minutes. Sessions expire after the configured lifetime (default 24 hours); resetting a password revokes all sessions. Cookie-authenticated writes require a matching CSRF token and an allowed browser Origin.

Development mail: the default `CASTRAVOLT_MAIL_MODE=file` writes private `.eml` files under `tmp/mailbox`; open them locally to use verification/reset links. No public endpoint exposes the inbox or raw tokens. Keep the ignored tmp directory private. Delivery runs after the HTTP response in a background task; it is best-effort rather than a durable queue, and failed delivery is recorded without recipient/token details. Users can request a new link. Production mail delivery is not verified by local tests.

Production configuration: set `CASTRAVOLT_ENVIRONMENT=production`, HTTPS `CASTRAVOLT_FRONTEND_URL`, `CASTRAVOLT_SECURE_COOKIES=true`, `CASTRAVOLT_MAIL_MODE=smtp`, `CASTRAVOLT_MAIL_FROM`, `CASTRAVOLT_SMTP_HOST`, `CASTRAVOLT_SMTP_PORT`, `CASTRAVOLT_SMTP_STARTTLS=true`, and SMTP credentials if required. Restrict `CASTRAVOLT_CORS_ORIGINS` to actual trusted frontend origins. Production settings reject file capture/insecure cookies/non-TLS SMTP. Configure deliverability, secrets, expiry/retention and durable delivery if operational requirements need it before production release.

Account integration tests use a uniquely named disposable PostgreSQL database, apply actual migrations, then drop only that database. Run `uv run pytest tests/test_accounts.py tests/test_foundation.py tests/test_dev_workflow.py -q` with local PostgreSQL available. The configured local DB role needs permission to create a test database. These tests do not truncate your application database. Frontend DOM tests verify session revocation on focus and protected-content removal.

Stage 1 foundation remains the React/TypeScript shell, typed FastAPI connection, health/readiness endpoints, bounded PostgreSQL engine configuration and Compose setup. Stage 2 now supplies real account access; private project CRUD, map extraction and prediction endpoints arrive in later stages. Unfinished project/model features are clearly labelled.

The supplied model was inspected and the selected tuned pipeline reconstructed with prediction parity. See [Stage 0 handoff](STAGE_0_HANDOFF.md). Original POI extraction compatibility is still pending.

## Local setup

Simplified Windows entry points: `setup.cmd` prepares dependencies and generates local credentials when `.env` is absent; `start.cmd` supervises database/migrations/API/frontend in one terminal. Their standard-library implementation is `scripts/dev.py`. The manual commands below remain available for debugging. Existing configuration is never overwritten; Ctrl+C stops only child app services and a database started by that invocation. Startup rejects occupied application ports and reports missing Docker/setup clearly. The Python 3.12 launcher is managed by uv and the frontend install follows package-lock.json.

Requirements: Python 3.12+, uv, Node 22.12+ (or a supported newer Node release), and Docker Desktop with its Linux engine running, or an existing PostgreSQL server.

1. Copy `.env.example` to `.env`. Choose a local PostgreSQL password and update both password fields consistently; URL-encode reserved characters in the connection URL. Never commit `.env`.
2. Install the backend: `uv sync --locked`.
3. Start PostgreSQL: `docker compose up -d db`.
4. Apply the migration baseline: `uv run alembic upgrade head`.
5. Start API: `uv run uvicorn castravolt.main:app --host 127.0.0.1 --port 8000`.
6. In another terminal, `cd frontend`, then `npm ci` and `npm run dev`.
7. Open http://127.0.0.1:5173. The Vite proxy forwards `/api` and `/health` to FastAPI. API docs: http://127.0.0.1:8000/docs.

The frontend and liveness API can run without PostgreSQL; `/health/ready` correctly returns 503 until a configured database is reachable. Readiness currently covers foundation database connectivity only and explicitly reports predictions unavailable. Later stages must add schema/auth/model readiness requirements.

PostgreSQL is bound only to local loopback. `docker compose down` stops services without deleting database storage; do not use `down -v` unless intentionally discarding local data. Production credentials, HTTPS, email/provider choices and deployment are not configured by this stage.

## Checks

- Backend: `uv run pytest tests/test_foundation.py -q`.
- Frontend: from `frontend/`, `npm test` and `npm run build`.
- API types: with the API running, from `frontend/`, `npm run generate:api`. Commit the regenerated schema when the API changes. The current schema is generated from FastAPI OpenAPI.
- Database migration SQL without a live server: `uv run alembic upgrade head --sql` (requires the configured connection URL but does not connect).
- Model handoff: `uv sync --group model-validation`, then `uv run --group model-validation python scripts/verify_model_handoff.py`.

Frontend dependencies are pinned with a lockfile. The project-local `.npmrc` avoids an observed npm 11.4 peer-resolution crash; build/test checks validate the resulting installation. No global npm settings are changed.

## Structure

- `frontend/`: React/Vite application, visual tokens, typed API client and frontend tests.
- `src/castravolt/`: FastAPI configuration, application and database foundation. This retains the existing uv Python package layout rather than introducing a second Python package under backend.
- `backend/migrations/`: Alembic migration environment and versions.
- `scripts/`: reproducible model-handoff verification.
- `model/`: original user-supplied experiment export and separately verified handoff.
- `notebooks/`: offline ML development/evaluation.
- `tests/`: backend and notebook verification.

Product/design/build decisions live in PRD.md, TRD.md, DESIGN.md and IMPLEMENTATION_PLAN.md. Model artifacts and environment files are excluded from Git; manifests/fixtures are retained. Transfer trusted artifacts explicitly when moving this project to another machine.


## Internal prototype and project storage

Default `CASTRAVOLT_INTERNAL_ACCESS=true`: login ID `admin`, password `123`; public registration and email recovery are disabled. A hashed persistent admin row is created on first successful login. Everyone with this shared login sees its records. Production settings reject demo access.

Migration `0003_projects` adds projects, sites and prediction snapshots. Run the normal startup launcher to apply it. Projects/sites support CRUD; prediction endpoints are read-only until model integration. Confirmed deletion cascades through child sites/predictions. State remains unresolved until map/boundary integration.

Full local application checks: `uv run pytest tests/test_accounts.py tests/test_projects.py tests/test_foundation.py tests/test_dev_workflow.py -q`. PostgreSQL integration tests create and drop uniquely named test databases, preserving the application database. The retained public-account tests use explicit non-internal settings in disposable databases.

## Stage 4 providers and state boundaries

- Run setup after updating frontend dependencies, then startup; migration `0004_geocode_cache` is applied automatically.
- Leaflet 1.9.4 and @types/leaflet 1.9.21 are locked. Default tiles: https://tile.openstreetmap.org/{z}/{x}/{y}.png with OSM attribution and normal browser caching. Optional overrides `VITE_MAP_TILE_URL` / `VITE_MAP_TILE_ATTRIBUTION` belong in frontend/.env.local and require restarting Vite (rebuild for production).
- Backend `CASTRAVOLT_GEOCODER_URL` and `CASTRAVOLT_GEOCODER_USER_AGENT` configure Nominatim-compatible HTTPS search. Public Nominatim requires an identifying application User-Agent, caching and no more than one request/second; the global PostgreSQL reservation uses 1.1 seconds. Search is explicit, never autocomplete. Select a suitable service for significant traffic.
- `GET /api/v1/locations/search?q=...` and `/locations/validate?latitude=...&longitude=...` require a session. Search errors do not become cached zero results. Validation requires no remote geocoder and state cannot be supplied by the browser.
- Boundary source, exact hashes and ODbL license are bundled in src/castravolt/resources. Data represents 2017 and urban-only coverage is provisional. Include these package resources when deploying; missing/corrupt geometry must not be replaced with a bounding rectangle.
- Expanded suite: `uv run pytest tests/test_locations.py tests/test_map_api.py tests/test_projects.py tests/test_accounts.py tests/test_foundation.py tests/test_dev_workflow.py -q`.
- Policies checked: https://operations.osmfoundation.org/policies/nominatim/ and https://operations.osmfoundation.org/policies/tiles/. Leaflet Circle radius is in metres: https://leafletjs.com/reference.html#circle.

## Stage 5 feature service

`POST /api/v1/sites/{id}/features` requires a session, CSRF and ownership. It reads the persisted site; never trust browser-supplied POI/adoption counts. Migration 0005 adds the successful-extraction cache. `CASTRAVOLT_OVERPASS_URL` configures the HTTPS provider; default Private.coffee. `CASTRAVOLT_POI_CACHE_HOURS` defaults to 24. Outgoing misses reserve a shared 35-second lease; per-IP/user quotas also apply. Failures do not poison the cache.

Run `uv run python scripts/prepare_adoption_context.py` to reconcile the current filtered 2025 CSV into packaged context. Counts differing from the evaluated setup fail for review rather than silently changing the model's inputs. Hash/scope are included. No pandas or raw CSV read is required on normal API requests.

Run `uv run pytest tests/test_features.py tests/test_feature_api.py` plus existing application tests. Original extraction parity is pending; no configuration flag automatically approves new rules for inference. Read docs/STAGE_5_IMPLEMENTATION.md before Stage 6.


Provider errors now retain Retry-After for UI countdowns. Check logs for `poi_provider_failure kind=... status=... request_id=...`. The message distinguishes timeout, connection, TLS verification, provider overload and incomplete result. The shared lease is shortened on completion/failure rather than always holding 35 seconds. Never disable certificate checks or treat failures as zero POIs. Current live provider access remains unverified after reproducible status failures.


## Bundled local POIs (default)

`CASTRAVOLT_POI_SOURCE=local` uses hash-checked resources/poi_snapshot.json.gz, with source coverage/time/ODbL metadata in poi_snapshot_manifest.json. Local context requests have no Overpass dependency or cooldown. `overpass` is an explicit alternative, using the configured HTTPS endpoint and native system TLS verification. Snapshot source/rule hashes enter cache keys; do not edit a manifest to disguise incompatible rules.

For a deliberate source refresh: install optional tooling with `uv sync --locked --group poi-build --group model-validation`; download and verify a trusted Geofabrik source PBF; run `uv run --group poi-build --group model-validation python scripts/build_local_pois.py <source.osm.pbf>`. Inspect fixture counts/source/license and commit the compact snapshot plus manifest together. Never publish an incomplete build. Restart workers after a snapshot update. Source PBF files stay in ignored data/poi/source; normal setup does not need osmium or a source download.

The source reader uses multiple filtered passes, with strict missing-reference handling for study coverage. Native source polling defaults on in launcher children to avoid missed filesystem events. This does not modify global environment settings.


## Stage 6 model serving

Setup already installs the model-validation group. Manual serving should retain it: `uv run --group model-validation uvicorn castravolt.main:app --host 127.0.0.1 --port 8000`. `CASTRAVOLT_MODEL_DIRECTORY` defaults to the repo-relative model/verified_rf80_cv5; trusted manifest, fixtures and ignored evaluated_pipeline.joblib are required. Check `/health/model` for artifact readiness. Foundation DB readiness does not certify model/data validity.

`POST /api/v1/sites/{id}/predictions`: JSON idempotency_key (UUID), site_updated_at (aware timestamp) and acknowledge_unverified_pois=true. The latter is the labelled experimental development action, not scientific approval; production rejects unverified feature inference. No browser feature counts are accepted. Migration 0006 enforces key uniqueness. History GETs remain immutable/owned; metadata includes full model and source hashes.

Full application verification adds tests/test_inference.py and tests/test_prediction_api.py to the existing suite. Experimental requests cannot mark POI parity verified. Retain all scientific limitations when transferring or demonstrating this prototype.
