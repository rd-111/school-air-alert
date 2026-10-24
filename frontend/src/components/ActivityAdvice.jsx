const activityLabelKeys = {
  pe: "pe",
  sports: "sports",
  recess: "recess",
  assembly: "assembly",
  bus_wait: "busWait",
};
const activityIcons = { pe: "◉", sports: "◇", recess: "✳", assembly: "▤", bus_wait: "↗" };

export default function ActivityAdvice({ recommendations = [], labels }) {
  if (!recommendations.length) return null;
  return (
    <section className="panel activity-advice" aria-labelledby="activity-advice-title">
      <h2 id="activity-advice-title">{labels.activityGuidanceTitle}</h2>
      <p>{labels.activityGuidanceDisclaimer}</p>
      <ul>
        {recommendations.map(({ activity, guidance_code: code }) => (
          <li className="activity-note" key={activity}>
            <span className="activity-note-icon" aria-hidden="true">{activityIcons[activity] || "•"}</span>
            <strong>{labels.activityNames[activityLabelKeys[activity]]}</strong>
            <span>{labels.activityGuidance[code.toLowerCase()]}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
