import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { loadSchoolHistory, loadSchools } from "../api/client.js";

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

  if (state === "loading") return <PageState title={labels.loadingTitle} message={labels.loadingMessage} />;
  if (state === "error") return <PageState title={labels.errorTitle} message={labels.errorMessage} />;
  if (state === "empty") return <PageState title={labels.emptyTitle} message={labels.noSchools} />;

  const counts = report.counts;
  const protectedHours = (counts.yellow + counts.red) * 2;
  return (
    <main className="dashboard report-page">
      <Link to="/" className="back-link">{labels.backToDashboard}</Link>
      <p className="eyebrow">{labels.reportEyebrow}</p>
      <h1>{labels.reportTitle}</h1>
      <label className="school-picker">{labels.schoolPicker}
        <select value={schoolId} onChange={(event) => setSchoolId(event.target.value)}>
          {schools.map((school) => <option key={school.school_id} value={school.school_id}>{school.name}</option>)}
        </select>
      </label>
      <p>{labels.forecastHistoryNote}</p>
      {report.mode === "demo" && <p className="demo-badge">{labels.demoNotice}</p>}
      {report.daily.length === 0 ? <p className="panel no-history">{labels.noHistory}</p> : (
        <div className="report-counts">
          {[["GREEN", counts.green], ["YELLOW", counts.yellow], ["RED", counts.red]].map(([status, count]) => (
            <article className={`panel count-card status-${status.toLowerCase()}`} key={status}>
              <span>{labels.status[status.toLowerCase()]}</span><strong>{count}</strong>
            </article>
          ))}
        </div>
      )}
      <section className="panel protected-hours">
        <p className="eyebrow">{labels.protectedHoursLabel}</p>
        <strong>{protectedHours}</strong><span>{labels.hoursUnit}</span>
        <p>{labels.protectedHoursCalculation}</p>
      </section>
    </main>
  );
}

function PageState({ title, message }) {
  return <main className="state-page"><section className="panel state-panel"><h1>{title}</h1><p>{message}</p></section></main>;
}
