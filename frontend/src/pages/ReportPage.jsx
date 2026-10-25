import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { loadSchoolHistory, loadSchools } from "../api/client.js";
import { formatPm25WithUnit } from "../utils/formatPm25.js";

export default function ReportPage({ labels }) {
  const [searchParams] = useSearchParams();
  const [schoolId, setSchoolId] = useState(searchParams.get("school_id") || "");
  const [schools, setSchools] = useState([]);
  const [report, setReport] = useState(null);
  const [state, setState] = useState("loading");

  useEffect(() => {
    let active = true;
    async function load() {
      setState("loading");
      try {
        const schoolList = await loadSchools(labels);
        if (!active) return;
        setSchools(schoolList);
        const selected = schoolId || schoolList[0]?.school_id;
        if (!selected) {
          setReport(null);
          setState("empty");
          return;
        }
        if (!schoolId) setSchoolId(selected);
        const result = await loadSchoolHistory(selected, 30);
        if (active) {
          setReport(result);
          setState("ready");
        }
      } catch {
        if (active) setState("error");
      }
    }
    load();
    return () => { active = false; };
  }, [labels, schoolId]);

  if (state === "loading") return <PageState title={labels.loadingTitle} message={labels.loadingMessage} role="status" />;
  if (state === "error") return <PageState title={labels.errorTitle} message={labels.errorMessage} role="alert" />;
  if (state === "empty") return <PageState title={labels.emptyTitle} message={labels.noSchools} role="status" />;

  const counts = report.counts;
  const protectedHours = (counts.yellow + counts.red) * 2;
  return (
    <main className="dashboard report-page">
      <Link to="/" className="back-link">{labels.backToDashboard}</Link>
      <header className="report-heading">
        <div>
          <p className="eyebrow">{labels.reportEyebrow}</p>
          <h1>{labels.reportTitle}</h1>
          <p className="report-period">{labels.reportPeriod.replace("{count}", String(report.days))}</p>
          <p>{labels.forecastHistoryNote}</p>
        </div>
        {report.mode === "demo" && <p className="demo-badge">{labels.demoNotice}</p>}
      </header>
      <section className="panel report-school-panel">
        <label className="school-picker">{labels.schoolPicker}
          <select value={schoolId} onChange={(event) => setSchoolId(event.target.value)}>
            {schools.map((school) => <option key={school.school_id} value={school.school_id}>{school.name}</option>)}
          </select>
        </label>
        <p className="report-school-name">{report.school.name}</p>
      </section>
      {report.daily.length === 0 ? (
        <p className="panel no-history" role="status">{labels.noHistory}</p>
      ) : (
        <>
          <section className="report-summary" aria-label={labels.reportStatusDistribution}>
            <div className="report-section-heading">
              <div>
                <p className="eyebrow">{labels.reportStatusDistribution}</p>
                <h2>{labels.daysRecorded.replace("{count}", String(report.daily.length))}</h2>
              </div>
            </div>
            <div className="report-counts">
              {[ ["GREEN", counts.green], ["YELLOW", counts.yellow], ["RED", counts.red] ].map(([status, count]) => (
                <article className={`panel count-card status-${status.toLowerCase()}`} key={status}>
                  <span>{labels.status[status.toLowerCase()]}</span><strong>{count}</strong>
                </article>
              ))}
            </div>
            {(counts.green + counts.yellow + counts.red) > 0 && (
              <div className="report-status-bar" aria-hidden="true">
                {[["green", counts.green], ["yellow", counts.yellow], ["red", counts.red]].map(([status, count]) => (
                  count > 0 && <span
                    className={`report-status-segment status-${status}`}
                    key={status}
                    style={{ flexGrow: count }}
                  />
                ))}
              </div>
            )}
          </section>
          <section className="panel report-history" aria-labelledby="report-history-title">
            <div className="report-section-heading">
              <div>
                <p className="eyebrow">{labels.historySectionEyebrow}</p>
                <h2 id="report-history-title">{labels.dailyForecasts}</h2>
              </div>
            </div>
            <ol className="report-days">
              {report.daily.map((day) => (
                <li className={`report-day status-${day.status.toLowerCase()}`} key={day.date}>
                  <time dateTime={day.date}>{day.date}</time>
                  <span className="report-day-status">{labels.status[day.status.toLowerCase()] || labels.status.unknown}</span>
                  <span>{labels.averagePm25}: <strong>{formatPm25WithUnit(day.average_pm25, labels.pm25Unit)}</strong></span>
                  <span>{labels.peakPm25}: <strong>{formatPm25WithUnit(day.peak_pm25, labels.pm25Unit)}</strong></span>
                </li>
              ))}
            </ol>
          </section>
          <section className="panel protected-hours">
            <div>
              <p className="eyebrow">{labels.protectedHoursLabel}</p>
              <p>{labels.protectedHoursCalculation}</p>
            </div>
            <strong>{protectedHours}<span>{labels.hoursUnit}</span></strong>
          </section>
        </>
      )}
    </main>
  );
}

function PageState({ title, message, role }) {
  return <main className="state-page"><section className="panel state-panel" role={role} aria-live={role === "alert" ? "assertive" : "polite"}><h1>{title}</h1><p>{message}</p></section></main>;
}
