# 2–3 minute demo script

This is a walkthrough, not a claim that a live deployment or notification
delivery has been verified. Start in demo mode for a reliable presentation; the
dashboard labels illustrative data as demo data.

## Before the demo

- From `backend/`, start the local API with `USE_MEMORY_DB=true` if showing live
  forecasts: `python -m uvicorn app.main:app --reload --port 8017`.
- From `frontend/`, start Vite with
  `VITE_DATA_MODE=demo npm run dev -- --port 5174`.
- To demonstrate provider-backed data instead, use
  `VITE_DATA_MODE=live VITE_API_URL=http://localhost:8017`; this needs internet
  access to Open-Meteo. Keep demo mode as a fallback presentation plan, not a
  silent fallback from a failed live request.

## Walkthrough

1. **Problem and users (20 seconds):** “School staff need a quick way to review
   air-quality forecasts before deciding what to do with outdoor activities.”
2. **Dashboard (40 seconds):** show the status card, hourly forecast chart, and
   best/worst activity windows. Point out that the status is a project policy
   label and forecast decision support, not an official government AQI reading
   or a safety guarantee. In demo mode, call out the demo badge.
3. **Location and detail (25 seconds):** enter valid latitude/longitude and
   explain that live mode requests the backend forecast endpoint. If live mode
   is enabled, show the source and retrieval time; do not describe a failed or
   stale request as current data.
4. **School tools (25 seconds):** show school registration/subscription forms,
   the history report, and the printable notice poster. Explain that local
   memory mode is temporary and does not deliver email.
5. **Telegram and limits (25 seconds):** show the public bot link and explain
   that real Telegram replies require server-side token/secret configuration
   and a configured webhook. Do not claim delivery unless a real test confirms
   it. Close by noting that F19 accuracy scoring and F20 smoke hints remain
   pending approved data and methods.

Finish by inviting the judges to try the language selector and the demo/live
mode distinction.
