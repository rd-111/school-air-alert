import { afterEach, describe, expect, it, vi } from "vitest";
import { normalizeForecast } from "./client.js";

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
