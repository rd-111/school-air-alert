export default function ActivityWindows({ data, labels }) {
  return (
    <section className="windows-grid" aria-label={labels.activityWindowsTitle}>
      <article className="panel window-card best-window">
        <span className="window-icon" aria-hidden="true">🌤️</span>
        <div>
          <p className="eyebrow">{labels.bestWindowLabel}</p>
          <h2>{data.bestWindow?.label || labels.noWindow}</h2>
          <p>{data.noSuitableWindow ? labels.noSuitableWindow : labels.bestWindowMessage}</p>
        </div>
      </article>
      <article className="panel window-card worst-window">
        <span className="window-icon" aria-hidden="true">🏠</span>
        <div>
          <p className="eyebrow">{labels.worstWindowLabel}</p>
          <h2>{data.worstWindow?.label || labels.noWindow}</h2>
          <p>{labels.worstWindowMessage}</p>
        </div>
      </article>
    </section>
  );
}
