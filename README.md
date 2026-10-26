# CastraVolt

CastraVolt helps planners estimate how many EV charging points a proposed site may need in Kuala Lumpur and Selangor. It also shows monthly EV registration trends.

Built with React, TypeScript, FastAPI and PostgreSQL. Currently under development; the workspace preview is available, while accounts and predictions are planned for later stages.

## First-time setup

Install **uv**, **Node.js 22.12+** and **Docker Desktop**. Then run this once from the project folder:

```powershell
.\setup.cmd
```

This prepares Python 3.12, installs dependencies and creates `.env` with a random local database password. Existing `.env` settings are kept unchanged.

## Start the project

Open Docker Desktop, wait for its engine to start, then run:

```powershell
.\start.cmd
```

It starts PostgreSQL, applies migrations, and runs the backend and frontend together. Keep that terminal open and visit [CastraVolt](http://127.0.0.1:5173).

## Stop

Press **Ctrl+C** in the same terminal. App services stop and database data is preserved. A database already running before this command is left running.

If startup fails, follow the terminal message. Service logs are in `tmp/dev-backend.log` and `tmp/dev-frontend.log`. Stop older previews first if ports 8000 or 5173 are already in use.

For tests, model verification and technical details, see [Development notes](docs/DEVELOPMENT.md).
