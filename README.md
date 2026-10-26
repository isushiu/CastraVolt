# CastraVolt

CastraVolt helps planners estimate the total EV charging points for a proposed site in Kuala Lumpur or Selangor. It also displays monthly EV registration trends.

Built with React, TypeScript, FastAPI and PostgreSQL. Currently under development.

## Requirements

Install these on the computer running the project:

- [uv](https://docs.astral.sh/uv/getting-started/installation/) — manages Python and backend dependencies.
- [Node.js 22.12+](https://nodejs.org/en/download) — includes npm.
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) — runs PostgreSQL. On Linux, Docker Engine with Compose also works.

Open a terminal in the project folder. Reopen the terminal after installing tools.

## 1. Check your computer

```powershell
.\check.cmd
```

This checks the required tools and Docker engine. If Docker is installed but stopped, open Docker Desktop and wait for its engine to run.

## 2. First-time setup

```powershell
.\setup.cmd
```

Setup installs dependencies and creates `.env` with matching random database credentials. Existing `.env` settings are preserved. Stop any running CastraVolt preview before running setup again.

## 3. Start

With Docker running:

```powershell
.\start.cmd
```

This starts PostgreSQL, applies migrations, and launches the backend and frontend together.

Open [CastraVolt](http://127.0.0.1:5173/). Keep the terminal open; press **Ctrl+C** to stop the app. Database data is preserved. A database already running before startup is left running.

After the first setup, you normally only need to open Docker and run `.\start.cmd`.

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
