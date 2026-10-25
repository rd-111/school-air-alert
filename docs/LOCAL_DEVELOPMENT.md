# Local development

This guide starts the frontend and backend on one computer. The backend uses
temporary in-memory repositories for local testing; the frontend can run with
illustrative demo data or request a live Open-Meteo forecast through the API.
Neither mode verifies AWS deployment or real notification delivery.

## Prerequisites

- Git
- Python 3.12
- Node.js 22.12 or newer and npm
- Internet access for package installation and live Open-Meteo requests

The frontend lockfile is `frontend/package-lock.json`; use `npm ci` for a
reproducible install. The backend reads settings from process environment
variables and does not automatically load `backend/.env`.

## Clone and prepare dependencies

```sh
git clone https://github.com/rd-111/school-air-alert.git
cd school-air-alert
```

### Linux or macOS

```sh
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
cd ../frontend
npm ci
```

### Windows PowerShell

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
cd ..\frontend
npm ci
```

If PowerShell blocks activation, use a terminal with an approved local script
policy or run the virtual environment's Python directly:
`..\backend\.venv\Scripts\python.exe -m pip ...` (from the repository root).
Do not lower a machine-wide security policy just for this project.

## Configure local mode

The local backend should use memory repositories. Set `USE_MEMORY_DB=true` in
the process that starts Uvicorn.

Linux/macOS:

```sh
export USE_MEMORY_DB=true
```

PowerShell:

```powershell
$env:USE_MEMORY_DB = "true"
```

Copy `frontend/.env.example` to `frontend/.env` if you want to set frontend
mode explicitly. For live mode, use these public, non-secret settings:

```dotenv
VITE_DATA_MODE=live
VITE_API_URL=http://localhost:8017
```

For demo mode use `VITE_DATA_MODE=demo`. The mock dashboard data is illustrative
and must not be described as live. Never place a backend secret, NASA key,
Telegram token, or AWS credential in a `VITE_` variable. Backend `.env.example`
documents variable names; setting `backend/.env` alone does not load them.

## Start the application

Open two terminals at the repository root.

**Terminal 1 — backend:**

```sh
cd backend
source .venv/bin/activate
export USE_MEMORY_DB=true
python -m uvicorn app.main:app --reload --port 8017
```

On PowerShell, activate with `..\.venv\Scripts\Activate.ps1` after changing
to `backend`, then set `$env:USE_MEMORY_DB = "true"` and run the same Uvicorn
module command.

**Terminal 2 — frontend:**

```sh
cd frontend
npm run dev -- --port 5174
```

Open `http://localhost:5174`. The API base is `http://localhost:8017` and the
health endpoint is `http://localhost:8017/api/v1/health`. FastAPI docs are at
`http://localhost:8017/docs`. Use `http://127.0.0.1:5174` if desired; both
localhost forms on Vite ports 5173–5175 are in the default local CORS allowlist.

In demo mode, the dashboard uses frontend sample data. In live mode, the
backend's in-memory school list includes the fictional `Demo School`; newly
registered records last only while that backend process remains running.
Forecast calls in live mode need internet access to Open-Meteo. No key is
needed for the forecast API.

## Run checks

Backend, from `backend/` with its virtual environment active:

```sh
python -m pytest -q
ruff check .
```

Frontend, from `frontend/`:

```sh
npm test -- --run
npm run build
```

The project has previously seen an intermittent synchronous Starlette
TestClient/AnyIO hang. Its exact cause is unknown. If it recurs, capture the
specific failing test and output; do not skip it to report a full pass.

## Troubleshooting

- **`python3.12` or `py -3.12` is missing:** install Python 3.12 for your OS;
  do not change the system Python used by other projects.
- **`npm ci` says no lockfile:** run it from `frontend/`, where the committed
  `package-lock.json` lives. Confirm Node is 22.12 or newer with `node --version`.
- **Port 8017 is busy:** choose another backend port, such as 8020, and set
  `VITE_API_URL` to that same backend origin before restarting Vite.
- **The live dashboard cannot connect:** verify `/api/v1/health`, `VITE_DATA_MODE=live`,
  and the matching `VITE_API_URL`; restart both processes after changing env.
- **CORS error:** open the exact Vite origin printed in its terminal. For a
  different origin, configure the backend `CORS_ORIGINS` as comma-separated
  exact origins; do not use `*`.
- **Forecast provider error:** check internet access and the backend response.
  The frontend must show an error in live mode rather than claim mock data is
  live. Demo mode can still be used for UI walkthroughs.
- **FIRMS says unconfigured:** optional live hint needs a valid
  backend-only `FIRMS_MAP_KEY`. Do not put it in the frontend or commit it.
- **Email, Telegram, AWS schedules, or report history are unavailable:** local
  memory mode does not provide persistent AWS storage, SNS delivery, or a
  deployed webhook. See `docs/DEPLOYMENT.md`; no live delivery is implied.
