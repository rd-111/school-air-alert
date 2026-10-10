import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { loadSchoolStatus } from "../api/client.js";

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

  if (state === "loading") return <PosterState title={labels.loadingTitle} message={labels.loadingMessage} />;
  if (state === "error") return <PosterState title={labels.errorTitle} message={labels.errorMessage} />;
  if (state === "empty") return <PosterState title={labels.posterNeedsSchool} message={labels.posterQueryHelp} />;

  const level = status.status.toLowerCase();
  const date = status.date || status.retrieved_at.slice(0, 10);
  const best = status.best_window ? `${formatTime(status.best_window.start)}–${formatTime(status.best_window.end)}` : labels.noWindow;
  const worst = status.worst_window ? `${formatTime(status.worst_window.start)}–${formatTime(status.worst_window.end)}` : labels.noWindow;
  return (
    <main className="poster-page">
      <div className="print-controls"><Link to="/">{labels.backToDashboard}</Link><button onClick={() => window.print()}>{labels.printPoster}</button></div>
      {status.mode === "demo" && <p className="demo-badge">{labels.demoNotice}</p>}
      <article className={`poster-card status-${level}`}>
        <p className="eyebrow">{labels.productEyebrow}</p>
        <h1>{status.school.name}</h1>
        <p className="poster-date">{date}</p>
        <div className="poster-status"><span aria-hidden="true">{status.status === "GREEN" ? "✅" : status.status === "YELLOW" ? "⚠️" : status.status === "RED" ? "🏠" : "ℹ️"}</span><strong>{labels.status[level]}</strong></div>
        <ul className="poster-advice">
          {labels.posterAdvice[level].map((line) => <li key={line}>{line}</li>)}
        </ul>
        <p>{labels.bestWindowLabel}: {best}</p>
        <p>{labels.worstWindowLabel}: {worst}</p>
        <footer>{status.mode === "demo" ? labels.disclaimer : labels.liveDisclaimer}</footer>
      </article>
    </main>
  );
}

function formatTime(value) {
  return new Intl.DateTimeFormat(undefined, { hour: "2-digit", minute: "2-digit", hour12: false, timeZone: "Asia/Kolkata" }).format(new Date(value));
}

function PosterState({ title, message }) {
  return <main className="state-page"><section className="panel state-panel"><h1>{title}</h1><p>{message}</p></section></main>;
}
