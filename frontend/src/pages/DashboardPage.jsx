import { useCallback, useEffect, useState } from "react";
import { loadDashboardData } from "../api/client.js";
import ActivityWindows from "../components/ActivityWindows.jsx";
import HourlyForecastChart from "../components/HourlyForecastChart.jsx";
import StatusCard from "../components/StatusCard.jsx";
import LocationForm from "../components/LocationForm.jsx";
import HourlyReadings from "../components/HourlyReadings.jsx";
import SchoolForms from "../components/SchoolForms.jsx";
import TelegramLink from "../components/TelegramLink.jsx";
import ActivityAdvice from "../components/ActivityAdvice.jsx";
import SmokeHint from "../components/SmokeHint.jsx";

const SELECTED_SCHOOL_KEY = "school-air-alert-selected-school";

function readSavedSchool() {
  try {
    const school = JSON.parse(window.localStorage.getItem(SELECTED_SCHOOL_KEY));
    if (
      school && typeof school.school_id === "string" && typeof school.name === "string"
      && Number.isFinite(school.latitude) && school.latitude >= -90 && school.latitude <= 90
      && Number.isFinite(school.longitude) && school.longitude >= -180 && school.longitude <= 180
    ) return school;
  } catch {
    // Ignore invalid or unavailable local storage and use the default location.
  }
  return null;
}

export default function DashboardPage({ labels }) {
  const [savedSchool] = useState(readSavedSchool);
  const [data, setData] = useState(null);
  const [state, setState] = useState("loading");
  const [attempt, setAttempt] = useState(0);
  const [location, setLocation] = useState(() => savedSchool
    ? { latitude: savedSchool.latitude, longitude: savedSchool.longitude }
    : { latitude: 19.076, longitude: 72.8777 });
  const [locationError, setLocationError] = useState(false);
  const [selectedSchoolId, setSelectedSchoolId] = useState(savedSchool?.school_id || "");
  const [selectedSchool, setSelectedSchool] = useState(savedSchool);

  useEffect(() => {
    let active = true;
    setState("loading");
    loadDashboardData(location, labels).then((result) => {
      if (!active) return;
      setData(result);
      setState(result ? "ready" : "empty");
    }).catch(() => {
      if (!active) return;
      setData(null);
      setState("error");
    });
    return () => { active = false; };
  }, [labels, location, attempt]);

  function updateLocation(nextLocation) {
    if (!nextLocation) {
      setLocationError(true);
      return;
    }
    setLocationError(false);
    setLocation(nextLocation);
    setAttempt((value) => value + 1);
  }

  const handleSchoolChange = useCallback((school) => {
    if (!school) return;
    setSelectedSchoolId(school.school_id);
    setSelectedSchool(school);
    try {
      window.localStorage.setItem(SELECTED_SCHOOL_KEY, JSON.stringify(school));
    } catch {
      // Selection remains available for this page even when storage is unavailable.
    }
    setLocation((current) => (
      current.latitude === school.latitude && current.longitude === school.longitude
        ? current
        : { latitude: school.latitude, longitude: school.longitude }
    ));
  }, []);

  return (
    <main className="dashboard" aria-busy={state === "loading"}>
      <header className="page-header">
        <div>
          <p className="eyebrow">{labels.productEyebrow}</p>
          <h1>{labels.pageTitle}</h1>
          <p className="school-name">{selectedSchool?.name || data?.schoolName}</p>
        </div>
        {data && state === "ready" && (
          <span className={`demo-badge ${data.mode === "live" ? "live-badge" : ""}`} aria-label={data.mode === "live" ? labels.liveNotice : labels.demoNotice}>
            {data.mode === "live" ? labels.liveNotice : labels.demoNotice}
          </span>
        )}
      </header>

      <SchoolForms
        labels={labels}
        selectedSchoolId={selectedSchoolId}
        selectedSchool={selectedSchool}
        onSchoolChange={handleSchoolChange}
      />
      <LocationForm
        key={`${location.latitude},${location.longitude}`}
        location={location}
        onChange={updateLocation}
        labels={labels}
      />
      {locationError && <p className="form-error" role="alert">{labels.invalidLocation}</p>}

      {state === "loading" && <StatePanel title={labels.loadingTitle} message={labels.loadingMessage} />}
      {state === "empty" && <StatePanel title={labels.emptyTitle} message={labels.emptyMessage} />}
      {state === "error" && (
        <StatePanel
          title={labels.errorTitle}
          message={labels.errorMessage}
          actionLabel={labels.retry}
          onAction={() => setAttempt((value) => value + 1)}
        />
      )}

      {state === "ready" && data && <>
        <TelegramLink labels={labels} />
        <p className="location-note">{labels.locationNote} {data.location?.latitude ?? location.latitude}{labels.coordinateSeparator} {data.location?.longitude ?? location.longitude}</p>
        <StatusCard data={data} labels={labels} />

        <section className="panel chart-panel" aria-labelledby="forecast-title">
          <div className="section-heading">
            <div>
              <p className="eyebrow">{labels.forecastEyebrow}</p>
              <h2 id="forecast-title">{labels.forecastTitle}</h2>
            </div>
            <span className="unit-label">{labels.pm25Unit}</span>
          </div>
          <HourlyForecastChart hourly={data.hourly} bestWindow={data.bestWindow} labels={labels} />
          <HourlyReadings hourly={data.hourly} labels={labels} />
        </section>

        <section className="panel forecast-reliability" aria-labelledby="forecast-reliability-title">
          <h2 id="forecast-reliability-title">{labels.forecastReliabilityTitle}</h2>
          <p className="reliability-status">{labels.forecastAccuracyUnavailable}</p>
          <p>{labels.forecastReliabilityNote}</p>
          {data.mode === "live" && (
            <dl className="reliability-details">
              {data.source?.provider && <div><dt>{labels.forecastProvider}</dt><dd>{data.source.provider}</dd></div>}
              {data.retrievedAt && <div><dt>{labels.retrievedAt}</dt><dd>{new Date(data.retrievedAt).toLocaleString()}</dd></div>}
              {data.hourly?.length > 0 && <div><dt>{labels.forecastHorizon}</dt><dd>{data.hourly.length} {labels.forecastHours}</dd></div>}
            </dl>
          )}
        </section>

        <ActivityWindows data={data} labels={labels} />
        <ActivityAdvice recommendations={data.activityGuidance} labels={labels} />
        <SmokeHint schoolId={selectedSchoolId} dataMode={data.mode} labels={labels} />

        {data.source && <p className="source-note">{labels.dataSource}: {data.source.attribution} <a href={data.source.provider_url} target="_blank" rel="noreferrer">{labels.providerOpenMeteo}</a> · <a href={data.source.model_url} target="_blank" rel="noreferrer">{labels.providerCams}</a> · {labels.sourceLicense}: {data.source.license} · {labels.retrievedAt}: {new Date(data.retrievedAt).toLocaleString()}</p>}
        {data.stale && <p className="form-error" role="alert">{labels.staleDataNotice}</p>}
        <footer className="disclaimer">{data.mode === "demo" ? labels.disclaimer : `${data.policyNote} ${labels.activityAdvice} ${labels.disclaimer}`}</footer>
      </>}
    </main>
  );
}

function StatePanel({ title, message, actionLabel, onAction }) {
  return (
    <section
      className="panel state-panel dashboard-state-panel"
      aria-live={actionLabel ? "assertive" : "polite"}
      role={actionLabel ? "alert" : "status"}
    >
      <span className="state-icon" aria-hidden="true">
        {actionLabel ? "⚠️" : "🌿"}
      </span>
      <h1>{title}</h1>
      <p>{message}</p>
      {actionLabel && <button onClick={onAction}>{actionLabel}</button>}
    </section>
  );
}
