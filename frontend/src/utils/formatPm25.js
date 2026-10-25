export function formatPm25(value, fallback = "—") {
  return typeof value === "number" && Number.isFinite(value) ? value.toFixed(1) : fallback;
}

export function formatPm25WithUnit(value, unit, fallback = "—") {
  const formatted = formatPm25(value, null);
  return formatted === null ? fallback : `${formatted} ${unit}`;
}
