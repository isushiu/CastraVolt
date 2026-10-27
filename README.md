# CastraVolt

CastraVolt helps planners estimate the total EV charging points for a proposed site in Kuala Lumpur or Selangor. It also displays monthly EV registration trends.

Built with React, TypeScript, FastAPI and PostgreSQL. Internal login, projects, map/address selection and saved sites are available. Research model estimates and saved history are available; the trends dashboard is under development.

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
