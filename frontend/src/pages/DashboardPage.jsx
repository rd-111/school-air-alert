import { useCallback, useEffect, useState } from "react";
import { loadDashboardData } from "../api/client.js";
import ActivityWindows from "../components/ActivityWindows.jsx";
import HourlyForecastChart from "../components/HourlyForecastChart.jsx";
import StatusCard from "../components/StatusCard.jsx";

export default function DashboardPage({ labels }) {
  const [data, setData] = useState(null);
  const [state, setState] = useState("loading");
  const [attempt, setAttempt] = useState(0);

  const load = useCallback(async () => {
    setState("loading");
    try {
      const result = await loadDashboardData();
      setData(result);
      setState(result ? "ready" : "empty");
    } catch {
      setData(null);
      setState("error");
    }
  }, []);

  useEffect(() => {
    load();
  }, [load, attempt]);

  if (state === "loading") {
    return <StatePanel title={labels.loadingTitle} message={labels.loadingMessage} />;
  }

  if (state === "empty") {
    return <StatePanel title={labels.emptyTitle} message={labels.emptyMessage} />;
  }

  if (state === "error") {
    return (
      <StatePanel
        title={labels.errorTitle}
        message={labels.errorMessage}
        actionLabel={labels.retry}
        onAction={() => setAttempt((value) => value + 1)}
      />
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
        <span className="demo-badge" aria-label={labels.demoNotice}>
          {labels.demoNotice}
        </span>
      </header>

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
      </section>

      <ActivityWindows data={data} labels={labels} />

      <footer className="disclaimer">{labels.disclaimer}</footer>
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
