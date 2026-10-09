# School Air Alert — Codex Rules

## Goal

Build a working hackathon MVP that helps schools monitor air quality and communicate Green, Yellow, or Red alerts to staff and parents.

## Workflow

* Read this file and inspect relevant files before every task.
* Make small, focused changes. Reuse existing code; avoid unnecessary files and dependencies.
* Before editing, state a brief plan and files to change. Wait for approval when the user requests it.
* Do not overwrite unrelated work.
* Keep code simple, readable, and beginner-friendly.
* Run relevant tests after changes when approved. Report commands and actual results.
* If blocked, explain the issue and suggest the smallest fix.
* Never claim a feature works unless it has been tested or verified.

## Architecture

* Python backend; keep business logic separate from UI and integrations.
* Keep frontend simple and demo-ready.
* Isolate air-quality data providers, alert classification, and notification delivery.
* Use mock/demo data until a real data source is selected and verified.
* Keep interfaces modular so data providers and notifications can be replaced easily.

## Air quality

* Clearly label demo data and prototype thresholds.
* Never invent live readings or misrepresent demo data as real.
* Verify authoritative standards and document units, averaging periods, and data sources before calling thresholds official.
* Alerts are informational, not medical or emergency advice.

## Security and AWS

* Never expose, print, read, or commit secrets or AWS credential files.
* Keep `.env`, `.aws/`, tokens, and private data out of Git.
* Use `.env.example` with placeholder values only.
* Never deploy, create paid resources, change IAM/permissions, or delete cloud resources without explicit approval.
* Prefer local tests and mock integrations before AWS integration.
* Never hardcode API keys.

## Testing and quality

* Add tests for business logic, boundaries, invalid inputs, and failures.
* Test without network access wherever possible.
* Handle missing data and API errors safely.
* Avoid unnecessary abstractions, dependencies, and large refactors.
* Keep setup and demo instructions in README.md.

## Hackathon delivery

* Prioritize a reliable end-to-end demo over extra features.
* Document setup, architecture, data sources, limitations, and demo steps.
* Keep commits small and meaningful.
* Before finishing, report: summary, changed files, tests/results, remaining issues, and next step.
* Do not claim AWS integration, live data, or notifications work unless verified.
