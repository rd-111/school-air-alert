import { lazy, Suspense, useState } from "react";
import { Link, Route, Routes } from "react-router-dom";
import en from "./i18n/en.json";
import hi from "./i18n/hi.json";
import mr from "./i18n/mr.json";

const DashboardPage = lazy(() => import("./pages/DashboardPage.jsx"));
const ReportPage = lazy(() => import("./pages/ReportPage.jsx"));
const PosterPage = lazy(() => import("./pages/PosterPage.jsx"));

const languages = { en, hi, mr };

export default function App() {
  const [language, setLanguage] = useState("en");
  const labels = languages[language];

  return (
    <>
      <div className="language-bar">
        <nav className="app-nav" aria-label={labels.siteNavigation}>
          <Link to="/">{labels.dashboardLink}</Link>
          <Link to="/report">{labels.reportLink}</Link>
          <Link to="/poster?school_id=demo-school">{labels.posterLink}</Link>
        </nav>
        <label htmlFor="language-select">{labels.languageLabel}</label>
        <select
          id="language-select"
          value={language}
          onChange={(event) => setLanguage(event.target.value)}
        >
          <option value="en">{labels.languages.en}</option>
          <option value="hi">{labels.languages.hi}</option>
          <option value="mr">{labels.languages.mr}</option>
        </select>
      </div>
      <Suspense fallback={<RouteLoading labels={labels} />}>
        <Routes>
          <Route path="/" element={<DashboardPage labels={labels} />} />
          <Route path="/report" element={<ReportPage labels={labels} />} />
          <Route path="/poster" element={<PosterPage labels={labels} />} />
          <Route path="*" element={<DashboardPage labels={labels} />} />
        </Routes>
      </Suspense>
    </>
  );
}

function RouteLoading({ labels }) {
  return (
    <main className="state-page" role="status">
      <section className="panel state-panel">
        <h1>{labels.loadingTitle}</h1>
        <p>{labels.loadingMessage}</p>
      </section>
    </main>
  );
}
