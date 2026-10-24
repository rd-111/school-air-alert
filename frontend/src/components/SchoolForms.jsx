import { useEffect, useState } from "react";
import { loadSchools, registerSchool, subscribeToSchool } from "../api/client.js";

export default function SchoolForms({ labels, selectedSchoolId, selectedSchool, onSchoolChange }) {
  const [schools, setSchools] = useState([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState(false);
  const [busy, setBusy] = useState(false);

  async function refreshSchools(preferredId = selectedSchoolId) {
    try {
      const result = await loadSchools(labels);
      const match = result.find((school) => school.school_id === preferredId);
      if (match) {
        setSchools(result);
        onSchoolChange?.(match);
        setError(false);
      } else if (!preferredId) {
        setSchools(result);
        onSchoolChange?.(result[0] || null);
        setError(false);
      } else if (selectedSchool?.school_id === preferredId) {
        // Keep the restored school selected during partial or stale list responses.
        setSchools([selectedSchool, ...result.filter((school) => school.school_id !== preferredId)]);
        setError(true);
      } else {
        setSchools(result);
        setError(true);
      }
    } catch {
      setError(true);
    }
  }

  useEffect(() => {
    refreshSchools();
  }, [labels, onSchoolChange]);

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
      setMessage(result.status === "demo_only" ? labels.demoActionNotice : labels.schoolCreated);
      await refreshSchools(result.school_id);
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
        school_id: selectedSchoolId,
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
        <select
          value={selectedSchoolId || ""}
          onChange={(event) => {
            const selected = schools.find((school) => school.school_id === event.target.value);
            if (selected) onSchoolChange?.(selected);
          }}
          disabled={!schools.length}
        >
          {!schools.length && <option value="">{labels.noSchools}</option>}
          {schools.map((school) => <option key={school.school_id} value={school.school_id}>{school.name}</option>)}
        </select>
      </label>
      {selectedSchool && (
        <div className="school-selected" aria-live="polite">
          <strong>{selectedSchool.name}</strong>
          <span>{selectedSchool.latitude}, {selectedSchool.longitude}</span>
        </div>
      )}
      {error && <p className="form-error" role="alert">{labels.formError}</p>}

      <details className="school-form-panel register-school-details">
        <summary>{labels.registerSchool}</summary>
        <form className="school-form" aria-label={labels.registerSchool} onSubmit={create}>
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

      <details className="school-form-panel subscription-details">
        <summary>{labels.subscribeEmail}</summary>
        <form className="school-form" aria-label={labels.subscribeEmail} onSubmit={subscribe}>
          <label>{labels.emailAddress}<input name="email" type="email" maxLength="254" required /></label>
          <label className="checkbox-label"><input name="sensitive" type="checkbox" />{labels.sensitiveOptIn}</label>
          <button disabled={busy || !selectedSchoolId}>{labels.subscribeButton}</button>
        </form>
      </details>
      {message && <p className="form-message" role="status">{message}</p>}
    </section>
  );
}
