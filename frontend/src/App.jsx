import { lazy, Suspense, useLayoutEffect, useState } from "react";
import { Link, NavLink, Route, Routes } from "react-router-dom";
import en from "./i18n/en.json";
import hi from "./i18n/hi.json";
import mr from "./i18n/mr.json";

const DashboardPage = lazy(() => import("./pages/DashboardPage.jsx"));
const ReportPage = lazy(() => import("./pages/ReportPage.jsx"));
const PosterPage = lazy(() => import("./pages/PosterPage.jsx"));

const languages = { en, hi, mr };
const THEME_STORAGE_KEY = "school-air-alert-theme";
const LANGUAGE_STORAGE_KEY = "school-air-alert-language";

function getInitialLanguage() {
  try {
    const savedLanguage = window.localStorage.getItem(LANGUAGE_STORAGE_KEY);
    return Object.prototype.hasOwnProperty.call(languages, savedLanguage) ? savedLanguage : "en";
  } catch {
    return "en";
  }
}

function getSavedTheme() {
  try {
    const savedTheme = window.localStorage.getItem(THEME_STORAGE_KEY);
    return savedTheme === "light" || savedTheme === "dark" ? savedTheme : null;
  } catch {
    return null;
  }
}

function getInitialTheme() {
  const savedTheme = getSavedTheme();
  if (savedTheme) return savedTheme;
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export default function App() {
  const [language, setLanguage] = useState(getInitialLanguage);
  const [theme, setTheme] = useState(getInitialTheme);
  const [themeIsSaved, setThemeIsSaved] = useState(() => getSavedTheme() !== null);
  const labels = languages[language];
  const nextTheme = theme === "dark" ? "light" : "dark";

  useLayoutEffect(() => {
    document.documentElement.dataset.theme = theme;
    if (themeIsSaved) {
      try {
        window.localStorage.setItem(THEME_STORAGE_KEY, theme);
      } catch {
        // Keep the theme usable even when browser storage is unavailable.
      }
    }
    document.querySelector('meta[name="theme-color"]')?.setAttribute(
      "content",
      theme === "dark" ? "#0a1118" : "#f6f9fb",
    );
  }, [theme, themeIsSaved]);

  return (
    <>
      <header className="language-bar">
        <Link className="brand-lockup" to="/" aria-label="School Air Alert home">
          <span className="brand-mark" aria-hidden="true">
            <svg viewBox="0 0 32 32" focusable="false">
              <path d="M16 3.5 27 8v7.1c0 6.4-4.5 11.2-11 13.4C9.5 26.3 5 21.5 5 15.1V8l11-4.5Z" />
              <path d="M9.5 16.5c2.2-2.3 4.4-2.3 6.5 0s4.3 2.3 6.5 0" />
              <path d="M11 12.2h10" />
            </svg>
          </span>
          <span className="brand-name">School Air Alert</span>
        </Link>
        <nav className="app-nav" aria-label={labels.siteNavigation}>
          <NavLink to="/" end className={({ isActive }) => isActive ? "active" : undefined}>{labels.dashboardLink}</NavLink>
          <NavLink to="/report" className={({ isActive }) => isActive ? "active" : undefined}>{labels.reportLink}</NavLink>
          <NavLink to="/poster?school_id=demo-school" className={({ isActive }) => isActive ? "active" : undefined}>{labels.posterLink}</NavLink>
        </nav>
        <label htmlFor="language-select">{labels.languageLabel}</label>
        <select
          id="language-select"
          value={language}
          onChange={(event) => {
            const nextLanguage = event.target.value;
            if (!Object.prototype.hasOwnProperty.call(languages, nextLanguage)) return;
            setLanguage(nextLanguage);
            try {
              window.localStorage.setItem(LANGUAGE_STORAGE_KEY, nextLanguage);
            } catch {
              // Language switching remains available when browser storage is unavailable.
            }
          }}
        >
          <option value="en">{labels.languages.en}</option>
          <option value="hi">{labels.languages.hi}</option>
          <option value="mr">{labels.languages.mr}</option>
        </select>
        <button
          className="theme-toggle"
          type="button"
          aria-label={nextTheme === "dark" ? labels.themeSwitchToDark : labels.themeSwitchToLight}
          aria-pressed={theme === "dark"}
          onClick={() => {
            setThemeIsSaved(true);
            setTheme(nextTheme);
          }}
        >
          <ThemeIcon theme={nextTheme} />
          <span>{nextTheme === "dark" ? labels.themeDark : labels.themeLight}</span>
        </button>
      </header>
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

function ThemeIcon({ theme }) {
  return theme === "dark" ? (
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path d="M20.1 15.2A8.6 8.6 0 0 1 8.8 3.9 8.7 8.7 0 1 0 20.1 15.2Z" />
    </svg>
  ) : (
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2m0 16v2M4.93 4.93l1.42 1.42m11.3 11.3 1.42 1.42M2 12h2m16 0h2M4.93 19.07l1.42-1.42m11.3-11.3 1.42-1.42" />
    </svg>
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
