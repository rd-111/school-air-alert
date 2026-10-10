import { mockDashboardData } from "./mockData.js";

export const DATA_MODE = import.meta.env.VITE_DATA_MODE === "live" ? "live" : "demo";
const API_URL = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");
const REQUEST_TIMEOUT_MS = 12000;
const demoSchools = [{ school_id: "demo-school", name: "Demo School" }];

async function requestApi(path, { method = "GET", body } = {}) {
  if (!API_URL) throw new Error("VITE_API_URL is required in live mode");
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    const response = await fetch(`${API_URL}${path}`, {
      method,
      headers: { Accept: "application/json", ...(body ? { "Content-Type": "application/json" } : {}) },
      body: body ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result?.error?.message || "The request failed");
    return result;
  } catch (error) {
    if (error.name === "AbortError") throw new Error("The request timed out");
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

export async function loadDashboardData(location = { latitude: 19.076, longitude: 72.8777 }, labels) {
  if (DATA_MODE === "demo") {
    return {
      ...mockDashboardData,
      location,
      schoolName: labels?.demoSchoolName || mockDashboardData.schoolName,
      mode: "demo",
      source: null,
      retrievedAt: null,
      hourly: mockDashboardData.hourly.map((item) => ({ ...item, status: statusFor(item.pm25) })),
    };
  }
  if (!API_URL) throw new Error("VITE_API_URL is required in live mode");

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    const query = new URLSearchParams({
      latitude: String(location.latitude),
      longitude: String(location.longitude),
    });
    const response = await fetch(`${API_URL}/api/v1/forecast?${query}`, {
      headers: { Accept: "application/json" },
      signal: controller.signal,
    });
    const body = await response.json();
    if (!response.ok) throw new Error(body?.error?.message || "Forecast request failed");
    return normalizeForecast(body);
  } catch (error) {
    if (error.name === "AbortError") throw new Error("Forecast request timed out");
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

function statusFor(value) {
  if (!Number.isFinite(value)) return "UNKNOWN";
  return value <= 60 ? "GREEN" : value <= 120 ? "YELLOW" : "RED";
}

export function normalizeForecast(body) {
  if (!body || body.data_type !== "forecast" || !Array.isArray(body.hourly)
    || !body.timezone || !body.retrieved_at) {
    throw new Error("The backend returned an invalid forecast");
  }
  const summary = body.school_hours_summary;
  if (!summary || !body.recommendations || !body.location || !body.source
    || !["GREEN", "YELLOW", "RED", "UNKNOWN"].includes(summary.status)
    || !Number.isFinite(body.location.latitude) || !Number.isFinite(body.location.longitude)
    || body.hourly.some((item) => !item || !Number.isFinite(Date.parse(item.time))
      || (item.pm25 !== null && !Number.isFinite(item.pm25))
      || !["GREEN", "YELLOW", "RED", "UNKNOWN"].includes(item.status))) {
    throw new Error("The backend returned an incomplete forecast");
  }
  const formatTime = (value) => new Intl.DateTimeFormat(undefined, {
    hour: "2-digit", minute: "2-digit", hour12: false, timeZone: body.timezone,
  }).format(new Date(value));
  const windowLabel = (window) => window
    ? `${formatTime(window.start)}–${formatTime(window.end)}`
    : null;

  return {
    mode: "live",
    schoolName: "School Air Alert",
    status: summary.status,
    averagePm25: summary.average_pm25,
    peakPm25: summary.peak_pm25,
    advice: summary.advice,
    hourly: body.hourly.map((item) => ({
      time: formatTime(item.time), pm25: item.pm25, status: item.status,
    })),
    bestWindow: body.recommendations.best_window
      ? { ...body.recommendations.best_window, label: windowLabel(body.recommendations.best_window) }
      : null,
    worstWindow: body.recommendations.worst_window
      ? { ...body.recommendations.worst_window, label: windowLabel(body.recommendations.worst_window) }
      : null,
    noSuitableWindow: body.recommendations.no_suitable_window,
    activityGuidance: body.recommendations.activity_guidance || [],
    policyNote: summary.policy_note,
    source: body.source,
    retrievedAt: body.retrieved_at,
    stale: body.stale === true,
    location: body.location,
    timezone: body.timezone,
  };
}

export async function loadSchools(labels) {
  if (DATA_MODE === "demo") {
    return demoSchools.map((school) => ({
      ...school,
      name: school.school_id === "demo-school" ? labels?.demoSchoolName || school.name : school.name,
    }));
  }
  return requestApi("/api/v1/schools");
}

export async function registerSchool(school) {
  if (DATA_MODE === "demo") {
    const school_id = `demo-school-${demoSchools.length}`;
    demoSchools.push({ school_id, name: school.name });
    return { school_id, name: school.name, status: "demo_only" };
  }
  return requestApi("/api/v1/schools", { method: "POST", body: school });
}

export async function subscribeToSchool(subscription) {
  if (DATA_MODE === "demo") return { status: "demo_only" };
  return requestApi("/api/v1/subscribe", { method: "POST", body: subscription });
}

export async function loadSchoolStatus(schoolId) {
  if (DATA_MODE === "demo") {
    const now = new Date();
    const date = now.toISOString().slice(0, 10);
    return {
      school: { school_id: schoolId, name: demoSchools.find((school) => school.school_id === schoolId)?.name || "Demo School" },
      date,
      status: "GREEN",
      average_pm25: 32,
      peak_pm25: 45,
      best_window: { start: `${date}T11:00:00+05:30`, end: `${date}T12:00:00+05:30`, average_pm25: 25, status: "GREEN", outdoor_activity_recommended: true, reason_code: "LOWEST_PM25_WINDOW" },
      worst_window: { start: `${date}T17:00:00+05:30`, end: `${date}T18:00:00+05:30`, average_pm25: 45, status: "GREEN", outdoor_activity_recommended: true, reason_code: "HIGHEST_PM25_WINDOW" },
      hourly: mockDashboardData.hourly.map((point) => ({ ...point, status: statusFor(point.pm25) })),
      source: { provider: "Demo data", model: "Illustrative only", provider_url: "", model_url: "", license: "", attribution: "Illustrative values only; not live data.", model_resolution_note: "" },
      retrieved_at: now.toISOString(),
      mode: "demo",
    };
  }
  return requestApi(`/api/v1/status?${new URLSearchParams({ school_id: schoolId })}`);
}

export async function loadSchoolHistory(schoolId, days = 30) {
  if (DATA_MODE === "demo") {
    return {
      school: { school_id: schoolId, name: demoSchools.find((school) => school.school_id === schoolId)?.name || "Demo School" },
      days,
      counts: { green: 0, yellow: 0, red: 0 },
      daily: [],
      mode: "demo",
    };
  }
  return requestApi(`/api/v1/history?${new URLSearchParams({ school_id: schoolId, days: String(days) })}`);
}
