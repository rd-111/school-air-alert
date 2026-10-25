import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { loadSchoolStatus } from "../api/client.js";
import { formatPm25WithUnit } from "../utils/formatPm25.js";

export default function PosterPage({ labels }) {
  const [searchParams] = useSearchParams();
  const schoolId = searchParams.get("school_id");
  const [status, setStatus] = useState(null);
  const [state, setState] = useState(schoolId ? "loading" : "empty");

  useEffect(() => {
    let active = true;
    if (!schoolId) return undefined;
    loadSchoolStatus(schoolId).then((result) => {
      if (active) {
        setStatus(result);
        setState("ready");
      }
    }).catch(() => {
      if (active) setState("error");
    });
    return () => { active = false; };
  }, [schoolId]);

  if (state === "loading") return <PosterState title={labels.loadingTitle} message={labels.loadingMessage} role="status" />;
  if (state === "error") return <PosterState title={labels.errorTitle} message={labels.errorMessage} role="alert" />;
  if (state === "empty") return <PosterState title={labels.posterNeedsSchool} message={labels.posterQueryHelp} role="status" />;

  const level = status.status.toLowerCase();
  const date = status.date || status.retrieved_at.slice(0, 10);
  const best = status.best_window ? `${formatTime(status.best_window.start)}–${formatTime(status.best_window.end)}` : labels.noWindow;
  const worst = status.worst_window ? `${formatTime(status.worst_window.start)}–${formatTime(status.worst_window.end)}` : labels.noWindow;
  return (
    <main className="poster-page">
      <div className="print-controls"><Link to="/">{labels.backToDashboard}</Link><button type="button" onClick={() => window.print()}>{labels.printPoster}</button></div>
      {status.mode === "demo" && <p className="demo-badge">{labels.demoNotice}</p>}
      <article className={`poster-card status-${level}`}>
        <header className="poster-header">
          <p className="eyebrow">{labels.productEyebrow}</p>
          <h1>{status.school.name}</h1>
          <p className="poster-date">{date}</p>
        </header>
        <div className="poster-status"><span aria-hidden="true">{status.status === "GREEN" ? "✓" : status.status === "YELLOW" ? "!" : status.status === "RED" ? "⌂" : "i"}</span><strong>{labels.status[level]}</strong></div>
        <section className="poster-summary" aria-label={labels.posterForecastSummary}>
          <div><span>{labels.averagePm25}</span><strong>{formatPm25WithUnit(status.average_pm25, labels.pm25Unit)}</strong></div>
          <div><span>{labels.peakPm25}</span><strong>{formatPm25WithUnit(status.peak_pm25, labels.pm25Unit)}</strong></div>
        </section>
        <section className="poster-advice-section">
          <h2>{labels.activityAdvice}</h2>
          <ul className="poster-advice">
            {labels.posterAdvice[level].map((line) => <li key={line}>{line}</li>)}
          </ul>
        </section>
        <section className="poster-windows" aria-label={labels.activityWindowsTitle}>
          <p><span>{labels.bestWindowLabel}</span><strong>{best}</strong></p>
          <p><span>{labels.worstWindowLabel}</span><strong>{worst}</strong></p>
        </section>
        <footer>
          <p>{status.mode === "demo" ? labels.disclaimer : labels.liveDisclaimer}</p>
          <p>{labels.posterSource}: {status.source?.provider || status.source?.model || "—"}</p>
          {status.retrieved_at && <p>{labels.retrievedAt}: {formatDateTime(status.retrieved_at)}</p>}
        </footer>
      </article>
    </main>
  );
}

function formatTime(value) {
  return new Intl.DateTimeFormat(undefined, { hour: "2-digit", minute: "2-digit", hour12: false, timeZone: "Asia/Kolkata" }).format(new Date(value));
}

function formatDateTime(value) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium", timeStyle: "short", timeZone: "Asia/Kolkata",
  }).format(new Date(value));
}

function PosterState({ title, message, role }) {
  return <main className="state-page"><section className="panel state-panel" role={role} aria-live={role === "alert" ? "assertive" : "polite"}><h1>{title}</h1><p>{message}</p></section></main>;
}
