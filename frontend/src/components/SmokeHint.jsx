import { useEffect, useState } from "react";
import { loadSchoolSmokeHint } from "../api/client.js";

export default function SmokeHint({ schoolId, dataMode, onSchoolLocation, labels }) {
  const [state, setState] = useState("loading");
  const [hint, setHint] = useState(null);

  useEffect(() => {
    let active = true;
    setHint(null);
    if (dataMode === "demo") {
      setState("demo");
      return () => { active = false; };
    }
    if (!schoolId) {
      setState("no_school");
      return () => { active = false; };
    }

    setState("loading");
    loadSchoolSmokeHint(schoolId).then((result) => {
      if (!active) return;
      setHint(result);
      setState(result.status);
      onSchoolLocation?.(result.school);
    }).catch(() => {
      if (active) setState("error");
    });
    return () => { active = false; };
  }, [dataMode, onSchoolLocation, schoolId]);

  return (
    <section className="panel smoke-hint" aria-labelledby="smoke-hint-title" aria-busy={state === "loading"}>
      <div className="smoke-heading">
        <div>
          <p className="eyebrow">{labels.smokeEyebrow}</p>
          <h2 id="smoke-hint-title">{labels.smokeTitle}</h2>
        </div>
        <span className="smoke-icon" aria-hidden="true">🛰️</span>
      </div>
      <p className="smoke-intro">{labels.smokeIntro}</p>

      {state === "loading" && <p role="status">{labels.smokeLoading}</p>}
      {state === "demo" && <p className="smoke-state" role="status">{labels.smokeDemo}</p>}
      {state === "no_school" && <p className="smoke-state" role="status">{labels.smokeSelectSchool}</p>}
      {state === "error" && <p className="smoke-state smoke-unavailable" role="status">{labels.smokeError}</p>}
      {hint && <SmokeHintDetails hint={hint} labels={labels} state={state} />}

      <p className="smoke-disclaimer">{labels.smokeDisclaimer}</p>
    </section>
  );
}

function SmokeHintDetails({ hint, labels, state }) {
  const schoolLocation = `${hint.school.latitude}, ${hint.school.longitude}`;
  const message = {
    unconfigured: labels.smokeUnconfigured,
    unavailable: labels.smokeUnavailable,
    no_detections: labels.smokeNoDetections,
    stale: labels.smokeStale,
    relevant_detections: labels.smokeRelevant,
    wind_unavailable: labels.smokeWindUnavailable,
    wind_indeterminate: labels.smokeWindIndeterminate,
    no_upwind_clusters: labels.smokeNoUpwindClusters,
    transport_possible: labels.smokeTransportPossible,
  }[state];
  const timestamp = (value) => value
    ? new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value))
    : null;

  return (
    <div className="smoke-details">
      <p className={`smoke-state smoke-${state}`} role="status">{message}</p>
      <dl className="smoke-metadata">
        <div><dt>{labels.smokeSchoolLocation}</dt><dd>{hint.school.name} · {schoolLocation}</dd></div>
        <div><dt>{labels.smokeSearchRadius}</dt><dd>{hint.search_radius_km} {labels.smokeDistanceUnit}</dd></div>
        {hint.latest_observation_at && (
          <div><dt>{labels.smokeLastObservation}</dt><dd>{timestamp(hint.latest_observation_at)}</dd></div>
        )}
        {hint.retrieved_at && (
          <div><dt>{labels.smokeRetrievedAt}</dt><dd>{timestamp(hint.retrieved_at)}</dd></div>
        )}
        <div>
          <dt>{labels.smokeSource}</dt>
          <dd><a href={hint.source.url} target="_blank" rel="noreferrer">
            {hint.source.provider} · {hint.source.dataset}
          </a></dd>
        </div>
      </dl>
      {hint.detections.length > 0 && (
        <>
          <h3>{labels.smokeDetectionListTitle}</h3>
          <ul className="smoke-detections">
            {hint.detections.map((detection) => (
              <li key={`${detection.observed_at}-${detection.latitude}-${detection.longitude}`}>
                <strong>{timestamp(detection.observed_at)}</strong>
                <span>{detection.distance_km} {labels.smokeDistanceUnit} · {detection.satellite || hint.source.dataset}</span>
                {detection.confidence && <span>{labels.smokeConfidence}: {detection.confidence}</span>}
              </li>
            ))}
          </ul>
        </>
      )}
      {hint.wind_source && (
        <p className="smoke-model-note">
          <a href={hint.wind_source.url} target="_blank" rel="noreferrer">{hint.wind_source.provider}</a>
          {" · "}{hint.wind_source.dataset}
          {hint.wind_source.retrieved_at && (
            <span> · {labels.smokeWindRetrievedAt}: {timestamp(hint.wind_source.retrieved_at)}</span>
          )}
        </p>
      )}
      {hint.clusters?.length > 0 && (
        <ul className="smoke-clusters" aria-label={labels.smokeClusterList}>
          {hint.clusters.map((cluster) => (
            <li key={cluster.cluster_id}>
              <span>{labels.smokeCluster}: {cluster.pixel_count} {labels.smokePixels}</span>
              {cluster.wind_status !== "indeterminate" && (
                <span>{labels.smokeWindFrom}: {cluster.wind_direction_from_degrees}° · {cluster.wind_speed_mps} m/s</span>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
