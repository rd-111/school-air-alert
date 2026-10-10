# Pending product and verification decisions

These items are intentionally unavailable until their data sources and rules
are agreed. The dashboard must not display placeholder accuracy or smoke claims.

## F19 — Forecast accuracy meter

The feature specification asks for yesterday's forecast compared with what
occurred, summarized as matched statuses over the previous 10 days, and stored
in History. It does not identify an authoritative observation source or define
how school forecasts are matched to observations. Open-Meteo historical or
archived forecast output is not actual observed ground truth.

Decisions needed:

1. Which observation provider is authoritative and available for the schools
   being served (for example, a named government monitoring network and API)?
2. How is a school matched to an observation station, and what distance or
   station-quality rules apply when there are several stations or none?
3. Which forecast is scored: the forecast issued at 06:00 for the school day,
   or another lead time? Which local date and timezone define the match?
4. How are observed and forecast hourly values aggregated to a daily status,
   and how are missing or invalid observations treated in the 10-day count?
5. What observation provenance, timestamp, and schema are retained in History?

After approval, implement an isolated observation-provider interface and
mocked tests before exposing the meter. Until then, no accuracy percentage or
sample score is presented as real.

## F20 — NASA FIRMS smoke-source hint

The feature specification calls for hotspots in the previous 24 hours that are
upwind of a school and permits a smoke-contribution sentence when a cluster is
found. The repository has no wind-data provider or approved calculation for
“upwind” or “cluster.” A FIRMS hotspot is a satellite detection; by itself it
does not establish an active fire at the school or show that smoke caused its
PM2.5 reading.

Decisions needed:

1. Approve the server-side NASA FIRMS integration and secret configuration for
   its MAP_KEY. No key belongs in the frontend or source control.
2. Select the wind provider, measurement height, observation/forecast time, and
   handling for missing or stale wind data.
3. Define the geographic search area, what counts as upwind, and the allowed
   wind-direction uncertainty.
4. Define a hotspot cluster (count, distance, acquisition time, sensor/source,
   confidence, and any fire-radiative-power filters).
5. Approve the evidence threshold and wording for any alert. The specified
   “likely contributing” sentence must not appear from a hotspot alone.

Proposed design after approval: a backend-only, optional FIRMS service with a
bounded request, validated coordinates/area, normalized detection timestamps,
source attribution, and explicit `unconfigured`, `unavailable`, `no_candidate`,
or evidence-backed result states. Its failure must not block the forecast or
dashboard. No such service or result schema is currently implemented.

## Backend test environment

The local synchronous ASGI test hang is reproducible, but its cause is not
identified. AnyIO and asyncio worker functions finish in worker threads, while
the event loop does not process their result callback until timeout; the same
behavior appears in both project virtual environments. Package metadata shows
the installed FastAPI, Starlette, HTTPX, and AnyIO versions satisfy their
declared dependency ranges. The seven route tests remain enabled; a verified
non-hanging subset can be run with the command in `README.md`. Do not interpret
that subset as a full-suite pass.
