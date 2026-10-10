# Architecture

```mermaid
flowchart LR
  Browser[React dashboard on Vite / Amplify target] -->|HTTP /api/v1| API[FastAPI]
  API --> Forecast[Forecast assembly service]
  Forecast --> Provider[Open-Meteo Air Quality API / CAMS Global]
  Forecast --> Classify[School PM2.5 policy]
  Forecast --> Planner[School-hour window planner]
  API --> Health[Versioned health endpoint]
  API --> SchoolAPI[School, subscription, status and history routes]
  SchoolAPI --> SchoolRepo[Schools and Subscribers repositories]
  SchoolAPI --> HistoryRepo[History repository]
  Daily[06:00 IST EventBridge Scheduler] --> Job[Daily Lambda]
  Evening[19:00 IST EventBridge Scheduler] --> Job
  Job --> Forecast
  Job --> HistoryRepo
  Job --> SNS[Regular and sensitive SNS topics]
  Job --> Telegram[Telegram Bot API]
  Job --> NotifyRuns[Notification run claims / idempotency table]
  Job -. optional .-> Bedrock[Amazon Bedrock Converse]
```

The 19:00 schedule requests the next local calendar day's forecast with a
two-day provider horizon. The scheduled timestamp anchors its target date across
retries. Notification claims reduce duplicate delivery; live scheduler and
SNS/Telegram behavior have not been deployed or verified. F19 observed-data
comparison and F20 fire-source hints are absent pending data-source and policy
decisions.

The browser's API client has explicit demo and live modes. The live API returns
forecast provenance and retrieval time; it does not label forecast values as
measurements. FastAPI is wrapped by the existing Mangum handler, but AWS SAM
infrastructure and deployment have not been verified.
