# Contributing to School Air Alert

Thanks for considering a contribution. This project helps school staff use
PM2.5 forecasts as one input when planning outdoor activities. It is a
decision-support prototype, not a sensor network or medical advice.

## Repository map

- `frontend/` — React/Vite app, page components, translations, and frontend tests.
- `backend/app/` — FastAPI routes, schemas, services, configuration, and
  repositories.
- `backend/handlers/` — Lambda API and scheduled processing entry points.
- `backend/tests/` — backend unit and API tests with fixtures/mocks.
- `docs/` — feature specification, architecture, setup, deployment, and manual
  testing references.
- `template.yaml`, `amplify.yml` — AWS SAM and Amplify configuration; their
  presence does not mean the project is deployed.

## Development setup

Install Git, Python 3.12, Node.js 22.12 or newer, and npm. Follow
[`docs/LOCAL_DEVELOPMENT.md`](docs/LOCAL_DEVELOPMENT.md) for platform-specific
setup and two-terminal startup instructions. Backend tests use local mocks;
do not add real provider calls or credentials to tests.

## Checks before opening a pull request

Backend, from `backend/`:

```sh
python -m pytest -q
ruff check .
```

Frontend, from `frontend/`:

```sh
npm ci
npm test -- --run
npm run build
```

The GitHub Actions workflow runs these backend and frontend checks for pushes
and pull requests. Local results do not prove that live providers or AWS
integrations work. Preserve test failures and report hangs; do not skip tests or
weaken assertions to produce a passing result.

## Contribution workflow

1. Fork the repository and create a focused branch, for example
   `fix/forecast-empty-state` or `docs/windows-setup`.
2. Read `AGENTS.md`, `docs/AGENTS.md`, and the relevant feature entry in
   `docs/FEATURES.md` before changing behavior.
3. Make a small change that preserves existing architecture and public API
   behavior where practical. Add or update tests for behavior changes.
4. Run the relevant checks above and `git diff --check`.
5. Open a pull request with the problem, approach, tests actually run, and any
   limitations or follow-up decisions.

Do not include generated build output, caches, virtual environments, local
databases, `.env` files, credentials, tokens, private contact information, or
unrelated changes. Never claim provider, notification, or deployment success
without direct verification. Use safe fictional examples in tests and docs.

## Coding and product conventions

- Keep provider access, business rules, HTTP routes, and UI concerns separated.
- Keep PM2.5 values in `µg/m³` and distinguish forecast data from observation.
- Do not change classification thresholds or describe them as official CPCB
  categories without approved evidence.
- Keep missing data explicit; missing readings must not be treated as GREEN.
- Treat F20 detections and modeled wind as possible context, never proof of
  smoke exposure.
- Keep user-facing strings in the existing English, Hindi, and Marathi locale
  files when adding UI text.
- Do not add dependencies, AWS services, or new policy behavior without a
  documented need and review.

## Reporting bugs and proposing work

Use the repository's GitHub issue form to report a reproducible bug or propose
a focused improvement. Include steps, expected and actual behavior, relevant
route or command, and sanitized logs. Do not upload `.env` files, credentials,
school/child personal data, or screenshots containing private details. For
security-sensitive issues, avoid posting secrets in a public issue and contact
the repository maintainers through a private channel available to you.

There is no `LICENSE` file in the current repository. Please do not assume that
contributions or project code are covered by an open-source license until the
maintainers add one.
