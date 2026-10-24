import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import en from "../i18n/en.json";
import SmokeHint from "./SmokeHint.jsx";
import { loadSchoolSmokeHint } from "../api/client.js";

vi.mock("../api/client.js", () => ({ loadSchoolSmokeHint: vi.fn() }));

const hint = {
  status: "relevant_detections",
  school: { school_id: "school-1", name: "Example School", latitude: 19.076, longitude: 72.8777 },
  retrieved_at: "2026-10-23T12:00:00Z",
  latest_observation_at: "2026-10-23T11:00:00Z",
  search_radius_km: 25,
  detections: [{
    observed_at: "2026-10-23T11:00:00Z", latitude: 19.08, longitude: 72.88,
    distance_km: 0.6, satellite: "N21", confidence: "n",
  }],
  source: { provider: "NASA FIRMS", dataset: "VIIRS NOAA-21 Near Real-Time", url: "https://firms.modaps.eosdis.nasa.gov/api/area/" },
};

function renderHint() {
  const onSchoolLocation = vi.fn();
  const view = render(
    <SmokeHint schoolId="school-1" dataMode="live" onSchoolLocation={onSchoolLocation} labels={en} />,
  );
  return { ...view, onSchoolLocation };
}

describe("optional school smoke hint", () => {
  beforeEach(() => vi.clearAllMocks());

  it("shows a loading state while requesting school satellite data", () => {
    loadSchoolSmokeHint.mockReturnValue(new Promise(() => {}));
    renderHint();
    expect(screen.getByRole("status")).toHaveTextContent(en.smokeLoading);
  });

  it("shows nearby detections, their source and school coordinates", async () => {
    loadSchoolSmokeHint.mockResolvedValue(hint);
    const { onSchoolLocation } = renderHint();
    expect(await screen.findByText(en.smokeRelevant)).toBeInTheDocument();
    expect(screen.getByText(/Example School · 19.076, 72.8777/)).toBeInTheDocument();
    expect(screen.getByText(/NASA FIRMS · VIIRS NOAA-21 Near Real-Time/)).toBeInTheDocument();
    expect(screen.getByText(/0.6 km · N21/)).toBeInTheDocument();
    expect(screen.getByText(en.smokeDisclaimer)).toBeInTheDocument();
    expect(onSchoolLocation).toHaveBeenCalledWith(hint.school);
  });

  it("explains an empty result without claiming smoke is absent", async () => {
    loadSchoolSmokeHint.mockResolvedValue({ ...hint, status: "no_detections", detections: [] });
    renderHint();
    expect(await screen.findByText(en.smokeNoDetections)).toBeInTheDocument();
  });

  it("shows stale observation time without presenting it as recent", async () => {
    loadSchoolSmokeHint.mockResolvedValue({
      ...hint, status: "stale", detections: [], latest_observation_at: "2026-10-22T10:00:00Z",
    });
    renderHint();
    expect(await screen.findByText(en.smokeStale)).toBeInTheDocument();
    expect(screen.getByText(en.smokeLastObservation)).toBeInTheDocument();
  });

  it("shows missing credentials as unconfigured", async () => {
    loadSchoolSmokeHint.mockResolvedValue({ ...hint, status: "unconfigured", detections: [], retrieved_at: null });
    renderHint();
    expect(await screen.findByText(en.smokeUnconfigured)).toBeInTheDocument();
  });

  it("shows an unavailable state when the provider cannot respond", async () => {
    loadSchoolSmokeHint.mockResolvedValue({ ...hint, status: "unavailable", detections: [], retrieved_at: null });
    renderHint();
    expect(await screen.findByText(en.smokeUnavailable)).toBeInTheDocument();
  });

  it("does not request or imply live results in demo mode", () => {
    render(<SmokeHint schoolId="school-1" dataMode="demo" labels={en} />);
    expect(screen.getByRole("status")).toHaveTextContent(en.smokeDemo);
    expect(loadSchoolSmokeHint).not.toHaveBeenCalled();
  });

  it("shows an empty selection state when no school is selected", async () => {
    render(<SmokeHint dataMode="live" labels={en} />);
    expect(await screen.findByText(en.smokeSelectSchool)).toBeInTheDocument();
    expect(loadSchoolSmokeHint).not.toHaveBeenCalled();
  });

  it("handles an unavailable backend separately from an empty result", async () => {
    loadSchoolSmokeHint.mockRejectedValue(new Error("network unavailable"));
    renderHint();
    expect(await screen.findByText(en.smokeError)).toBeInTheDocument();
  });

  it("shows the approved interim wording only when modeled transport is indicated", async () => {
    loadSchoolSmokeHint.mockResolvedValue({
      ...hint,
      status: "transport_possible",
      wind_source: { provider: "Open-Meteo", dataset: "Historical Forecast API; modeled 10 m wind (Best Match)", url: "https://open-meteo.com/en/docs/historical-forecast-api" },
      clusters: [{ cluster_id: "1", observed_at: hint.latest_observation_at, latitude: 19.08, longitude: 72.88, pixel_count: 2, wind_status: "transport_toward", wind_speed_mps: 2, wind_direction_from_degrees: 45 }],
    });
    renderHint();
    expect(await screen.findByText(en.smokeTransportPossible)).toBeInTheDocument();
    expect(screen.getByText(/Historical Forecast API; modeled 10 m wind/)).toBeInTheDocument();
    expect(screen.queryByText(/Smoke from nearby fires is likely contributing/)).not.toBeInTheDocument();
  });

  it.each([
    ["wind_unavailable", "smokeWindUnavailable"],
    ["wind_indeterminate", "smokeWindIndeterminate"],
    ["no_upwind_clusters", "smokeNoUpwindClusters"],
  ])("shows an honest %s state without the transport claim", async (status, label) => {
    loadSchoolSmokeHint.mockResolvedValue({ ...hint, status });
    renderHint();
    expect(await screen.findByText(en[label])).toBeInTheDocument();
    expect(screen.queryByText(en.smokeTransportPossible)).not.toBeInTheDocument();
  });
});
