# School Air Alert: Feature Specification

Read the root `AGENTS.md`, `docs/AGENTS.md`, and this file before a feature task. Implement only the feature ID requested, follow its acceptance criteria, and keep changes within the listed target areas. The fixed architecture and stack in `docs/AGENTS.md` take precedence over older implementation paths in this feature list. Do not add dependencies, AWS services, or behavior beyond the stated requirements without asking.

## 0. Product summary

### Implementation status note (2026-10-23)

The repository has local implementations for the forecast, planner, daily
alerts, SNS/email, history and school APIs, sensitive mode, Telegram bot,
optional Bedrock messages, dashboard, monthly report, poster, and docs. F21's
19:00 IST tomorrow-forecast path is implemented locally. F19 remains blocked
until an authoritative observed-data source and date/station matching rules are
approved. F20 has a partial optional FIRMS and modeled-wind implementation;
the causal smoke-attribution claim remains blocked pending approval. AWS
resources, real provider calls, and delivery
remain unverified because nothing has been deployed. See README.md for setup,
test results, and limitations.

Every morning at 06:00 IST, the system forecasts PM2.5 for school hours (07:00–15:00), decides GREEN / YELLOW / RED, finds the best and worst hours for outdoor activity, and sends plain-language alerts to principals and parents by email and Telegram. A React website shows status, a 24-hour chart, a monthly report card, and a printable poster. Anyone can also check air quality for their location without signing up.

Users include principals or teachers deciding activities, parents, and parents of children with asthma or allergies who may want stricter alerts. Do not build hardware sensors, machine-learning forecasts, accounts or passwords, payments, native mobile apps, SMS, or maps/heatmaps of many cities.

**Clarification for later:** the target product also calls for activity-wise advice (assembly, recess, PE, bus wait). F6 currently specifies only time-window planning. Do not infer activity-specific rules until their inputs and acceptance criteria are agreed.

## 1. Shared definitions

### Status levels

PM2.5 is in µg/m³ and averaged over school hours.

| Status | Normal users | Sensitive students |
|---|---:|---:|
| GREEN | up to 60 | up to 40 |
| YELLOW | up to 120 | up to 90 |
| RED | above 120 | above 90 |

These values are placeholders. Keep threshold constants only in `backend/app/services/classify.py`: `LEVELS`, `LEVELS_SENSITIVE`, and `ACTIVITY_FACTOR`. Mark each with `TODO verify against CPCB guidance`. Record sources or placeholder status in `docs/thresholds.md`.

**Clarification for later:** no values or formula are specified for `ACTIVITY_FACTOR`. Do not invent them. Confirm whether and how it affects classification or advice before using it.

### Advice

- GREEN: normal outdoor activities are fine.
- YELLOW: shorten outdoor play, move strenuous activity to the safest hours, and keep students with breathing problems indoors.
- RED: move PE and assembly indoors, keep windows closed, and avoid outdoor activity.

Keep advice plain and short. Do not make medical claims. API responses that provide advice include: “Informational only, not medical advice.”

### Data and privacy

| Table | Partition key | Sort key | Other attributes |
|---|---|---|---|
| `Schools` | `school_id` (S) | none | name, lat, lon, language, topic_arn, topic_arn_sensitive, created_at |
| `Subscribers` | `school_id` (S) | `contact` (S) | channel (email or telegram), sensitive (BOOL), created_at |
| `History` | `school_id` (S) | `date` (S, YYYY-MM-DD) | avg_pm25, peak_pm25, status, best_window, worst_window |

Store numbers as `Decimal` in DynamoDB. Convert between floats and `Decimal` only in repositories. Store no child names or medical details; only the `sensitive` boolean flag.

### Alert message format

```text
Air alert for <School name>: <STATUS>
Average PM2.5 during school hours: <n> ug/m3 (peak <n>).
Best time for outdoor activity: <HH:00-HH:00>
Avoid outdoors: <HH:00-HH:00>
<one or two sentences of advice>
```

### Environment variable names

`SCHOOLS_TABLE`, `SUBSCRIBERS_TABLE`, `HISTORY_TABLE`, `BEDROCK_MODEL`, `TELEGRAM_TOKEN`, `TELEGRAM_SECRET`. Keep `.env.example` to names and placeholder values only; never put real values in Git.

## 2. CORE features

### F1. Air forecast fetch and parse

- **What:** fetch hourly PM2.5 forecast data for coordinates and extract school hours. Open-Meteo Air Quality API uses `hourly=pm2_5`, `forecast_days=1`, and `timezone=Asia/Kolkata`; no API key.
- **Target areas:** `backend/app/services/air.py`, `backend/tests/test_air.py`, `backend/tests/fixtures/open_meteo_sample.json`.
- **Functions:** `fetch_hourly_pm25(lat, lon)` uses standard-library `urllib.request`, a 10-second timeout, and one retry, returning parsed JSON. `parse_school_hours(data, hours=range(7, 15))` returns `(hour, pm25)` pairs and skips `None` values.
- **Acceptance:** tests use the saved fixture and never make network requests. Empty or malformed data returns an empty list rather than crashing.
- **Clarification for later:** the target also names Open-Meteo Geocoding API and location lookup without sign-up, but no feature specifies its input privacy, response, or endpoint. Do not add those behaviors to F1 without defining them.

### F2. Status classification

- **What:** turn a PM2.5 number into a status and advice.
- **Target areas:** `backend/app/services/classify.py`, `backend/tests/test_classify.py`.
- **Function:** `classify(pm25, sensitive=False)` returns `(status, advice)`.
- **Acceptance:** thresholds are held only in `LEVELS`, `LEVELS_SENSITIVE`, and `ACTIVITY_FACTOR` in the service module, each with `TODO verify against CPCB guidance`. Tests cover normal boundaries 60, 61, 120, 121 and sensitive boundaries 40, 41, 90, 91. Advice follows the shared definitions and does not make medical claims.

### F3. Daily scheduled alert

- **What:** a Lambda processes every school daily at 06:00 Asia/Kolkata.
- **Target areas:** root `template.yaml`, `backend/handlers/daily_check.py`, and the shared `backend/app/` package.
- **Behavior:** for each school, fetch F1 data, calculate average and peak PM2.5, classify with F2, build a message, send via F4, and log via F5.
- **Acceptance:** use SAM `ScheduleV2` / EventBridge Scheduler with time zone `Asia/Kolkata`; Lambda timeout is 60 seconds; one failing school is logged and skipped while others continue; handler returns a JSON summary per school.

### F4. Email alerts via SNS

- **What:** each school has regular and sensitive SNS topics (`topic_arn`, `topic_arn_sensitive`). The daily run publishes a separate message for each audience as required by F7.
- **Target areas:** `backend/app/services/notify.py`, `backend/app/services/messages.py`, and the relevant least-privilege resources in `template.yaml`.
- **Acceptance:** subject is `Air Alert <STATUS>: <school name>` and no longer than 100 characters. Grant `sns:Publish` only on needed topics where possible. Publish errors are logged and do not stop the run.

### F5. Alert history log

- **What:** each run writes one History row per school per date.
- **Target area:** `backend/app/repositories/` (repository responsible for History; exact module name may follow the repository's established naming).
- **Acceptance:** writing the same school and date twice overwrites idempotently. Repository converts numeric values to DynamoDB `Decimal` and back on read.

## 3. TIER 1 features

### F6. Activity planner

- **What:** find the safest and worst hours for outdoor activity.
- **Target areas:** `backend/app/services/planner.py`, `backend/tests/test_planner.py`.
- **Functions:** `best_window(hourly, length=1)`, `worst_window(hourly, length=1)`, and `summary(hourly)` returning `{avg, peak, best, worst}`.
- **Acceptance:** at least five tests, including ties, empty input, and fewer hours than the window length. The best window appears in each alert message and in the History row.
- **Clarification for later:** `docs/AGENTS.md` also requires activity-wise advice for assembly, recess, PE, and bus wait, but no rules connect those activities to windows or statuses. Define this separately before implementing it; do not infer thresholds or advice.

### F7. Sensitive-student mode

- **What:** parents who opt in receive alerts using stricter thresholds and extra advice (for example, asking them to keep their child indoors for outdoor periods).
- **Target areas:** `backend/app/services/classify.py`, `backend/app/services/messages.py`, `backend/handlers/daily_check.py`.
- **Acceptance:** when average PM2.5 is between 41 and 60, regular subscribers see GREEN and sensitive subscribers see YELLOW. Store only the `sensitive` boolean for this preference; no medical details.

### F8. School registration and subscription API

- **What:** HTTP API endpoints register a school and subscribe an email.
- **Target areas:** routers, schemas, services, and repositories under `backend/app/`; infrastructure and API integration in root `template.yaml`; tests in `backend/tests/test_api.py`.
- **Routes:** `GET /api/v1/schools` returns `[{school_id, name}]`; `POST /api/v1/schools` accepts `{name, latitude, longitude, language}`, creates the school and both SNS topics; `POST /api/v1/subscribe` accepts `{school_id, email, sensitive}` and subscribes to the matching topic.
- **Validation:** name 3–80 characters; latitude -90..90; longitude -180..180; language one of English, Hindi, Marathi; email format; unknown school returns 404. Bad input returns 400 with a clear message and saves nothing. Responses never expose other subscribers' email addresses. CORS headers and API throttling are configured.
- **API rules:** every route has Pydantic request and response models and `response_model=`, lives under `/api/v1`, and uses the standard error body `{"error":{"code":"SNAKE_CASE","message":"plain words"}}` without stack traces. Inject settings and repositories with `Depends`.
- **Clarification for later:** exact router split and whether school creation stores coordinates supplied by a person or a geocoding result can be decided when implementing, without changing the route behavior above.

### F9. Status and history API

- **What:** provide data for the website and bot.
- **Target areas:** routers, schemas, services, and repositories under `backend/app/`; tests in `backend/tests/`.
- **Routes:** `GET /api/v1/status?school_id=` returns the latest History row plus today's hourly values for the chart. `GET /api/v1/history?school_id=&days=30` returns GREEN/YELLOW/RED counts and the daily list.
- **Acceptance:** `days` is capped at 90. Empty history returns zero counts rather than an error. Use response models and standard API error bodies.

### F10. Telegram bot

- **What:** parents receive and request alerts on Telegram.
- **Target areas:** Telegram router and related services under `backend/app/`, root `template.yaml`, and `backend/tests/test_bot.py`.
- **Route:** `POST /api/v1/telegram` on the same FastAPI app handled by Mangum.
- **Commands:** `/start` (greeting and help), `/schools` (list), `/subscribe <school_id>`, `/sensitive on|off`, `/today`, `/stop`.
- **Security and acceptance:** reject requests unless `X-Telegram-Bot-Api-Secret-Token` matches `TELEGRAM_SECRET`; token and secret are SAM `NoEcho` parameters and never in Git. Tests use sample update JSON and no network. Daily alerts go to Telegram subscribers using each subscriber's `sensitive` flag. Blocked or failed chats are logged and skipped. External calls have timeouts and fallbacks.

### F11. Website dashboard

- **What:** a mobile-friendly page that a visitor can use without help.
- **Target areas:** React app under `frontend/src/`, including `api/client.js`, `pages/`, `components/`, `hooks/`, `i18n/`, `styles/`, `utils/`, and `test/`; Vite project files under `frontend/`.
- **Stack:** React 18, Vite, React Router, Recharts, JavaScript (not TypeScript), and plain CSS with CSS variables. No additional framework or UI dependency. All HTTP goes through `src/api/client.js`; its base URL is `import.meta.env.VITE_API_URL`.
- **Sections:** school picker; large status card with both color and GREEN/YELLOW/RED words, icon, and advice; 24-hour chart with best window highlighted; school registration form; email subscription form with sensitive checkbox; Telegram bot link.
- **Acceptance:** every screen has loading, empty, and error states; works with an empty database; mobile-first, body text at least 16px, large tap targets and good contrast; color is never the only signal. All visible text comes from `src/i18n/en.json`, `hi.json`, and `mr.json`; no hardcoded component strings, `dangerouslySetInnerHTML`, or frontend secrets. The API URL uses public `VITE_API_URL` configuration.

### F12. Monthly report card

- **What:** show evidence of forecasted school-day impacts.
- **Target areas:** React page/component under `frontend/src/`, localized strings under `frontend/src/i18n/`, and F9's history API.
- **Display and acceptance:** for the last 30 days show GREEN/YELLOW/RED counts and “outdoor hours protected” (number of RED/YELLOW days multiplied by school-day outdoor hours set by the school; default 2). Counts match History exactly. Clearly label this as based on forecasts, not measured exposure.
- **Clarification for later:** confirm how a school sets outdoor hours when designing registration/settings; retain the specified default of 2 until then.

### F13. Printable notice-board poster

- **What:** a simple page schools can print and display.
- **Target areas:** React page/route under `frontend/src/pages/`, components and CSS under `frontend/src/`; data comes from the status API.
- **Content:** school name, date, very large status text and color, best and worst hours, and three short advice lines. Read `school_id` from the page query string.
- **Acceptance:** `@media print` fits one A4 page, hides buttons, remains legible in black and white, and provides a Print button.

### F14. AI-written messages with Amazon Bedrock (optional, with fallback)

- **What:** produce a friendly short message in English, Hindi, or Marathi.
- **Target areas:** `backend/app/services/messages.py`, `backend/app/config.py`, and `backend/tests/test_messages.py`.
- **Function:** `ai_message(school_name, status, advice, summary, language)` uses Bedrock Runtime `converse` and `BEDROCK_MODEL`.
- **Prompt and safety:** provide only known facts; maximum 60 words; simple language; add no facts or medical claims. If model setting is empty, the call fails or times out, or reply omits the status word, return `template_message(...)` instead.
- **Acceptance:** mocked-client tests cover success, exception, timeout/fallback, and a reply that ignores the status. Bedrock remains optional; the app works with it disabled.

## 4. CROSS-CUTTING requirements

### F15. Security and privacy

- No secrets, tokens, keys, account IDs, or real emails in code, tests, docs, or Git history. Keep `.env`, `.aws/`, and credentials out of Git; never read credential files.
- Least-privilege IAM per function in root `template.yaml`; avoid `*` resources or explain unavoidable use in a comment.
- Validate API inputs and string lengths; return generic errors without stack traces using the standard error shape.
- Store only school name/location and subscriber contact plus `sensitive` flag. Provide unsubscribe via Telegram `/stop` and SNS email unsubscribe.
- Restrict CORS to the website origin once known.
- Never deploy or change cloud resources without explicit approval.

### F16. Reliability and fallbacks

- Every external call (Open-Meteo, Bedrock, Telegram) has a timeout and fallback.
- A school's failure never stops processing other schools.
- Logs are structured one-line records with `school_id` and short reason, never secrets.
- End-to-end behavior works with Bedrock disabled.

### F17. Tests and CI

- Test pure logic in `backend/app/services/`; tests never call network or AWS (mock integrations).
- Backend command: `cd backend && python -m pytest -q`.
- Backend lint: `cd backend && ruff check .`.
- `.github/workflows/test.yml` runs backend pytest on every push and pull request using Python 3.12. Frontend tests use Vitest and React Testing Library.
- Run tests and lint only when authorized for the task; do not install dependencies without approval.

### F18. Documentation

- `README.md`: problem, features, architecture summary, AWS services and purpose, setup/deploy steps, test instructions, and limitations.
- `docs/architecture.md`: Mermaid data-flow diagram.
- `docs/thresholds.md`: source for each PM2.5 number or explicit placeholder note.
- `docs/user-interview.md`, `docs/demo-script.md`, and `docs/blog-draft.md`: clearly marked placeholders; never invent results, numbers, or quotes.
- Keep environment-variable names in `.env.example` with placeholder values only.

## 5. TIER 2 features

Implement only after core and Tier 1 features are working.

### F19. Forecast accuracy meter

Compare yesterday's forecast with what occurred (check Open-Meteo historical options when implementing) and show “forecast matched the status on X of the last 10 days.” Store comparison in History and label it honestly.
- **Target areas:** backend services/repositories and tests, status/history API, and frontend report UI as needed.
- **Clarification for later:** define which measured/observed source is authoritative and how matching dates are handled before implementation; do not present forecast data as observed truth.

**Current implementation note (2026-10-09):** not implemented. Open-Meteo
forecast history/reanalysis is model-derived and is not an approved authoritative
school-site observation record. Approval is needed for the observation provider,
station-to-school matching, timezone/date alignment, missing-data handling, and
the comparison definition before this feature can report accuracy. Open-Meteo
describes its Historical Forecast API as archived model runs initialized from
measurements, while its Air Quality API `past_days` returns archived forecasts;
neither establishes the agreed school-site observation record. See the [Open-Meteo
Historical Forecast API](https://open-meteo.com/en/docs/historical-forecast-api)
and [Air Quality API](https://open-meteo.com/en/docs/air-quality-api).

### F20. Smoke-source hint

Use NASA FIRMS hotspots from the last 24 hours upwind of the school. If an approved cluster exists, add: “Smoke from nearby fires is likely contributing.” If FIRMS is unavailable, keep the core forecast available and show an explicit unavailable state for the optional hint.
- **Target areas:** isolated backend service/provider, configuration, and tests; integrate with alert messages only after verified.
- **Configuration clarification:** the optional NASA FIRMS service and
  backend-only key configuration are authorized for this partial
  implementation. The MAP_KEY is not a frontend setting or a committed value.

**Current implementation note (2026-10-23):** the optional backend service
queries NASA FIRMS for registered-school coordinates, filters NOAA-21 VIIRS
NRT CSV to the trailing 24 hours and configured radius (default 25 km),
deduplicates exact platform/time/location rows, and groups same-platform,
same-acquisition-minute pixels whose scan/track footprint disks overlap.
Clusters are not merged across platforms or acquisition minutes. A cluster is
one connected pixel group, not an independently verified fire. NASA documents
the VIIRS acquisition time as UTC and scan/track as actual pixel dimensions
([field definitions](https://modaps.modaps.eosdis.nasa.gov/services/about/products/viirs-land-c2-nrt/vnp14imgtdl_nrt.html)).

For each cluster, the backend makes one batched query to the Open-Meteo
Historical Forecast API for modeled 10 m wind at the cluster coordinate and
acquisition time. Meteorological wind-from direction is converted to a
downwind east/north vector, and hourly vectors are interpolated before
comparison with the cluster-to-school displacement. A positive projection is
labelled as possible modeled transport; this geometric half-plane check is not
a plume model. Missing, invalid, unbracketed, or non-hourly wind is
indeterminate. NASA FIRMS or Open-Meteo failure does not block the air-quality
forecast. The UI shows the exact interim wording only for a positive modeled
transport result. Both sources and the wind retrieval time are labelled.
The batched wind result uses the existing short configurable in-process cache.

The original “Smoke from nearby fires is likely contributing” causal statement
remains blocked: these data do not establish smoke at ground level, exposure
at a school, or a contribution to PM2.5. The interim wording also does not
confirm exposure. Wind is model output, not an observation. Open-Meteo data
availability varies by model and the newest archive records may be missing;
the service returns an indeterminate state instead of substituting forecast
values. Its free API is limited to non-commercial use and requires attribution.
F20 remains partially implemented pending approval of model adequacy, plume
and uncertainty policy, and evidence needed for any causal claim.

### F21. Evening “tomorrow” alert

Add a second schedule at 19:00 IST to send tomorrow's forecast status, reusing F1–F4 with `forecast_days=2`.
- **Target areas:** root `template.yaml`, `backend/handlers/daily_check.py`, and backend tests.
- **Clarification for later:** the fixed architecture explicitly specifies the 06:00 schedule. Confirm the additional schedule and tomorrow-message format before implementation.

**Current implementation note (2026-10-09):** implemented locally as a 19:00
Asia/Kolkata schedule using a two-day Open-Meteo forecast and a tomorrow label.
The event's scheduled time anchors the target date across retries; notification
claims reduce duplicate sends, and the evening run does not write a second
same-day History row. Asia/Kolkata has no daylight-saving transitions; local
date selection is covered at the UTC/India midnight boundary. SAM deployment
and live delivery are not verified.

## 6. Recommended build order

| Order | Features | Done when |
|---|---|---|
| 1 | F2, F1, F6 | `cd backend && python -m pytest -q` passes for those services |
| 2 | F5, F4, F3 | local/mock tests pass; real email delivery requires separately approved deployment and verification |
| 3 | F7 | normal and sensitive message behavior differs on a 41–60 µg/m³ day |
| 4 | F8, F9 | local API returns expected JSON and invalid input returns 400 |
| 5 | F14 | mocked success and fallbacks pass; Bedrock remains optional |
| 6 | F10 | mocked bot tests pass; live delivery requires separately approved setup |
| 7 | F11, F12, F13 | frontend tests/build pass and screens work on mobile |
| 8 | F15, F16, F17 | security/reliability review complete and CI green |
| 9 | F18 | documentation is understandable and limitations are explicit |
| 10 | F19–F21 | only after prerequisites and clarification items are resolved |

## 7. Task templates

**Implement one feature**

> Read `AGENTS.md`, `docs/AGENTS.md`, and `docs/FEATURES.md`. Implement ONLY feature F__. Follow its acceptance criteria, touch only its listed target areas, write tests, and run the relevant approved test command. Report files changed, exact verification commands/results, and unresolved questions.

**Review before commit**

> Review my uncommitted changes against feature F__ in `docs/FEATURES.md`. List missing or risky items by severity. Do not change files.

**Explain for learning**

> Explain what you just implemented for F__ in simple words, then ask me three questions to check I understood.

**Fix an error**

> Here is the exact error: [paste]. Explain the cause in two sentences, then propose the smallest fix. Do not change unrelated files.
