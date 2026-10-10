import { useEffect, useState } from "react";
import { loadSchools, registerSchool, subscribeToSchool } from "../api/client.js";

export default function SchoolForms({ labels }) {
  const [schools, setSchools] = useState([]);
  const [schoolId, setSchoolId] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState(false);
  const [busy, setBusy] = useState(false);

  async function refreshSchools() {
    try {
      const result = await loadSchools(labels);
      setSchools(result);
      setSchoolId((current) => result.some((school) => school.school_id === current)
        ? current
        : result[0]?.school_id || "");
      setError(false);
    } catch {
      setError(true);
    }
  }

  useEffect(() => {
    refreshSchools();
  }, [labels]);

  async function create(event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setMessage("");
    try {
      const result = await registerSchool({
        name: String(form.get("name")).trim(),
        latitude: Number(form.get("latitude")),
        longitude: Number(form.get("longitude")),
        language: String(form.get("language")),
      });
      setSchoolId(result.school_id);
      setMessage(result.status === "demo_only" ? labels.demoActionNotice : labels.schoolCreated);
      await refreshSchools();
    } catch {
      setMessage(labels.formError);
    } finally {
      setBusy(false);
    }
  }

  async function subscribe(event) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setMessage("");
    try {
      const result = await subscribeToSchool({
        school_id: schoolId,
        email: String(form.get("email")).trim(),
        sensitive: form.get("sensitive") === "on",
      });
      setMessage(result.status === "demo_only" ? labels.demoActionNotice : labels.subscriptionPending);
      formElement.reset();
    } catch {
      setMessage(labels.formError);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel school-tools" aria-labelledby="school-tools-title">
      <h2 id="school-tools-title">{labels.schoolToolsTitle}</h2>
      <label className="school-picker">
        {labels.schoolPicker}
        <select value={schoolId} onChange={(event) => setSchoolId(event.target.value)} disabled={!schools.length}>
          {!schools.length && <option value="">{labels.noSchools}</option>}
          {schools.map((school) => <option key={school.school_id} value={school.school_id}>{school.name}</option>)}
        </select>
      </label>
      {error && <p className="form-error" role="alert">{labels.formError}</p>}

      <details>
        <summary>{labels.registerSchool}</summary>
        <form className="school-form" onSubmit={create}>
          <label>{labels.schoolName}<input name="name" minLength="3" maxLength="80" required /></label>
          <label>{labels.latitude}<input name="latitude" type="number" min="-90" max="90" step="any" required /></label>
          <label>{labels.longitude}<input name="longitude" type="number" min="-180" max="180" step="any" required /></label>
          <label>{labels.schoolLanguage}
            <select name="language">
              <option value="English">{labels.languages.en}</option>
              <option value="Hindi">{labels.languages.hi}</option>
              <option value="Marathi">{labels.languages.mr}</option>
            </select>
          </label>
          <button disabled={busy}>{labels.createSchoolButton}</button>
        </form>
      </details>

      <details>
        <summary>{labels.subscribeEmail}</summary>
        <form className="school-form" onSubmit={subscribe}>
          <label>{labels.emailAddress}<input name="email" type="email" maxLength="254" required /></label>
          <label className="checkbox-label"><input name="sensitive" type="checkbox" />{labels.sensitiveOptIn}</label>
          <button disabled={busy || !schoolId}>{labels.subscribeButton}</button>
        </form>
      </details>
      {message && <p className="form-message" role="status">{message}</p>}
    </section>
  );
}
