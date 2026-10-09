import { useState } from "react";
import { Route, Routes } from "react-router-dom";
import DashboardPage from "./pages/DashboardPage.jsx";
import en from "./i18n/en.json";
import hi from "./i18n/hi.json";
import mr from "./i18n/mr.json";

const languages = { en, hi, mr };

export default function App() {
  const [language, setLanguage] = useState("en");
  const labels = languages[language];

  return (
    <>
      <div className="language-bar">
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
      <Routes>
        <Route path="/" element={<DashboardPage labels={labels} />} />
        <Route path="*" element={<DashboardPage labels={labels} />} />
      </Routes>
    </>
  );
}
