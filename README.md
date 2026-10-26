# CastraVolt

CastraVolt helps planners estimate how many EV charging points a proposed site may need in Kuala Lumpur and Selangor. It also shows monthly EV registration trends.

Built with React, TypeScript, FastAPI and PostgreSQL. Currently under development; the workspace preview is available, while accounts and predictions are planned for later stages.

## First-time setup

Install Python 3.12+, uv, Node.js 22.12+ and Docker Desktop. Open a terminal in this project folder.

```powershell
Copy-Item .env.example .env
uv sync --locked
npm.cmd ci --prefix frontend
```

Open `.env`, choose a local database password, and use it in both `POSTGRES_PASSWORD` and `CASTRAVOLT_DATABASE_URL`. URL-encode reserved characters in the connection URL if needed.

## Start the project

Open Docker Desktop and wait for its engine to start.

**Terminal 1 — database and backend:**

```powershell
docker compose up -d db --wait
uv run alembic upgrade head
uv run castravolt
```

**Terminal 2 — frontend** (also from the project folder):

```powershell
npm.cmd run dev --prefix frontend
```

Open [CastraVolt](http://127.0.0.1:5173). Backend documentation: [API docs](http://127.0.0.1:8000/docs).

## Stop

Press `Ctrl+C` in both terminals. To stop the database without deleting its data:

```powershell
docker compose down
```

For tests, model verification and technical details, see [Development notes](docs/DEVELOPMENT.md).
