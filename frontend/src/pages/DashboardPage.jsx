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

export default function DashboardPage({ labels }) {
  const [data, setData] = useState(null);
  const [state, setState] = useState("loading");
  const [attempt, setAttempt] = useState(0);
  const [location, setLocation] = useState({ latitude: 19.076, longitude: 72.8777 });
  const [locationError, setLocationError] = useState(false);

  const load = useCallback(async () => {
    setState("loading");
    try {
      const result = await loadDashboardData(location, labels);
      setData(result);
      setState(result ? "ready" : "empty");
    } catch {
      setData(null);
      setState("error");
    }
  }, [labels, location]);

  useEffect(() => {
    load();
  }, [load, attempt]);

  function updateLocation(nextLocation) {
    if (!nextLocation) {
      setLocationError(true);
      return;
    }
    setLocationError(false);
    setLocation(nextLocation);
    setAttempt((value) => value + 1);
  }

  if (state === "loading") {
    return <StatePanel title={labels.loadingTitle} message={labels.loadingMessage} />;
  }

  if (state === "empty") {
    return <StatePanel title={labels.emptyTitle} message={labels.emptyMessage} />;
  }

  if (state === "error") {
    return (
      <div className="dashboard">
        <LocationForm location={location} onChange={updateLocation} labels={labels} />
        {locationError && <p className="form-error" role="alert">{labels.invalidLocation}</p>}
        <StatePanel
          title={labels.errorTitle}
          message={labels.errorMessage}
          actionLabel={labels.retry}
          onAction={() => setAttempt((value) => value + 1)}
        />
      </div>
    );
  }

  return (
    <main className="dashboard">
      <header className="page-header">
        <div>
          <p className="eyebrow">{labels.productEyebrow}</p>
          <h1>{labels.pageTitle}</h1>
          <p className="school-name">{data.schoolName}</p>
        </div>
        <span className={`demo-badge ${data.mode === "live" ? "live-badge" : ""}`} aria-label={data.mode === "live" ? labels.liveNotice : labels.demoNotice}>
          {data.mode === "live" ? labels.liveNotice : labels.demoNotice}
        </span>
      </header>

      <LocationForm location={location} onChange={updateLocation} labels={labels} />
      <SchoolForms labels={labels} />
      <TelegramLink labels={labels} />
      {locationError && <p className="form-error" role="alert">{labels.invalidLocation}</p>}
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

      <ActivityWindows data={data} labels={labels} />
      <ActivityAdvice recommendations={data.activityGuidance} labels={labels} />

      {data.source && <p className="source-note">{labels.dataSource}: {data.source.attribution} <a href={data.source.provider_url} target="_blank" rel="noreferrer">{labels.providerOpenMeteo}</a> · <a href={data.source.model_url} target="_blank" rel="noreferrer">{labels.providerCams}</a> · {labels.sourceLicense}: {data.source.license} · {labels.retrievedAt}: {new Date(data.retrievedAt).toLocaleString()}</p>}
      {data.stale && <p className="form-error" role="alert">{labels.staleDataNotice}</p>}
      <footer className="disclaimer">{data.mode === "demo" ? labels.disclaimer : `${data.policyNote} ${labels.activityAdvice} ${labels.disclaimer}`}</footer>
    </main>
  );
}

function StatePanel({ title, message, actionLabel, onAction }) {
  return (
    <main className="state-page">
      <section className="panel state-panel" aria-live="polite">
        <span className="state-icon" aria-hidden="true">
          {actionLabel ? "⚠️" : "🌿"}
        </span>
        <h1>{title}</h1>
        <p>{message}</p>
        {actionLabel && <button onClick={onAction}>{actionLabel}</button>}
      </section>
    </main>
  );
}
