# School Air Alert - instructions for Codex

Read this file and `docs/FEATURES.md` before every task. Implement ONLY the feature ID I name.

## What this project is
A web app plus alert service for schools in India. Every morning it forecasts PM2.5 for school hours (07:00-15:00 IST), decides GREEN / YELLOW / RED, gives activity-wise advice (assembly, recess, PE, bus wait), and alerts principals and parents by email and Telegram. Anyone can also check their location instantly without signing up.

## Architecture (fixed)
React app (Vite) on AWS Amplify Hosting
  -> API Gateway HTTP API ($default stage)
  -> Lambda running FastAPI via Mangum
  -> DynamoDB, SNS, Amazon Bedrock (optional)
EventBridge Scheduler (06:00 Asia/Kolkata) -> second Lambda "daily_check" that reuses the same `app/` package.
Telegram webhook -> same FastAPI app. Infrastructure is defined in `template.yaml` (AWS SAM).

## Stack (do not change or add dependencies without asking)
- Backend: Python 3.12, FastAPI, Pydantic v2, pydantic-settings, Mangum, boto3. Dev: pytest, httpx, moto, ruff.
- Frontend: React 18, Vite, React Router, Recharts, plain CSS with CSS variables. JavaScript (not TypeScript). Dev: Vitest, React Testing Library.
- Outbound HTTP from the backend uses the standard library (`urllib.request`) with timeouts.
- Air data: Open-Meteo Air Quality API and Geocoding API (no API key).

## Repo map
- `backend/app/` : `main.py`, `config.py`, `deps.py`, `routers/`, `schemas/`, `services/`, `repositories/`, `core/`
- `backend/handlers/` : `lambda_api.py` (Mangum handler), `daily_check.py` (scheduled job)
- `backend/tests/`, `backend/scripts/`
- `frontend/src/` : `api/`, `pages/`, `components/`, `hooks/`, `i18n/`, `styles/`, `utils/`, `test/`
- `docs/` : `FEATURES.md`, `architecture.md`, `thresholds.md`, `user-interview.md`, `demo-script.md`, `blog-draft.md`
- `template.yaml` at the repo root

## Backend rules
- Layers: routers are thin -> services hold pure logic (no AWS imports, unit tested) -> repositories are the only code that touches DynamoDB.
- Every route has Pydantic request and response models and `response_model=`. All routes live under `/api/v1`.
- Error body is always `{"error": {"code": "SNAKE_CASE", "message": "plain words"}}`. Never return stack traces.
- Inject repositories and settings with `Depends` so tests can override them.
- Define routes with plain `def` (boto3 is blocking), not `async def`, unless nothing blocks.
- Settings come from environment variables via `app/config.py`. Keep `.env.example` updated (names only).
- `USE_MEMORY_DB=true` switches to in-memory repositories with demo schools, so the frontend can be developed with no AWS.
- DynamoDB: convert float to Decimal on write and back on read, only inside repositories.
- Every external call (Open-Meteo, Bedrock, Telegram) has a timeout and a fallback. One school failing never stops the others.
- PM2.5 thresholds live only in `services/classify.py` as `LEVELS`, `LEVELS_SENSITIVE`, `ACTIVITY_FACTOR`, each marked `TODO verify against CPCB guidance`. Never invent health claims. Responses carry the disclaimer: "Informational only, not medical advice."
- Write only to `/tmp` inside Lambda.

## Frontend rules
- Functional components and hooks. One component per file, PascalCase names.
- All HTTP goes through `src/api/client.js`. The base URL comes from `import.meta.env.VITE_API_URL`. Nothing secret ever goes in the frontend (`VITE_` variables are public).
- Every screen has loading, empty and error states.
- Mobile first. Colour is never the only signal: always show the words GREEN/YELLOW/RED and an icon. Body text at least 16px, large tap targets, good contrast.
- All visible text comes from `src/i18n/en.json`, `hi.json`, `mr.json`. No hardcoded strings in components.
- No `dangerouslySetInnerHTML`. No inline secrets. Keep the bundle small.

## Commands
- Backend tests: `cd backend && python -m pytest -q`
- Backend lint: `cd backend && ruff check .`
- Run API locally: `cd backend && USE_MEMORY_DB=true uvicorn app.main:app --reload --port 8000` (docs at /docs)
- Frontend: `cd frontend && npm install`, `npm run dev`, `npm test`, `npm run build`
- Infra: `sam validate --lint`, `sam build`. `sam deploy` ONLY when I ask.

## Never do without asking
- Run `sam deploy`, `sam delete`, or any `aws` command that creates, changes or deletes cloud resources or costs money.
- Read, print or commit `~/.aws`, `.env`, tokens or keys.
- Run `git commit`, `git push`, or change Git history. I commit myself.
- Add features, files, dependencies or AWS services that are not part of the current task.
- Store child names, medical details or exact user locations. The only health data stored is a `sensitive` true/false flag.

## Definition of done
Tests pass and lint is clean. No secrets in code. API docs and `docs/` updated if behavior changed. End every task with: (1) files changed, (2) exact commands I run to verify, (3) anything you are unsure about.
