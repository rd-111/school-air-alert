# Pending product and verification decisions

The F19 accuracy result and F20 smoke-attribution claim remain unavailable
until their data sources and rules are agreed. The dashboard must not display
placeholder accuracy or unsupported smoke claims.

## F19 — Forecast accuracy indicator

Implemented an honest dashboard status: “Forecast accuracy not yet measured —
historical validation data is unavailable.” The dashboard also explains that
the output is a model forecast, not a school-site measurement, and that a
recent update does not establish accuracy. In live mode it displays provider,
retrieval time, and the number of displayed forecast hours only when supplied
by the current forecast response. This metadata is descriptive and is not a
confidence or accuracy measure. Demo mode does not show live-provider metadata.

Accuracy remains unmeasured. The feature specification asks for yesterday's
forecast compared with what occurred, summarized as matched statuses over the
previous 10 days, and stored in History. It does not identify an authoritative
observation source or define how school forecasts are matched to observations.
Open-Meteo historical or archived forecast output is not actual observed ground
truth.

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

The optional service queries the NASA FIRMS Area API server-side for registered
school coordinates. It requests a bounded 2-day VIIRS NOAA-21 NRT CSV area and
filters to detections acquired within the preceding 24 hours and inside the
configured radius (default 25 km). NASA's `acq_date`/`acq_time` are normalized
as UTC acquisition timestamps. Exact duplicate platform/time/location rows
are removed. Pixel clusters use overlapping circumscribed disks based on
NASA's scan and track pixel dimensions, and are limited to the same platform
and acquisition minute. Clusters are not merged across satellites or passes.
Explicit states distinguish missing providers, missing/stale wind samples,
detections without a downwind vector, and possible modeled transport. Provider
failures do not block the forecast.

For every cluster, Open-Meteo Historical Forecast supplies modeled 10 m wind
at that cluster's coordinates and acquisition timestamp. Samples are matched
by UTC timestamp; wind-from direction is converted into an east/north
downwind vector, and components are interpolated only across adjacent hourly
records. A positive dot product with the cluster-to-school displacement is
the geometric “toward” test. This is a half-plane check, not a plume model; no
minimum speed or directional tolerance is applied. Zero wind, missing values,
records outside the available time range, or gaps larger than an hour are
indeterminate. The UI then shows the interim wording only when at least one
cluster passes this test.

The radius remains a search boundary, not a plume or exposure model. FIRMS
hotspots do not establish smoke at ground level, exposure at the school, or a
cause for PM2.5. The specified “Smoke from nearby fires is likely
contributing” sentence remains blocked.

Decisions still needed:

1. Confirm that the Open-Meteo model and its spatial resolution are adequate
   for the intended school context; Best Match can vary by location and the
   newest historical archive records may be unavailable.
2. Approve whether the geometric half-plane check is suitable for the interim
   potential-transport wording, and whether a plume-width or uncertainty model
   is required. No undocumented speed or angle cutoffs are used.
3. Define what evidence, such as independent observed smoke/air-quality data
   and a validated attribution method, could support the original causal
   “likely contributing” sentence. It is not emitted by this implementation.

The credential approach is established: request a free NASA FIRMS MAP_KEY and
configure `FIRMS_MAP_KEY` only in backend local secret configuration or the
SAM `FirmsMapKey` `NoEcho` parameter. Never use a frontend variable or commit
the key. The operational radius default is configurable through
`FIRMS_SEARCH_RADIUS_KM` / `FirmsSearchRadiusKm`; this does not resolve plume
relevance. Open-Meteo needs no API key. Its free API is restricted to
non-commercial use, is rate limited, has no uptime guarantee, and requires
CC BY attribution. The modeled provider is not live-verified in this project.

## Backend test environment

The `TestClient` hang was traced to the restricted Codex execution sandbox:
asyncio's Unix socketpair wakeup send raises `EPERM` there, leaving the portal
event loop asleep. Outside that sandbox, the isolated health test, all seven
previously affected route tests, and the complete backend suite passed (94
tests) on 2026-10-11. This is not an application or dependency workaround; do
not skip the route tests. A normal local terminal should run the full suite.
