import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App.jsx";
import { loadDashboardData } from "./api/client.js";

vi.mock("./api/client.js", () => ({ loadDashboardData: vi.fn() }));
vi.mock("./components/HourlyForecastChart.jsx", () => ({
  default: () => <div>forecast chart</div>,
}));

function renderApp() {
  return render(
    <MemoryRouter>
      <App />
    </MemoryRouter>,
  );
}

describe("dashboard states", () => {
  beforeEach(() => {
    vi.clearAllMocks();
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
});
