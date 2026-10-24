import { afterEach, describe, expect, it, vi } from "vitest";
import { normalizeForecast, normalizeSmokeHint } from "./client.js";

const fixture = {
  data_type: "forecast",
  timezone: "Asia/Kolkata",
  retrieved_at: "2026-10-09T00:00:00Z",
  location: { latitude: 19, longitude: 72 },
  source: { provider_url: "https://example.test", model_url: "https://example.test", attribution: "Source", license: "CC BY" },
  hourly: [{ time: "2026-10-09T07:00:00+05:30", pm25: 20, status: "GREEN" }],
  school_hours_summary: { status: "GREEN", average_pm25: 20, peak_pm25: 20, advice: "advice", policy_note: "policy" },
  recommendations: { best_window: null, worst_window: null, no_suitable_window: true },
};

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

describe("forecast response validation", () => {
  it("normalizes a live response and keeps provider/source metadata", () => {
    const result = normalizeForecast(fixture);
    expect(result.mode).toBe("live");
    expect(result.hourly[0].status).toBe("GREEN");
    expect(result.source.attribution).toBe("Source");
    expect(result.noSuitableWindow).toBe(true);
  });

  it("rejects incomplete responses instead of falling back to demo data", () => {
    expect(() => normalizeForecast({ ...fixture, school_hours_summary: null })).toThrow(
      "incomplete forecast",
    );
  });

  it("requests and normalizes a successful live response", async () => {
    vi.resetModules();
    vi.stubEnv("VITE_DATA_MODE", "live");
    vi.stubEnv("VITE_API_URL", "http://api.example.test");
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => fixture }));
    const { loadDashboardData } = await import("./client.js");
    const result = await loadDashboardData({ latitude: 19, longitude: 72 });
    expect(result.mode).toBe("live");
    expect(fetch).toHaveBeenCalledWith(
      "http://api.example.test/api/v1/forecast?latitude=19&longitude=72",
      expect.objectContaining({ headers: { Accept: "application/json" } }),
    );
  });

  it("surfaces backend errors without silently returning demo data", async () => {
    vi.resetModules();
    vi.stubEnv("VITE_DATA_MODE", "live");
    vi.stubEnv("VITE_API_URL", "http://api.example.test");
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: false,
      json: async () => ({ error: { message: "provider unavailable" } }),
    }));
    const { loadDashboardData } = await import("./client.js");
    await expect(loadDashboardData()).rejects.toThrow("provider unavailable");
  });
});

describe("NASA FIRMS hint response validation", () => {
  const response = {
    status: "relevant_detections",
    school: { school_id: "s1", name: "School", latitude: 19, longitude: 72 },
    retrieved_at: "2026-10-23T12:00:00Z",
    latest_observation_at: "2026-10-23T11:00:00Z",
    search_radius_km: 25,
    detections: [{
      observed_at: "2026-10-23T11:00:00Z", latitude: 19.01, longitude: 72.01,
      distance_km: 1.4, satellite: "N21", confidence: "n",
    }],
    source: { provider: "NASA FIRMS", dataset: "VIIRS NOAA-21 NRT", url: "https://firms.modaps.eosdis.nasa.gov/" },
  };

  it("accepts a normalized provider response", () => {
    expect(normalizeSmokeHint(response)).toEqual(response);
  });

  it("rejects malformed or fabricated-shape responses", () => {
    expect(() => normalizeSmokeHint({ ...response, status: "smoke_confirmed" })).toThrow("invalid satellite hint");
    expect(() => normalizeSmokeHint({ ...response, detections: [{ ...response.detections[0], distance_km: "near" }] }))
      .toThrow("invalid detection data");
  });

  it("loads smoke hints through the configured backend path", async () => {
    vi.resetModules();
    vi.stubEnv("VITE_API_URL", "http://api.example.test");
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: async () => response,
    }));
    const { loadSchoolSmokeHint } = await import("./client.js");
    await expect(loadSchoolSmokeHint("school one")).resolves.toEqual(response);
    expect(fetch).toHaveBeenCalledWith(
      "http://api.example.test/api/v1/schools/school%20one/smoke-hint",
      expect.objectContaining({ headers: { Accept: "application/json" } }),
    );
  });
});
