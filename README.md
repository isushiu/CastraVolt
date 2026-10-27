# CastraVolt

Urban EV infrastructure planning for Kuala Lumpur and Selangor.

<<<<<<< Updated upstream
## Current state
=======
Built with React, TypeScript, FastAPI and PostgreSQL. Internal login, projects, map/address selection and saved sites are available. Research model estimates and saved history are available; the trends dashboard is under development.
>>>>>>> Stashed changes

Stage 1 foundation: React/TypeScript Midnight Iris workspace shell, typed FastAPI connection, health/readiness endpoints, bounded PostgreSQL engine configuration, initial Alembic baseline and local Compose configuration. Accounts, real private projects, map extraction and prediction endpoints arrive in later stages. Preview pages explicitly identify unfinished features and do not invent project/model results.

The supplied model was inspected and the selected tuned pipeline reconstructed with prediction parity. See [Stage 0 handoff](docs/STAGE_0_HANDOFF.md). Original POI extraction compatibility is still pending.

## Local setup

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

<<<<<<< Updated upstream
Product/design/build decisions live in PRD.md, TRD.md, DESIGN.md and IMPLEMENTATION_PLAN.md. Model artifacts and environment files are excluded from Git; manifests/fixtures are retained. Transfer trusted artifacts explicitly when moving this project to another machine.
=======
```powershell
.\start.cmd
```

This starts PostgreSQL, applies migrations, and launches the backend and frontend together.

Open [CastraVolt](http://127.0.0.1:5173/). Keep the terminal open; press **Ctrl+C** to stop the app. Database data is preserved. A database already running before startup is left running.

After the first setup, you normally only need to open Docker and run `.\start.cmd`.

## Sign in

Use **User ID: `admin`** and **Password: `123`**. No registration or email verification is needed. Everyone using this internal demo account shares its projects and sites.

After updating an existing checkout, stop the app and run `start.cmd` again. Startup applies the new project/site migration automatically and keeps existing data. Shared demo credentials are for local development only.

## macOS / Linux

Use `sh check.sh`, `sh setup.sh`, and `sh start.sh` instead of the Windows commands. These launchers are provided but have not yet been tested on those operating systems.

## Using another computer

Clone or copy the project into any folder, install the requirements, and follow the steps above. No personal directory paths are required. Do not copy `.venv`, `node_modules`, or someone else's `.env`; setup prepares them locally.

The app uses local ports **8000** and **5173**, and PostgreSQL uses host port **55432** by default. These ports must be free. If you change the database port, update both `POSTGRES_PORT` and the port in `CASTRAVOLT_DATABASE_URL` in `.env`. The container's internal database port stays 5432. Model `.joblib` files are excluded from Git and must be transferred separately from a trusted source when needed for prediction features.

Python runs inside the project's `.venv` automatically. You do not need to activate it or see `(.venv)` in the terminal prompt; `(base)` can remain visible.

These requirements are for local development. Planners using a future hosted version will need only a browser.

## Troubleshooting

- **Docker unavailable:** open Docker Desktop and resolve any engine, WSL or virtualisation message it shows.
- **Port already in use:** stop the older CastraVolt preview before starting again.
- **Files locked during setup:** stop running previews, then rerun `.\setup.cmd`.
- **A service fails to start:** inspect `tmp/dev-backend.log` or `tmp/dev-frontend.log`.

For manual startup, tests and technical details, see [Development notes](docs/DEVELOPMENT.md).

## Choosing a site

Open a project → **Add site on map**. Search for an address, click the map, or drag the pin. Confirm the site name/category, then save. The dashed circle shows 3 km; the app checks the pin is in Kuala Lumpur or Selangor. Urban-only coverage remains provisional. **Open on map** edits a saved site.

Internet access is needed for map tiles and address search. State checks use bundled research boundaries. The public map/search providers are development defaults; larger deployments need suitable provider arrangements. POI gathering and ML estimates are later stages.


If a new screen shows **Not Found** for location checks after an update, the old backend is still running. Stop the app in its terminal with Ctrl+C, then run `.\start.cmd` again. Development startup now reloads backend Python changes automatically. Coordinates/state/address are derived from the map pin; site creation and editing use the map only.


## Preparing site context

Save a site, then choose **Prepare site context** to request nearby mapped facilities within 3 km and its state's fixed 2025 EV registration figure. Counts are cached and can take time to fetch. Provider errors show a retry message; they never mean zero facilities.

The current counting rules are a **research preview** awaiting comparison with the original training extraction rules. This does not yet produce charger predictions. External Overpass service availability was not verified successfully in this development session. Restart with start.cmd after updating to apply the POI-cache migration.


## Facility lookup now works locally

The default source is a compact OpenStreetMap snapshot bundled with the app (map data dated **25 October 2026**). Prepare site context no longer waits for public Overpass servers or their cooldown. It covers KL/Selangor and the surrounding 3 km circles. The snapshot date/source are shown beside the results. Map tiles and address search still use the internet.

After updating, stop the app with Ctrl+C and run `.\start.cmd` once. The compact snapshot is included when cloning/copying the code; no large OSM download or additional data service is required to run it. The counting rules remain a research preview pending training-data validation.


## Generate an estimate

Save the site → **Prepare site context** → **Generate experimental estimate**. The output appears below the map and is saved to site history. It shows the total planned charging points. Editing the pin or inputs clears the current result; past snapshots stay in history.

Estimates remain **experimental** because live POI counting rules are not yet verified against training. The original model is checked against saved test outputs. To update, restart with start.cmd (applies migration 0006). Setup installs the required model dependencies. On another computer, separately copy the trusted evaluated_pipeline.joblib into model/verified_rf80_cv5; model binaries are excluded from Git. Never replace it with the default deployment candidate.

## Current estimator

Uses the verified 1 km Random Forest with eight nearby-facility counts, host category and state. EV registrations are reserved for the trends dashboard. Estimates are research guidance. See [results](RESULTS.md) and [backlog](BACKLOG.md).
>>>>>>> Stashed changes
