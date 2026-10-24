# School Air Alert

A responsive school dashboard for hourly PM2.5 forecast decision support.
It shows GREEN/YELLOW/RED project-policy labels, hourly values, and the lowest
and highest forecast windows during school hours. It does not guarantee safety
or provide medical advice.

## Architecture and status

- Frontend: JavaScript, React 18, Vite, React Router, Recharts, plain responsive CSS.
- Backend: Python 3.12, FastAPI, Pydantic, and Mangum Lambda adapter.
- Deployment architecture (defined, not deployed): Amplify Hosting, API Gateway
  HTTP API, Lambda, DynamoDB, EventBridge Scheduler, and SNS. Telegram uses its
  HTTPS Bot API; Bedrock messages are optional.
- Live provider: Open-Meteo Air Quality API using CAMS Global forecast data.
- Daily processing: a 06:00 Asia/Kolkata SAM schedule runs the school forecast,
  writes an idempotent History row, and attempts regular and stricter sensitive
  SNS notifications independently for each school.
- Evening processing: a separate 19:00 Asia/Kolkata schedule requests a
  two-day forecast, selects tomorrow's local school hours, and sends a
  tomorrow-labelled alert. Notification-run claims reduce duplicate sends.
  This is implemented locally but has not been deployed or verified against
  EventBridge, DynamoDB, SNS, or Telegram.
- Versioned school endpoints provide school listing/registration, email
  subscription requests, current forecast status, and up to 90 days of saved
  forecast history.
- The frontend also includes school forms, a forecast-history report, and a
  print-ready notice poster.
- The dashboard defaults to clearly labelled demo data. Live forecast mode is
  available through the backend API.
- `template.yaml` defines the HTTP API, school/history/notification-run tables,
  and morning/evening schedules. It has not been validated with SAM or deployed
  to AWS.

## Requirements

- Python 3.12
- Node.js 22.12 or newer and npm (required by the configured Vite/Vitest versions)

## Local setup

Install backend dependencies in a Python 3.12 virtual environment using the
repository requirements files, then run:

```sh
cd backend
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
USE_MEMORY_DB=true python -m uvicorn app.main:app --reload --port 8017
```

In another terminal:

```sh
cd frontend
npm ci
npm run dev
```

Open the local Vite URL printed by the dev server. The default mode is demo.

## Demo and live forecast modes

Copy `frontend/.env.example` to `frontend/.env` for local changes. Keep
`VITE_DATA_MODE=demo` for illustrative data. To request live provider forecasts,
set:

```text
VITE_DATA_MODE=live
VITE_API_URL=http://localhost:8017
```

Vite variables are public browser configuration; do not put secrets in them.
Live mode never silently falls back to demo data. The location form accepts
latitude and longitude; Mumbai is only the displayed example/default.
The public Telegram link is configured with
`VITE_TELEGRAM_BOT_USERNAME=schoolalert11_bot` to show it on the dashboard.
This is public configuration; never use the bot token there. Seeing the link
does not verify webhook configuration or message delivery.

The backend accepts:

```text
GET /api/v1/forecast?latitude=19.0760&longitude=72.8777
GET /api/v1/health
GET /api/v1/schools
POST /api/v1/schools
POST /api/v1/subscribe
GET /api/v1/status?school_id=...
GET /api/v1/history?school_id=...&days=30
GET /api/v1/schools/<school_id>/smoke-hint
```

The forecast response identifies `data_type: forecast`, reports the retrieval
timestamp and source, and uses the configured school-hours policy. The default
school period is 07:00–14:00 local time, following the current F1 requirements.

Backend environment values are listed in `backend/.env.example`. Configure
`CORS_ORIGINS` to a comma-separated allowlist containing the exact local or
Amplify website origins. For local job/repository development, set
`USE_MEMORY_DB=true`; it uses an in-memory demo school with no SNS topics, so it
does not send notifications. Provider requests have a ten-second timeout, one
retry, and a short in-process per-location/day-count cache. Old or incomplete
forecasts are marked UNKNOWN; live mode does not silently substitute mock data.
The backend reads settings from its process environment; it does not load a
`backend/.env` file automatically.

The optional F20 satellite context uses a registered school's saved
coordinates. The backend queries NASA FIRMS for a bounded area, filters NOAA-21
VIIRS NRT rows to the last 24 hours and configured radius, removes exact
duplicate pixels, and groups overlapping scan/track footprints within the same
platform and acquisition minute. The radius defaults to 25 km
(`FIRMS_SEARCH_RADIUS_KM`, maximum 100 km); it is a search boundary, not a
plume radius. The browser never receives the FIRMS key. Request a free key
from [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/api/map_key/) and set
`FIRMS_MAP_KEY` only in the backend environment. Without it, the hint reports
that it is unconfigured and the forecast continues normally.

For detected clusters, the backend optionally requests modeled 10 m wind at
each cluster's location and acquisition time through the [Open-Meteo
Historical Forecast API](https://open-meteo.com/en/docs/historical-forecast-api).
Wind direction is treated as the direction it comes from; vector components
are interpolated between adjacent hourly records. Missing or incomplete wind
produces an indeterminate hint. A modeled vector pointing toward the school
can show this interim wording: “Nearby fire detections may indicate a
potential smoke transport risk. Satellite detections and modeled wind do not
confirm smoke exposure at this school.” This is not a plume or exposure model.
The modeled wind response is cached briefly using the backend's existing
`FIRMS_CACHE_TTL_SECONDS` setting.
The original “Smoke from nearby fires is likely contributing” causal message
is not shown. NASA FIRMS hotspots are satellite indicators, not ground-level
measurements or confirmation of smoke at school.

Open-Meteo's free service is for non-commercial use, is rate limited, has no
uptime guarantee, and requires CC BY attribution. Both services are optional;
live access and data availability have not been verified as part of deployment.

For a local check, open a backend terminal, enter the key without echoing it,
and start the API:

```sh
cd backend
read -rsp "NASA FIRMS MAP_KEY: " FIRMS_MAP_KEY
printf '\n'
export FIRMS_MAP_KEY FIRMS_SEARCH_RADIUS_KM=25 USE_MEMORY_DB=true
.venv/bin/python -m uvicorn app.main:app --reload --port 8017
```

Then request the in-memory demo school's hint from another terminal:

```sh
curl -s http://localhost:8017/api/v1/schools/demo-school/smoke-hint
```

In the frontend terminal use live mode (`VITE_DATA_MODE=live` and
`VITE_API_URL=http://localhost:8017`) and open the selected demo school's
dashboard. The demo school has illustrative coordinates; for a real school,
register its actual location first. Without a MAP_KEY the API returns
`unconfigured`; do not use the example placeholder as a real key.

School SNS topics are created with names beginning
`school-air-alert-<school-id>-` so the SAM policy limits publishing and topic
management to this application's topic name prefix. Email subscriptions remain
pending until the recipient confirms through SNS.

Telegram webhook configuration uses `TELEGRAM_TOKEN` and `TELEGRAM_SECRET`.
The SAM template marks both deployment parameters as `NoEcho`; do not put their
values in Git. The webhook requires the `X-Telegram-Bot-Api-Secret-Token` header.
Supported bot commands are `/start`, `/schools`, `/subscribe <school_id>`,
`/sensitive on|off`, `/today`, and `/stop`. Telegram and SNS delivery have not
been verified against live services.

Optional AI message generation uses `BEDROCK_MODEL`. For SAM, provide both the
model identifier and its exact permitted ARN; when no model is configured,
messages use the deterministic template. Bedrock calls have not been run.

## Provider and attribution

The backend requests `hourly=pm2_5`, one forecast day, India time, and the CAMS
global domain. See [Open-Meteo Air Quality API documentation](https://open-meteo.com/en/docs/air-quality-api).
The response credits Open-Meteo and CAMS, links to both sources, and reports
CC BY 4.0. The public free API is for non-commercial use and has request limits;
check the [Open-Meteo terms](https://open-meteo.com/en/terms) before use. CAMS
Global is a forecast model (about 45 km resolution with native three-hourly
updates), not a school-site sensor or real-time observation.

## Classification

Defaults preserve the prototype's regular thresholds (GREEN ≤60, YELLOW ≤120,
otherwise RED) and sensitive thresholds (GREEN ≤40, YELLOW ≤90, otherwise RED)
in µg/m³. They are placeholders for hourly school decision support, not official
CPCB AQI categories. See [threshold documentation](docs/thresholds.md).
The activity panel gives general policy guidance only: incomplete forecasts
receive no recommendation, RED requests school-policy review, and other
statuses defer to school policy. It does not invent different numeric rules for
PE, sports, recess, assemblies, or bus waiting.

## F19–F21 status

- **F19 forecast accuracy indicator: implemented; accuracy remains unmeasured.**
  The dashboard says historical validation data is unavailable and explains
  that a model forecast is not a school-site measurement. In live mode it also
  shows the provider, retrieval timestamp, and displayed forecast-hour count
  when supplied by the existing response. These details do not imply accuracy
  or confidence. A forecast archive or reanalysis product is not an approved
  authoritative observation source; select an observed dataset,
  station-matching method, and date-alignment rules before validating results.
- **F20 smoke-source hint: partially implemented.** Optional nearby NOAA-21
  VIIRS NRT detections are grouped by reported pixel footprints and matched to
  Open-Meteo modeled historical wind at their location/time. The interim
  possible-transport wording is shown only when the modeled vector points
  toward the school. The original causal smoke-contribution message remains
  blocked; model adequacy, plume uncertainty, and observed attribution remain
  unresolved. Neither provider's live availability is deployment-verified.
- **F21 evening alert: implemented locally, infrastructure unverified.** The
  19:00 IST event requests `forecast_days=2`, selects tomorrow in Asia/Kolkata,
  labels the message as tomorrow, and does not write another same-day History
  row. EventBridge/DynamoDB/SNS/Telegram behavior still needs deployment-level
  verification.

The remaining F19 accuracy-validation and F20 model-adequacy, plume, and
attribution decisions are listed in
[`docs/pending-decisions.md`](docs/pending-decisions.md). No accuracy score or
smoke-contribution message is displayed.

Notification claims reduce duplicate retries. If an external publish succeeds
but its response times out, the outcome is uncertain; live delivery semantics
are not verified.

## Checks

```sh
cd backend
python -m pytest -q
ruff check .
cd ../frontend
npm test -- --run
npm run build
```

The full backend suite passed locally with **94 passed** on 2026-10-11. In a
restricted execution sandbox, synchronous Starlette `TestClient` requests may
hang because the sandbox denies asyncio's Unix socketpair wakeup send with
`EPERM`. This is an environment restriction; the same seven route tests and
the full suite passed when run outside that sandbox. Do not exclude those tests.

Use Node.js 22.12 or newer. `npm ci` uses the committed
`frontend/package-lock.json`. CI is configured for Python 3.12 and Node 22.12;
no remote CI run is claimed here.

Provider, SNS, Telegram, and Bedrock network calls are mocked in tests. Live
forecast mode itself needs a working internet connection and the backend.

SAM validation/build commands (not run here):

```sh
sam validate --lint --template-file template.yaml
sam build --template-file template.yaml
```

The SAM CLI is not installed in the current environment, so these local
template checks remain to be run. YAML syntax parsing alone does not establish
that the template will deploy.

Deployment is not verified. Only after reviewing the template, supplying
approved parameters, and explicitly authorizing deployment should you run
`sam deploy --guided`.

## Troubleshooting

- **CORS in the browser:** run the backend on the URL in `VITE_API_URL`, and
  open the Vite origin shown in its terminal. The backend allows ports 5173,
  5174, and 5175 on `localhost` and `127.0.0.1`. For another frontend origin,
  set `CORS_ORIGINS` to a comma-separated list of exact origins, restart the
  backend, and do not use `*`.
- **Live mode says the forecast could not load:** in `frontend/.env`, check
  `VITE_DATA_MODE=live` and `VITE_API_URL=http://localhost:8017` (or the
  backend's selected port), then restart Vite. Check
  `http://localhost:8017/api/v1/health` and the forecast URL below. Live mode
  requires internet access to Open-Meteo; provider errors are shown instead of
  silently switching to demo data.
- **Missing configuration:** compare local values with `frontend/.env.example`
  and `backend/.env.example`. Keep tokens and credentials only in local or
  deployment secret configuration; never copy them into Vite variables.
- **Port is already in use:** inspect it with `ss -ltnp` or `lsof -i :8017`.
  Do not stop a process you do not recognize. You can start FastAPI on another
  port, for example `python -m uvicorn app.main:app --reload --port 8017`, and
  set `VITE_API_URL=http://localhost:8017` before restarting Vite.
- **Backend tests appear to hang:** in a restricted execution sandbox, asyncio's
  cross-thread socketpair wakeup can be denied with `EPERM`, leaving Starlette
  `TestClient` waiting for a callback. The full suite passed when run outside
  that sandbox: `python -m pytest -q` (94 passed). Run the command from the
  backend directory in a normal local terminal rather than filtering tests.

## Teammate smoke-test guide

Run the backend and frontend in separate terminals using the setup above. In
default demo mode, check the dashboard, language selector, hourly chart,
activity guidance, report, poster, and location form without AWS credentials.
The poster route accepts `?school_id=<id>` and its Print button opens the
browser print dialog. For live mode, configure `VITE_DATA_MODE=live` and
`VITE_API_URL`, then query the forecast endpoint above with valid coordinates;
confirm it identifies forecast data and includes its source/retrieval time.

School registration and subscriptions can be exercised with the local
memory-backed backend, but it is not persistent and does not deliver email.
Telegram and SNS delivery require external configuration and credentials and
are not verified. Bedrock is optional; without a model setting, the deterministic
template is used. Keep secrets out of frontend variables and use no real student
or parent information in demos.

## Known limitations

- Authentication, email unsubscribe management, and live Telegram/SNS delivery
  have not been implemented or verified. Telegram `/stop` removes bot
  subscriptions; SNS email subscribers can use SNS's confirmation/unsubscribe
  flow.
- School recommendations use a simplified placeholder policy and incomplete
  forecast hours may limit window selection.
- Coordinates are entered manually; no geocoding or maps provider is used.
- API caching is process-local, so separate Lambda instances do not share it.
- AWS deployment and production CORS origins have not been verified.
- DynamoDB/SNS integration tests use mocks; no AWS account was accessed.
- F19 accuracy comparison remains unavailable pending authoritative
  observations. F20 combines optional nearby satellite detections with modeled
  wind and pixel grouping, but cannot establish plume transport or smoke
  exposure. Its original causal attribution claim remains pending.
