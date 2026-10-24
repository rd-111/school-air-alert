# School Air Alert — Manual Live-Data Testing Guide

This guide maps F1–F21 to the implementation currently in the repository. It
separates local UI/API checks from live provider checks and deployed AWS
verification. A successful local test or mocked provider test does not prove
that a live provider, notification, schedule, or deployment is working.

## Before testing

### Local app startup

Use Python 3.12 and Node.js 22.12 or newer. The backend reads process
environment variables; it does not automatically load `backend/.env`.

Terminal 1, from the repository root:

```sh
cd backend
source .venv/bin/activate
export USE_MEMORY_DB=true
python -m uvicorn app.main:app --reload --port 8017
```

Terminal 2:

```sh
cd frontend
VITE_DATA_MODE=live VITE_API_URL=http://localhost:8017 npm run dev -- --port 5174
```

Open the Vite URL printed in Terminal 2. To use the dashboard demo instead,
set `VITE_DATA_MODE=demo` (or omit it); demo readings are illustrative and are
not provider data. `USE_MEMORY_DB=true` creates a temporary in-memory demo
school. Its records disappear when the backend process restarts, and it does
not create SNS topics or deliver email.

Check that the API process responds:

```sh
curl -i http://localhost:8017/api/v1/health
```

Expected: HTTP 200 and `{"status":"ok"}`. This only checks that the API is
running; it does not check Open-Meteo, AWS, or notifications.

### Configuration checklist

Variable names below are public configuration names, not secret values.

| Variable | Needed for |
|---|---|
| `VITE_DATA_MODE`, `VITE_API_URL` | Frontend demo/live selection and backend base URL |
| `VITE_TELEGRAM_BOT_USERNAME` | Public Telegram link shown by the UI; never put a bot token in a `VITE_` variable |
| `USE_MEMORY_DB` | Local in-memory demo repositories; use `true` locally, `false` for persistent deployment |
| `CORS_ORIGINS` | Exact allowed browser origins; include the deployed frontend origin in production |
| `AWS_REGION`, `SCHOOLS_TABLE`, `SUBSCRIBERS_TABLE`, `HISTORY_TABLE`, `NOTIFICATION_RUNS_TABLE` | Deployed DynamoDB/SNS/Lambda operations |
| `FIRMS_MAP_KEY`, `FIRMS_SEARCH_RADIUS_KM`, `FIRMS_CACHE_TTL_SECONDS` | Optional backend-only NASA FIRMS context; Open-Meteo wind needs no key |
| `TELEGRAM_TOKEN`, `TELEGRAM_SECRET` | Telegram Bot API sends and authenticated webhook |
| `BEDROCK_MODEL` | Optional Bedrock message generation; also needs deployed IAM permission for the selected model |
| `FORECAST_CACHE_TTL_SECONDS`, `PM25_GREEN_MAX`, `PM25_YELLOW_MAX`, `PM25_SENSITIVE_GREEN_MAX`, `PM25_SENSITIVE_YELLOW_MAX` | Forecast cache and classification configuration |

Keep actual credentials in local secret configuration or an approved AWS
secret/parameter mechanism. Never put them in source control, screenshots,
terminal transcripts, or frontend variables. NASA FIRMS requires a valid
MAP_KEY for live requests. Open-Meteo Air Quality and Historical Forecast APIs
need no API key; public service terms/rate limits apply. Check the provider
terms before use.

## Feature-by-feature checks

### F1 — Air forecast fetch and parse

- **Status / UI / API:** implemented. Dashboard `/` (hourly chart and readings); `GET /api/v1/forecast?latitude=19.0760&longitude=72.8777`.
- **Data / provider / config:** live hourly forecast from Open-Meteo Air Quality API, CAMS Global; no provider key. Demo mode instead uses local illustrative data.
- **Manual test:** with the backend running and `VITE_DATA_MODE=live`, load `/` or run the curl request above. Inspect JSON `data_type`, `hourly`, `source`, `retrieved_at`, and `stale`. Compare the response timestamp and source links with the selected coordinates. The frontend should show its Live label and provider attribution. A recent timestamp means the backend retrieved/cached a model forecast; it is not a real-time sensor observation.
- **Negative / verification boundary:** try latitude 91 or longitude 181; expect a validation error (normally HTTP 422). Provider rejection/unavailability returns a structured upstream error (502); timeout returns 504. Missing hourly readings can produce `UNKNOWN`/incomplete forecast status. The endpoint is live-testable locally with internet access; this project does not claim live-provider verification from this guide.

### F2 — PM2.5 status classification

- **Status / UI / API:** classification service implemented; shown in the dashboard status card and forecast response `school_hours_summary.status`. There is no standalone classification endpoint.
- **Data / provider / config:** deterministic local calculation over PM2.5 forecast values; limits may be configured with the four `PM25_*` variables above. Defaults are prototype policy bands, not official CPCB AQI categories.
- **Manual test:** fetch a live forecast and compare `average_pm25` and status to the configured regular thresholds. For boundary behavior, run the existing backend classifier tests (`cd backend && python -m pytest -q tests/test_classify.py`) rather than trying to force a provider to emit an exact value.
- **Negative / verification boundary:** incomplete input must not be treated as GREEN; expect `UNKNOWN` in forecast assembly when required readings are missing. Live display can be checked locally, but exact boundary verification is deterministic/local, not live-provider verification. Threshold authority remains a documented limitation.

### F3 — Daily scheduled alert processing

- **Status / UI / API:** locally implemented handler; no user-facing page or HTTP trigger. AWS resource is `DailyCheckFunction` in `template.yaml`, scheduled daily at 06:00 Asia/Kolkata.
- **Data / provider / config:** scheduled processing reads school records, fetches Open-Meteo forecast data, and uses DynamoDB/SNS/Telegram integrations when configured. Needs deployed tables, `AWS_REGION`, table names, appropriate IAM, and live notification configuration.
- **Manual test:** only in a deployed environment, inspect the EventBridge Scheduler schedule and target, then check the Lambda invocation/CloudWatch logs after the next 06:00 IST run. Confirm a per-school outcome, forecast date, History row, and actual recipient delivery independently. A manually invoked Lambda can test processing but does not prove the schedule fired.
- **Negative / verification boundary:** check logs for a failed school and confirm later schools still process; provider failure should not generate a successful alert. Local memory mode loses history on process exit and has no SNS topics, so it cannot verify scheduled persistence or delivery. AWS schedule and delivery are currently unverified.

### F4 — Email alerts via Amazon SNS

- **Status / UI / API:** publishing service implemented locally; no direct page to send a test alert. School creation/subscription use `POST /api/v1/schools` and `POST /api/v1/subscribe`; scheduled publishing is in F3/F21.
- **Data / provider / config:** AWS SNS topics (regular and sensitive), DynamoDB school records, deployed IAM permissions and `AWS_REGION`; no browser credential.
- **Manual test:** in the deployed live app, register a test school, subscribe a mailbox, click the SNS confirmation link, then allow the next scheduled alert. Verify the confirmation and delivered message at the mailbox and SNS/Lambda logs. A pending-confirmation response alone is not delivery.
- **Negative / verification boundary:** invalid email or unknown school should return a structured validation/404 error. Missing topics or SNS permission should fail the send without stopping other schools. Local `USE_MEMORY_DB=true` returns demo-only subscription status and sends no email. Real SNS delivery is not verified.

### F5 — Alert history log

- **Status / UI / API:** locally implemented. Visible through report `/report` and `GET /api/v1/history?school_id=<id>&days=30`; daily processing writes history.
- **Data / provider / config:** DynamoDB `History` table in deployment; in-memory repository during local demo. No separate external data provider; records contain forecasts, not observed air quality.
- **Manual test:** with a deployed school and schedule, inspect the History row for school/date and then call the history endpoint. Confirm `avg`, `peak`, status, and windows match the successful daily run. Repeat/run a retry for the same school/date and confirm only one row for that date.
- **Negative / verification boundary:** unknown school returns 404; empty history returns zero counts and an empty list; `days` must be 1 or greater and is capped at 90. Local memory history disappears on restart. DynamoDB persistence/idempotency require AWS and are not deployment-verified.

### F6 — Activity planner

- **Status / UI / API:** implemented in the dashboard Activity Windows section and forecast recommendations; `GET /api/v1/forecast?...` exposes `recommendations.best_window`, `worst_window`, and `no_suitable_window`.
- **Data / provider / config:** calculated locally from hourly forecast values, usually live Open-Meteo in live mode. No additional variable.
- **Manual test:** load a live forecast and compare the displayed best/worst windows with the hourly values in the same response. Confirm the selected intervals correspond to the lowest/highest contiguous forecast period.
- **Negative / verification boundary:** missing or insufficient contiguous hours can leave a window unset and show no-suitable/incomplete guidance. These are forecast-based decision aids, not guarantees of safety. Locally testable; no AWS required.

### F7 — Sensitive-student mode

- **Status / UI / API:** implemented in email subscription checkbox, Telegram `/sensitive on|off`, and separate regular/sensitive scheduled message paths. No dedicated status API for the preference.
- **Data / provider / config:** sensitivity boolean stored with subscriber records (DynamoDB when deployed; memory locally); forecast values from Open-Meteo; threshold variables `PM25_SENSITIVE_GREEN_MAX` and `PM25_SENSITIVE_YELLOW_MAX`.
- **Manual test:** register a live school, subscribe one test recipient with the sensitive checkbox and another without, confirm SNS subscriptions, then observe a scheduled alert whose school-hour average falls between the normal and sensitive thresholds. Compare the two message statuses and language. For Telegram, subscribe and issue `/sensitive on`, then `/today`.
- **Negative / verification boundary:** invalid/missing readings should not become GREEN. Invalid subscription input should be rejected. Local classification tests cover boundaries, but in-memory mode cannot verify actual recipient delivery. Sensitive policy thresholds remain placeholders, not government categories.

### F8 — School registration and email subscription API

- **Status / UI / API:** locally implemented. Dashboard School tools form; `GET /api/v1/schools`, `POST /api/v1/schools`, and `POST /api/v1/subscribe`.
- **Data / provider / config:** live persistence uses DynamoDB; school topic creation/subscription uses SNS. Needs table names, AWS region, IAM, and confirmed email for live delivery. Local memory mode is temporary and creates no SNS topics.
- **Manual test:** in local mode, create a test school with valid name, coordinates, and language, then choose it from the selector. Subscribe an email; expect the UI to identify the action as demo-only. In a deployed environment repeat with a test mailbox; expect `pending_confirmation`, receive the SNS email, and confirm.
- **Negative / verification boundary:** try name shorter than 3 characters, out-of-range coordinates, unsupported language, malformed email, and nonexistent school ID. Expect structured validation/404 errors and no saved invalid record. AWS topic creation, persistence, and confirmation require deployment.

### F9 — School status and history API

- **Status / UI / API:** implemented. Dashboard school selector and report; `GET /api/v1/status?school_id=<id>` and `GET /api/v1/history?school_id=<id>&days=30`.
- **Data / provider / config:** status combines latest saved History with a current Open-Meteo forecast; history comes from DynamoDB or in-memory repository. Needs a registered school; persistent history needs AWS table configuration.
- **Manual test:** select a registered school or call both endpoints. Compare status's hourly/source/retrieval fields to the forecast endpoint and compare history counts to its `daily` entries. Populate history by a successful daily run in a deployed environment.
- **Negative / verification boundary:** unknown school returns 404; empty history returns zero counts. Invalid `days` below 1 is rejected; values above 90 are capped in service logic. In-memory history is temporary, and live persistence needs AWS.

### F10 — Telegram bot

- **Status / UI / API:** webhook and command handling implemented locally; UI provides a public bot link. Webhook is `POST /api/v1/telegram` and requires `X-Telegram-Bot-Api-Secret-Token`.
- **Data / provider / config:** Telegram Bot API; backend-only `TELEGRAM_TOKEN` and `TELEGRAM_SECRET`, plus public `VITE_TELEGRAM_BOT_USERNAME`. Telegram subscriber records use the configured repository. Requires an HTTPS deployed webhook URL for real Telegram updates.
- **Manual test:** set a new/valid bot token and webhook secret only in backend/deployment secret configuration. Configure Telegram's webhook to the deployed `/api/v1/telegram` URL with the same secret header. Message the bot `/start`, `/schools`, `/subscribe <school_id>`, `/sensitive on`, `/today`, `/sensitive off`, and `/stop`; confirm replies and subscription state.
- **Negative / verification boundary:** missing/wrong secret should return 403; missing bot config returns 503; unavailable send should be logged safely and not expose tokens. A link in the UI does not prove webhook or delivery works. Real Telegram requires deployment and credentials; not verified.

### F11 — Website dashboard

- **Status / UI / API:** implemented. Frontend route `/`; components include `DashboardPage`, `StatusCard`, `HourlyForecastChart`, `HourlyReadings`, `ActivityWindows`, `ActivityAdvice`, `SchoolForms`, `TelegramLink`, and `SmokeHint`. Forecast API is `GET /api/v1/forecast`.
- **Data / provider / config:** demo mode uses `frontend/src/api/mockData.js`; live mode calls the configured API URL and Open-Meteo through the backend. Set `VITE_DATA_MODE=live` and `VITE_API_URL`; no frontend provider secret.
- **Manual test:** open `/` in demo mode and verify the Demo badge; switch to live mode and verify Live badge, source, retrieval time, selected coordinates, hourly chart, status words/icons, windows, and forms. Use language selector for English, Hindi, and Marathi.
- **Negative / verification boundary:** disconnect backend or use a bad API URL and check the error state; enter invalid coordinates and check validation. Live mode must show error rather than silently switching to mock. Local browser testable; API/provider needs internet. Responsive appearance should be checked at narrow mobile and desktop widths.

### F12 — Monthly report card

- **Status / UI / API:** implemented at `/report`; selects a school and calls `GET /api/v1/schools` and `GET /api/v1/history?school_id=<id>&days=30`.
- **Data / provider / config:** forecast History from memory locally or DynamoDB in deployment; no new external provider.
- **Manual test:** open `/report`, select a school, and compare GREEN/YELLOW/RED totals with matching returned `daily` rows. Verify the protected-hours figure is `(yellow + red) × 2` and the text identifies this as forecast history.
- **Negative / verification boundary:** no schools/history should render an empty state; API failure should render an error state. Local memory data is ephemeral. It measures forecast classifications, not actual exposure. AWS needed only for persistent deployed history.

### F13 — Printable notice-board poster

- **Status / UI / API:** implemented at `/poster?school_id=<id>`; calls `GET /api/v1/status?school_id=<id>` in live mode.
- **Data / provider / config:** saved/current forecast status via backend; demo mode supplies illustrative data. No special variable beyond frontend mode/API URL.
- **Manual test:** use `/poster?school_id=demo-school` in demo mode and a real ID in live mode. Confirm school, date, status, best/worst window, and three translated advice lines. Use Print and inspect print preview for one-page layout, legibility, and hidden navigation/buttons.
- **Negative / verification boundary:** omit `school_id` and expect the guidance state; use unknown ID or unavailable backend and expect error. Locally testable; live status needs backend/provider and persistent school data needs AWS.

### F14 — Optional Amazon Bedrock message generation

- **Status / UI / API:** optional daily-message integration implemented with deterministic template fallback; no UI/API switch. Invoked by F3/F21 daily processing when `BEDROCK_MODEL` is configured.
- **Data / provider / config:** Amazon Bedrock Runtime. Needs `BEDROCK_MODEL`, `AWS_REGION`, deployed IAM `bedrock:InvokeModel` permission scoped to the approved model ARN, and a supported model/access in that region. Invocation may incur charges.
- **Manual test:** only after reviewing the model/region and possible cost, configure the model securely and run a test daily invocation in an approved AWS environment. Inspect the resulting message for correct status, supplied facts, language, length, and disclaimer. Then disable the model and confirm deterministic template messages are used.
- **Negative / verification boundary:** empty model setting, model timeout/error, missing status/disclaimer, or overlong output should fall back to template text. No local live Bedrock call is required or claimed; mocked tests do not verify AWS access.

### F15 — Security and privacy

- **Status / UI / API:** cross-cutting safeguards implemented in config, schemas, error handling, CORS, secret handling, and AWS policies; no separate page. Check all `/api/v1` routes, especially registration, subscription, and Telegram webhook.
- **Data / provider / config:** `CORS_ORIGINS`, backend-only integration secrets, DynamoDB/SNS/IAM in deployment. No secret is needed for local validation checks.
- **Manual test:** send an allowed `Origin` header from `http://localhost:5174` to `/api/v1/health`, then an unapproved origin. Confirm only the allowed origin is reflected. Try invalid coordinates, school data, and webhook secret; confirm generic structured errors and no stack trace or secret.
- **Negative / verification boundary:** never use a real parent/student address in a test; use a mailbox you control. Review browser network requests and frontend build config to ensure no private key is sent. IAM, secret storage, and production CORS require deployed review; no AWS security audit is implied here.

### F16 — Reliability and fallbacks

- **Status / UI / API:** implemented fallbacks and per-school isolation in provider, daily, and optional-service paths; visible states appear in dashboard, forecast errors, and smoke hint.
- **Data / provider / config:** Open-Meteo, SNS, Telegram, optional Bedrock/FIRMS; use the corresponding variables above. No added provider is required to test core forecast locally.
- **Manual test:** first confirm live forecast works. Then test optional F20 with FIRMS unconfigured and verify the PM2.5 dashboard still loads. In an isolated local session, make Open-Meteo unavailable (for example, temporarily disconnect network) and request forecast; expect a clear upstream error, not fake data. In a deployed test, inspect a multi-school run where one school/provider/send fails and later schools still process.
- **Negative / verification boundary:** stale/incomplete forecast should be labeled and not become GREEN; failed notification must not be reported delivered. Network disruption is not a deterministic provider-specific test; automated mocked tests provide repeatable failure coverage. Multi-school AWS behavior needs deployment.

### F17 — Tests and CI

- **Status / UI / API:** implemented test suites and GitHub Actions workflow `.github/workflows/test.yml`; no product page or provider.
- **Data / provider / config:** local fixtures/mocks; no live credentials should be needed. CI uses Python 3.12 and Node 22.12, installs backend requirements and frontend from lockfile.
- **Manual test:** from repository root run `cd backend && python -m pytest -q && ruff check .`, then `cd ../frontend && npm ci && npm test -- --run && npm run build`. For remote CI, inspect the workflow run for the actual commit in GitHub Actions.
- **Negative / verification boundary:** failing or hanging tests must remain visible; do not deselect tests to claim a full pass. A local pass does not prove remote CI passed. The project has previously had intermittent TestClient/AnyIO hangs; the precise cause remains unknown.

### F18 — Documentation

- **Status / UI / API:** documentation feature implemented in README and `docs/`; no runtime page or endpoint.
- **Data / provider / config:** static repository content; no provider or environment variable.
- **Manual test:** review `README.md`, `docs/architecture.md`, `docs/thresholds.md`, `docs/DEPLOYMENT.md`, `docs/pending-decisions.md`, and this guide. Compare documented endpoints and variable names with source. Run `git diff --check` after documentation edits.
- **Negative / verification boundary:** search docs for claims that imply live provider, notification, CI, or AWS success and confirm they match evidence. This is a manual documentation check, not an application live-data check.

### F19 — Forecast accuracy meter

- **Status / UI / API:** accuracy calculation is blocked; dashboard `/` shows the unavailable/not-yet-measured forecast reliability state. There is no accuracy endpoint.
- **Data / provider / config:** no approved authoritative observation provider, station matching, date alignment, or scoring definition; no relevant environment variable.
- **Manual test:** load dashboard and verify it says accuracy has not been measured and does not show a fabricated percentage or sample score. Inspect source/retrieval metadata separately; that metadata is not an accuracy score.
- **Negative / verification boundary:** do not use archived forecasts as actual observations. No live accuracy test is possible until the data source and methodology are approved and implemented. F19 is not complete as an accuracy calculation.

### F20 — NASA FIRMS smoke-source hint

- **Status / UI / API:** optional hint implemented locally. Dashboard `SmokeHint` appears under Activity Advice for a selected registered school. Endpoint: `GET /api/v1/schools/<school_id>/smoke-hint`.
- **Data / provider / config:** backend queries NASA FIRMS NOAA-21 VIIRS NRT Area API and Open-Meteo Historical Forecast modeled 10 m wind. Requires backend-only `FIRMS_MAP_KEY`; radius is `FIRMS_SEARCH_RADIUS_KM` (default 25 km). Open-Meteo requires no key. Test with a real registered school coordinate, not illustrative coordinates, when possible.
- **Manual test:** securely configure the FIRMS key in the backend process, restart the backend, switch dashboard to live mode, register/select the school, then inspect the hint and endpoint JSON. Confirm NASA source, search radius, detection UTC times, and retrieval timestamps. If clusters exist, check that `wind_source` identifies modeled Open-Meteo data and each cluster has a wind status. `transport_possible` may show the interim warning; it is a cautious modeled estimate only. It does not confirm a fire is active, smoke transport, or exposure at the school.
- **Negative / verification boundary:** without key expect `unconfigured`; provider failure `unavailable`; no returned rows `no_detections`; old rows `stale`; wind failure/missing/stale/incomplete samples `wind_unavailable` or `wind_indeterminate`; detections with no positive toward result show no-upwind/indeterminate states. No detections does not prove no smoke. The original “Smoke from nearby fires is likely contributing” claim is blocked. Live FIRMS/Open-Meteo behavior is not verified; it needs internet and a valid key, but does not need AWS for local request testing.

### F21 — 19:00 IST tomorrow forecast alert

- **Status / UI / API:** handler and schedule configuration implemented locally. `DailyCheckFunction` has a 19:00 Asia/Kolkata EventBridge Scheduler event with `forecast_target: tomorrow`; no frontend page or public endpoint.
- **Data / provider / config:** scheduled Lambda fetches a two-day Open-Meteo forecast, selects tomorrow's local school date, and uses DynamoDB/SNS/Telegram notification paths. Needs deployed EventBridge, Lambda, database tables, permissions, and configured recipients for real delivery.
- **Manual test:** in AWS, verify the enabled evening schedule, timezone, target, and Lambda target in EventBridge Scheduler. After a real invocation, inspect the event/logs for `forecast_target=tomorrow`, verify the message labels tomorrow, compare `forecast_date` to Asia/Kolkata local date, and confirm the run did not write a duplicate same-day History record. Check recipient delivery independently; a successful Lambda result alone is not proof a message arrived.
- **Negative / verification boundary:** test a failed forecast (no notification/history), retry and duplicate invocation (no duplicate successful send), and a UTC/India midnight boundary using controlled test events. These date/idempotency behaviors have local automated coverage. Actual schedule execution and SNS/Telegram delivery are unverified and require deployment.

## Exact local inspection commands

These commands exercise the current live forecast and school APIs; provider
requests require internet access. Replace `<school_id>` with the ID returned by
school registration. Do not put credentials into command history.

```sh
curl -i 'http://localhost:8017/api/v1/forecast?latitude=19.0760&longitude=72.8777'
curl -i 'http://localhost:8017/api/v1/schools'
curl -i 'http://localhost:8017/api/v1/status?school_id=<school_id>'
curl -i 'http://localhost:8017/api/v1/history?school_id=<school_id>&days=30'
curl -i 'http://localhost:8017/api/v1/schools/<school_id>/smoke-hint'
```

School creation/subscription request shapes are:

```sh
curl -i -X POST http://localhost:8017/api/v1/schools \
  -H 'Content-Type: application/json' \
  -d '{"name":"Test School","latitude":19.076,"longitude":72.8777,"language":"English"}'

curl -i -X POST http://localhost:8017/api/v1/subscribe \
  -H 'Content-Type: application/json' \
  -d '{"school_id":"<school_id>","email":"mailbox-you-control@example.org","sensitive":false}'
```

With `USE_MEMORY_DB=true`, registration is local and ephemeral; subscription
returns a demo-only result and creates no SNS subscription. Replace the example
address with a mailbox you control only when testing a deployed SNS flow.

## Overall verification boundaries

- The latest project progress report records 143 backend tests passed, the F20
  endpoint test passed individually, 36 frontend tests passed, and frontend
  build/Ruff/diff checks passed. These are local checks, not live-provider or
  deployed-AWS proof.
- Open-Meteo forecast and Historical Forecast responses are model data, not
  school-site measurements. NASA satellite detections plus modeled wind are
  only a potential transport hint, not confirmation of smoke exposure.
- F19's accuracy calculation remains unavailable pending authoritative
  observation data and matching/scoring rules.
- F20 live provider behavior has not been verified.
- F21's deployed schedule and actual SNS/Telegram delivery have not been
  verified. AWS architecture is defined in `template.yaml`, not proven deployed.
- Never run deployment commands or incur AWS costs as part of these manual
  checks without explicit project-owner approval.
