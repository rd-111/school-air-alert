const icons = { GREEN: "✅", YELLOW: "⚠️", RED: "🏠", UNKNOWN: "ℹ️" };

export default function HourlyReadings({ hourly, labels }) {
  return (
    <div className="hourly-list" role="group" aria-label={labels.hourlyReadings}>
      {hourly.map((item) => (
        <article className={`hour-reading status-${safeStatus(item.status).toLowerCase()}`} key={item.time}>
          <strong>{item.time}</strong>
          <span>{item.pm25 == null ? labels.noReading : `${item.pm25} ${labels.pm25Unit}`}</span>
          <span>{icons[safeStatus(item.status)]} {labels.status[safeStatus(item.status).toLowerCase()]}</span>
        </article>
      ))}
    </div>
  );
}

function safeStatus(value) {
  return ["GREEN", "YELLOW", "RED", "UNKNOWN"].includes(value) ? value : "UNKNOWN";
}
