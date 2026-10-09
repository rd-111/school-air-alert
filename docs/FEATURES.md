# School Air Alert: Feature Specification for Codex

**How to use this file:** save it as `docs/FEATURES.md`. Add this line to `AGENTS.md`:

> Before any feature task, read `docs/FEATURES.md`. Implement ONLY the feature ID I name. Follow its acceptance criteria. Do not add other features.

Then give Codex one feature at a time, for example: *"Implement F6 from docs/FEATURES.md. Touch only the files listed. Run pytest and summarize."*

---

## 0. Product summary

Every morning at 06:00 IST, the system forecasts PM2.5 for school hours (07:00 to 15:00), decides **GREEN / YELLOW / RED**, finds the best and worst hours for outdoor activity, and sends a short plain-language alert to principals and parents by email and Telegram. A website shows status, a 24-hour chart, a monthly report card, and a printable poster.

**Users:** principal or teacher (decides activities), parent (wants to know if the child can play outside), parent of a child with asthma or allergies (needs stricter alerts).

**Non-goals (do NOT build):** hardware sensors, machine-learning forecasts, user accounts or passwords, payments, native mobile apps, SMS, maps or heatmaps of many cities.

---

## 1. Shared definitions (all features use these)

### Status levels (PM2.5 in ug/m3, averaged over school hours)

| Status | Normal users | Sensitive students |
|---|---|---|
| GREEN | up to 60 | up to 40 |
| YELLOW | up to 120 | up to 90 |
| RED | above 120 | above 90 |

These are **placeholders**. Keep them only in constants `LEVELS` and `LEVELS_SENSITIVE` in `src/common/classify.py`, with the comment `TODO verify against CPCB guidance`. Record sources in `docs/thresholds.md`.

### Advice text (plain language, one or two sentences)
- GREEN: normal outdoor activities are fine.
- YELLOW: shorten outdoor play, move strenuous activity to the safest hours, keep students with breathing problems indoors.
- RED: move PE and assembly indoors, keep windows closed, no outdoor activity.

### DynamoDB tables (on-demand billing)

| Table | Partition key | Sort key | Other attributes |
|---|---|---|---|
| `Schools` | `school_id` (S) | none | name, lat, lon, language, topic_arn, topic_arn_sensitive, created_at |
| `Subscribers` | `school_id` (S) | `contact` (S) | channel (email or telegram), sensitive (BOOL), created_at |
| `History` | `school_id` (S) | `date` (S, YYYY-MM-DD) | avg_pm25, peak_pm25, status, best_window, worst_window |

Rules: numbers are stored as `Decimal`, never float. Store no names of children and no medical details, only a `sensitive` true/false flag.

### Alert message format

```
Air alert for <School name>: <STATUS>
Average PM2.5 during school hours: <n> ug/m3 (peak <n>).
Best time for outdoor activity: <HH:00-HH:00>
Avoid outdoors: <HH:00-HH:00>
<one or two sentences of advice>
```

### Environment variables (names only; never real values in Git)
`SCHOOLS_TABLE`, `SUBSCRIBERS_TABLE`, `HISTORY_TABLE`, `BEDROCK_MODEL`, `TELEGRAM_TOKEN`, `TELEGRAM_SECRET`

---

## 2. CORE features (must work before anything else)

### F1. Air forecast fetch and parse
- **What:** get the hourly PM2.5 forecast for a school's coordinates and extract school hours.
- **Source:** Open-Meteo Air Quality API, `hourly=pm2_5`, `forecast_days=1`, `timezone=Asia/Kolkata`. No API key.
- **Files:** `src/common/air.py`, `tests/test_air.py`, `tests/fixtures/open_meteo_sample.json`
- **Functions:**
  - `fetch_hourly_pm25(lat, lon)`: standard library `urllib` only, 10 second timeout, one retry, returns parsed JSON.
  - `parse_school_hours(data, hours=range(7, 15))`: returns a list of `(hour, pm25)`, skipping `None`.
- **Acceptance:** tests use the saved fixture and never call the network; empty or malformed data returns an empty list, not a crash.

### F2. Status classification
- **What:** turn a PM2.5 number into a status and advice.
- **Files:** `src/common/classify.py`, `tests/test_classify.py`
- **Function:** `classify(pm25, sensitive=False)` returns `(status, advice)`.
- **Acceptance:** tests cover each boundary (60, 61, 120, 121 and the sensitive equivalents 40, 41, 90, 91). Thresholds exist only in the two constants.

### F3. Daily scheduled alert
- **What:** a Lambda runs every day at 06:00 IST and processes every school.
- **Files:** `template.yaml`, `src/daily_check/app.py`
- **Behavior:** for each school: fetch (F1), average and peak PM2.5, classify (F2), build message, send (F4), log (F5).
- **Acceptance:** schedule uses EventBridge Scheduler / SAM `ScheduleV2` with time zone `Asia/Kolkata`; timeout 60 seconds; one failing school is logged and skipped, the others still run; the handler returns a JSON summary per school.

### F4. Email alerts via SNS
- **What:** each school has two SNS topics: `topic_arn` (everyone) and `topic_arn_sensitive`. The daily run publishes to each with its own message (see F7).
- **Files:** `src/common/notify.py`, `src/common/messages.py`
- **Acceptance:** subject is `Air Alert <STATUS>: <school name>` and is at most 100 characters; the function has `sns:Publish` only on the needed topics where possible; publish errors are logged and do not stop the run.

### F5. Alert history log
- **What:** every run writes one `History` row per school per date.
- **Files:** `src/common/db.py`
- **Acceptance:** writing the same school and date twice overwrites (idempotent); all numbers are `Decimal`.

---

## 3. TIER 1 features (the ones that make it stand out)

### F6. Activity planner
- **What:** show the safest and worst hours for outdoor activity.
- **Files:** `src/common/planner.py`, `tests/test_planner.py`
- **Functions:** `best_window(hourly, length=1)`, `worst_window(hourly, length=1)`, `summary(hourly)` returning `{avg, peak, best, worst}`.
- **Acceptance:** at least 5 tests including ties, empty list, and fewer hours than the window length; the best window appears in every alert message and in the History row.

### F7. Sensitive-student mode
- **What:** parents of students with asthma or allergies subscribe to the sensitive topic and receive alerts using the stricter thresholds and extra advice (for example "keep your child indoors for outdoor periods").
- **Files:** `src/common/classify.py`, `src/common/messages.py`, `src/daily_check/app.py`
- **Acceptance:** on a day with average PM2.5 between 41 and 60, normal subscribers see GREEN and sensitive subscribers see YELLOW; only the `sensitive` boolean is stored.

### F8. School registration and subscription API
- **What:** HTTP API endpoints to register a school and to subscribe an email.
- **Files:** `template.yaml`, `src/api/app.py`, `src/common/validation.py`, `tests/test_api.py`
- **Routes:**
  - `GET /schools` returns `[{school_id, name}]` only.
  - `POST /schools` with `{name, latitude, longitude, language}`; creates the school and both SNS topics.
  - `POST /subscribe` with `{school_id, email, sensitive}`; subscribes the email to the right topic.
- **Validation:** name 3 to 80 characters; latitude -90..90; longitude -180..180; language in `English`, `Hindi`, `Marathi`; email format; unknown `school_id` returns 404.
- **Acceptance:** bad input returns 400 with a clear message and saves nothing; responses never include other people's emails; CORS headers present; API throttling configured.

### F9. Status and history API
- **What:** data the website and bot read.
- **Routes:**
  - `GET /status?school_id=` returns the latest History row plus today's hourly values for the chart.
  - `GET /history?school_id=&days=30` returns counts of GREEN, YELLOW, RED days and the daily list.
- **Acceptance:** `days` is capped at 90; empty history returns zero counts, not an error.

### F10. Telegram bot
- **What:** parents receive and request alerts on Telegram.
- **Files:** `src/bot/app.py`, `template.yaml`, `tests/test_bot.py`
- **Route:** `POST /telegram` (webhook).
- **Commands:** `/start` (greeting and help), `/schools` (list), `/subscribe <school_id>`, `/sensitive on|off`, `/today`, `/stop`.
- **Security:** reject any request whose `X-Telegram-Bot-Api-Secret-Token` header does not equal `TELEGRAM_SECRET`; the token and secret are `NoEcho` template parameters, never in Git.
- **Acceptance:** tests use sample update JSON with no network; the daily run also sends to Telegram subscribers using their own `sensitive` flag; blocked or failed chats are logged and skipped.

### F11. Website dashboard
- **What:** a page a stranger can use without help.
- **Files:** `web/index.html`, `web/assets/style.css`, `web/assets/app.js`, `web/config.example.js`
- **Rules:** plain HTML, CSS and JavaScript only; no framework, no build step, no external libraries; API URL read from `window.CONFIG.API_URL`.
- **Sections:** school picker; large status card (colour AND the words GREEN/YELLOW/RED plus advice); 24-hour bar chart drawn with inline SVG with the best window highlighted; register-school form; subscribe form with a sensitive checkbox; link to the Telegram bot.
- **Acceptance:** mobile-first; readable without zooming on a phone; colour is never the only signal; loading and error messages shown; works with an empty database.

### F12. Monthly report card
- **What:** impact evidence for judges and schools.
- **Display:** for the last 30 days: counts of GREEN, YELLOW, RED days, and "outdoor hours protected" (number of RED/YELLOW days multiplied by the school-day outdoor hours the school set; default 2).
- **Source:** `GET /history`.
- **Acceptance:** numbers match the History table exactly; a clear label says it is based on forecasts, not measured exposure.

### F13. Printable notice-board poster
- **What:** a big simple page a school can print and stick on a board.
- **Files:** `web/poster.html` (reads `?school_id=`)
- **Content:** school name, date, status in very large type with colour and text, best and worst hours, three short advice lines.
- **Acceptance:** `@media print` fits one A4 page, hides buttons, stays legible in black and white; includes a Print button.

### F14. AI-written messages with Amazon Bedrock (optional, with fallback)
- **What:** a friendly short message in the school's language (English, Hindi or Marathi).
- **Files:** `src/common/messages.py`, `tests/test_messages.py`
- **Function:** `ai_message(school_name, status, advice, summary, language)` using the Bedrock runtime `converse` API and the model ID from `BEDROCK_MODEL`.
- **Rules for the prompt:** give the model only the facts; maximum 60 words; simple words; do not add facts or medical claims.
- **Safety:** if `BEDROCK_MODEL` is empty, or the call fails or times out, or the reply does not mention the status word, return `template_message(...)` instead.
- **Acceptance:** tests with a mocked client cover success, exception, and a reply that ignores the status.

---

## 4. CROSS-CUTTING requirements (apply to every feature)

### F15. Security and privacy
- No secrets, tokens, keys, account IDs or real emails in code, tests, docs or Git history.
- Least-privilege IAM for each function in `template.yaml`; avoid `"*"` resources and say why in a comment if unavoidable.
- Validate every API input; limit string lengths; return generic errors without stack traces.
- Store only: school name and location, subscriber contact, and a `sensitive` flag. Provide an unsubscribe route (`/stop` on Telegram; SNS unsubscribe link for email).
- CORS limited to the website origin once it is known.

### F16. Reliability and fallbacks
- Every external call (Open-Meteo, Bedrock, Telegram) has a timeout and a fallback.
- One school's failure never stops the others.
- Logs are structured one-liners that include `school_id` and a short reason, never secrets.
- The system works end to end with Bedrock disabled.

### F17. Tests and CI
- Each function in `src/common/` has unit tests; tests never call the network or AWS (mock them).
- `python -m pytest -q` passes.
- `.github/workflows/test.yml` runs pytest on every push and pull request using Python 3.12.

### F18. Documentation
- `README.md`: problem, features, architecture summary, AWS services and why each, setup and deploy steps, how to run tests, limitations.
- `docs/architecture.md`: Mermaid diagram of the data flow.
- `docs/thresholds.md`: source for every PM2.5 number or a note that it is a placeholder.
- `docs/user-interview.md`, `docs/demo-script.md`, `docs/blog-draft.md` with clearly marked placeholders; **never invent results, numbers or quotes**.

---

## 5. TIER 2 features (only if everything above works by Day 5)

### F19. Forecast accuracy meter
Compare yesterday's forecast with what actually happened (check the Open-Meteo documentation for past data options) and show "forecast matched the status on X of the last 10 days". Store the comparison in `History`. Label it honestly.

### F20. Smoke-source hint
Use NASA FIRMS fire hotspots (free map key, stored as a template parameter, never in Git) from the last 24 hours upwind of the school. If a cluster exists, add one line: "Smoke from nearby fires is likely contributing." Must fall back silently if FIRMS is unavailable.

### F21. Evening "tomorrow" alert
A second schedule at 19:00 IST that sends tomorrow's forecast status so parents can plan ahead. Reuse F1 to F4 with `forecast_days=2`.

---

## 6. Recommended build order (one feature per Codex task)

| Order | Features | Done when |
|---|---|---|
| 1 | F2, F1, F6 | pytest passes |
| 2 | F5, F4, F3 | a real email arrives from the scheduled Lambda |
| 3 | F7 | sensitive and normal messages differ on a 41-60 day |
| 4 | F8, F9 | curl returns correct JSON; bad input returns 400 |
| 5 | F14 | AI message works and fallback works |
| 6 | F10 | bot replies and delivers the daily alert |
| 7 | F11, F12, F13 | a stranger can use the site on a phone |
| 8 | F15, F16, F17 | review finds no high-severity issues; CI is green |
| 9 | F18 | README makes sense to a friend |
| 10 | F19 to F21 | only if time remains |

---

## 7. Codex instruction templates

**Implement one feature**
> Read AGENTS.md and docs/FEATURES.md. Implement ONLY feature F__ . Touch only the files listed for it. Write the tests it requires, run `python -m pytest -q`, and end with: files changed, how I verify it, anything you are unsure about.

**Review before commit**
> Review my uncommitted changes against the acceptance criteria of F__ in docs/FEATURES.md. List what is missing or risky by severity. Do not change files.

**Explain for learning**
> Explain what you just implemented for F__ in simple words, line by line, then ask me three questions to check I understood.

**Fix an error**
> Here is the exact error: [paste]. Explain the cause in two sentences, then propose the smallest fix. Do not change unrelated files.
