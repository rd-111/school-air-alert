import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App.jsx";
import {
  loadDashboardData,
  loadSchoolHistory,
  loadSchoolStatus,
  loadSchools,
} from "./api/client.js";

vi.mock("./api/client.js", () => ({
  loadDashboardData: vi.fn(),
  loadSchools: vi.fn(),
  registerSchool: vi.fn(),
  subscribeToSchool: vi.fn(),
  loadSchoolHistory: vi.fn(),
  loadSchoolStatus: vi.fn(),
}));
vi.mock("./components/HourlyForecastChart.jsx", () => ({
  default: () => <div>forecast chart</div>,
}));

function renderApp(initialEntries = ["/"]) {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <App />
    </MemoryRouter>,
  );
}

describe("dashboard states", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    loadSchools.mockResolvedValue([{ school_id: "demo-school", name: "Demo School" }]);
  });

  it("shows demo status and outdoor windows", async () => {
    loadDashboardData.mockResolvedValue({
      schoolName: "Demo School",
      status: "GREEN",
      averagePm25: 32,
      peakPm25: 45,
      hourly: [{ time: "11:00", pm25: 25 }],
      bestWindow: { start: "11:00", end: "12:00", label: "11:00–12:00" },
      worstWindow: { start: "17:00", end: "18:00", label: "17:00–18:00" },
    });

    renderApp();

    expect(await screen.findByRole("heading", { name: "GREEN" })).toBeInTheDocument();
    expect(screen.getByText("DEMO DATA · NOT LIVE")).toBeInTheDocument();
    expect(screen.getByText("11:00–12:00")).toBeInTheDocument();
    expect(screen.getByText("Forecast accuracy not yet measured — historical validation data is unavailable.")).toBeInTheDocument();
    expect(screen.queryByText("Provider", { exact: false })).not.toBeInTheDocument();
  });

  it("shows only supplied forecast metadata in the reliability panel", async () => {
    loadDashboardData.mockResolvedValue({
      schoolName: "School Air Alert", mode: "live", status: "UNKNOWN", averagePm25: null,
      peakPm25: null, hourly: [{ time: "07:00", pm25: null, status: "UNKNOWN" }],
      bestWindow: null, worstWindow: null, source: { provider: "Open-Meteo Air Quality API" },
      retrievedAt: "2026-10-09T00:00:00Z",
    });

    renderApp();

    const panel = await screen.findByRole("region", { name: "About this forecast" });
    expect(panel).toHaveTextContent("Forecast accuracy not yet measured");
    expect(panel).toHaveTextContent("Open-Meteo Air Quality API");
    expect(panel).toHaveTextContent("1 hours");
  });

  it("shows a loading state while dashboard data is pending", () => {
    loadDashboardData.mockReturnValue(new Promise(() => {}));
    renderApp();
    expect(screen.getByRole("heading", { name: "Loading air quality" })).toBeInTheDocument();
  });

  it("shows an empty state", async () => {
    loadDashboardData.mockResolvedValue(null);
    renderApp();
    expect(await screen.findByRole("heading", { name: "No forecast yet" })).toBeInTheDocument();
  });

  it("shows an error state", async () => {
    loadDashboardData.mockRejectedValue(new Error("unavailable"));
    renderApp();
    expect(await screen.findByRole("heading", { name: "Could not load the forecast" })).toBeInTheDocument();
  });

  it("shows unknown readings without implying GREEN", async () => {
    loadDashboardData.mockResolvedValue({
      schoolName: "Demo School", status: "UNKNOWN", averagePm25: null, peakPm25: null,
      hourly: [{ time: "07:00", pm25: null, status: "UNKNOWN" }],
      bestWindow: null, worstWindow: null, noSuitableWindow: true,
      mode: "demo",
    });
    renderApp();
    expect(await screen.findByRole("heading", { name: "UNKNOWN" })).toBeInTheDocument();
  });

  it("switches dashboard labels when a language is selected", async () => {
    loadDashboardData.mockResolvedValue({
      schoolName: "Demo School", status: "GREEN", averagePm25: 32, peakPm25: 45,
      hourly: [{ time: "11:00", pm25: 25, status: "GREEN" }],
      bestWindow: { start: "11:00", end: "12:00", label: "11:00–12:00" },
      worstWindow: { start: "17:00", end: "18:00", label: "17:00–18:00" }, mode: "demo",
    });
    renderApp();
    await screen.findByRole("heading", { name: "GREEN" });
    const select = screen.getByLabelText("Language");
    select.value = "hi";
    select.dispatchEvent(new Event("change", { bubbles: true }));
    expect(await screen.findByRole("heading", { name: "आज की स्थिति" })).toBeInTheDocument();
  });

  it("shows forecast-only empty report history", async () => {
    loadSchoolHistory.mockResolvedValue({
      school: { school_id: "demo-school", name: "Demo School" },
      days: 30, counts: { green: 0, yellow: 0, red: 0 }, daily: [], mode: "demo",
    });
    renderApp(["/report?school_id=demo-school"]);
    expect(await screen.findByRole("heading", { name: "Monthly report card" })).toBeInTheDocument();
    expect(await screen.findByText("No saved forecast history is available yet.")).toBeInTheDocument();
  });

  it("renders a printable poster for a requested school", async () => {
    loadSchoolStatus.mockResolvedValue({
      school: { school_id: "demo-school", name: "Demo School" },
      date: "2026-10-09", status: "GREEN", average_pm25: 32, peak_pm25: 45,
      best_window: null, worst_window: null, retrieved_at: "2026-10-09T00:00:00Z", mode: "demo",
    });
    renderApp(["/poster?school_id=demo-school"]);
    expect(await screen.findByRole("heading", { name: "Demo School" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Print poster" })).toBeInTheDocument();
    expect(screen.getByRole("list").children).toHaveLength(3);
  });
});
