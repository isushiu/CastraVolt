# CastraVolt

Urban EV infrastructure planning for Kuala Lumpur and Selangor.

## Current state

Stage 1 foundation: React/TypeScript Midnight Iris workspace shell, typed FastAPI connection, health/readiness endpoints, bounded PostgreSQL engine configuration, initial Alembic baseline and local Compose configuration. Accounts, real private projects, map extraction and prediction endpoints arrive in later stages. Preview pages explicitly identify unfinished features and do not invent project/model results.

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

