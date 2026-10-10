const activityLabelKeys = {
  pe: "pe",
  sports: "sports",
  recess: "recess",
  assembly: "assembly",
  bus_wait: "busWait",
};

export default function ActivityAdvice({ recommendations = [], labels }) {
  if (!recommendations.length) return null;
  return (
    <section className="panel activity-advice" aria-labelledby="activity-advice-title">
      <h2 id="activity-advice-title">{labels.activityGuidanceTitle}</h2>
      <p>{labels.activityGuidanceDisclaimer}</p>
      <ul>
        {recommendations.map(({ activity, guidance_code: code }) => (
          <li key={activity}>
            <strong>{labels.activityNames[activityLabelKeys[activity]]}: </strong>
            {labels.activityGuidance[code.toLowerCase()]}
          </li>
        ))}
      </ul>
    </section>
  );
}
