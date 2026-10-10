const statusIcons = {
  GREEN: "✅",
  YELLOW: "⚠️",
  RED: "🏠",
  UNKNOWN: "ℹ️",
};

export default function StatusCard({ data, labels }) {
  const status = ["GREEN", "YELLOW", "RED", "UNKNOWN"].includes(data.status) ? data.status : "UNKNOWN";
  const statusText = labels.status[status.toLowerCase()];

  return (
    <section className={`status-card status-${status.toLowerCase()}`} aria-labelledby="status-title">
      <div className="status-main">
        <span className="status-icon" aria-hidden="true">{statusIcons[status]}</span>
        <div>
          <p className="eyebrow">{labels.todayStatus}</p>
          <h2 id="status-title">{statusText}</h2>
        </div>
      </div>
      <div className="status-reading">
        <span className="reading-number">{data.averagePm25 ?? labels.noReading}</span>
        <span className="reading-unit">{labels.averagePm25} ({labels.pm25Unit})</span>
        <span className="peak-reading">{labels.peakPm25}: {data.peakPm25 ?? labels.noReading} {data.peakPm25 == null ? "" : labels.pm25Unit}</span>
      </div>
      <p className="status-advice">{labels.advice[status.toLowerCase()]}</p>
    </section>
  );
}
