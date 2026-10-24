import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App.jsx";
import {
  loadDashboardData,
  loadSchoolSmokeHint,
  loadSchoolHistory,
  loadSchoolStatus,
  loadSchools,
  registerSchool,
} from "./api/client.js";

vi.mock("./api/client.js", () => ({
  loadDashboardData: vi.fn(),
  loadSchoolSmokeHint: vi.fn(),
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

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("dashboard states", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
    delete document.documentElement.dataset.theme;
    loadSchools.mockResolvedValue([{
      school_id: "demo-school", name: "Demo School", latitude: 19.076, longitude: 72.8777,
    }]);
    loadSchoolSmokeHint.mockResolvedValue({
      status: "unconfigured",
      school: { school_id: "demo-school", name: "Demo School", latitude: 19.076, longitude: 72.8777 },
      retrieved_at: null,
      latest_observation_at: null,
      search_radius_km: 25,
      detections: [],
      source: { provider: "NASA FIRMS", dataset: "VIIRS NOAA-21 Near Real-Time", url: "https://firms.modaps.eosdis.nasa.gov/api/area/" },
    });
  });

  function mockThemeDashboard() {
    loadDashboardData.mockResolvedValue({
      schoolName: "Demo School", mode: "demo", status: "GREEN", averagePm25: 32,
      peakPm25: 45, hourly: [], bestWindow: null, worstWindow: null,
    });
  }

  it("shows the theme toggle and updates the root theme and saved preference", async () => {
    mockThemeDashboard();
    renderApp();

    const toggle = await screen.findByRole("button", { name: "Switch to dark mode" });
    expect(document.documentElement).toHaveAttribute("data-theme", "light");
    fireEvent.click(toggle);

    expect(document.documentElement).toHaveAttribute("data-theme", "dark");
    expect(window.localStorage.getItem("school-air-alert-theme")).toBe("dark");
    expect(screen.getByRole("button", { name: "Switch to light mode" })).toHaveAttribute("aria-pressed", "true");
    fireEvent.click(screen.getByRole("button", { name: "Switch to light mode" }));
    expect(document.documentElement).toHaveAttribute("data-theme", "light");
    expect(window.localStorage.getItem("school-air-alert-theme")).toBe("light");
  });

  it("restores the selected theme after the app is remounted", async () => {
    mockThemeDashboard();
    const app = renderApp();
    fireEvent.click(await screen.findByRole("button", { name: "Switch to dark mode" }));
    app.unmount();
    renderApp();

    expect(await screen.findByRole("button", { name: "Switch to light mode" })).toBeInTheDocument();
    expect(document.documentElement).toHaveAttribute("data-theme", "dark");
  });

  it("uses the system dark preference when no theme was saved", async () => {
    mockThemeDashboard();
    vi.stubGlobal("matchMedia", vi.fn().mockReturnValue({ matches: true }));
    renderApp();

    expect(await screen.findByRole("button", { name: "Switch to light mode" })).toBeInTheDocument();
    expect(document.documentElement).toHaveAttribute("data-theme", "dark");
    expect(window.localStorage.getItem("school-air-alert-theme")).toBeNull();
  });

  it("defaults to English when no language preference is saved", async () => {
    mockThemeDashboard();
    renderApp();

    expect(await screen.findByLabelText("Language")).toHaveValue("en");
    expect(window.localStorage.getItem("school-air-alert-language")).toBeNull();
  });

  it.each([
    ["hi", "आज की स्थिति"],
    ["mr", "आजची स्थिती"],
  ])("restores %s after the app is reloaded", async (language, dashboardTitle) => {
    window.localStorage.setItem("school-air-alert-language", language);
    mockThemeDashboard();
    const app = renderApp();

    expect(await screen.findByRole("heading", { name: dashboardTitle })).toBeInTheDocument();
    expect(screen.getByLabelText("भाषा")).toHaveValue(language);
    app.unmount();
    renderApp();

    expect(await screen.findByLabelText("भाषा")).toHaveValue(language);
    expect(screen.getByRole("heading", { name: dashboardTitle })).toBeInTheDocument();
  });

  it("defaults to English when the saved language is unsupported", async () => {
    window.localStorage.setItem("school-air-alert-language", "fr");
    mockThemeDashboard();
    renderApp();

    expect(await screen.findByLabelText("Language")).toHaveValue("en");
    expect(await screen.findByRole("heading", { name: "Today at a glance" })).toBeInTheDocument();
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

  it("loads the selected school's forecast and smoke hint using its registered location", async () => {
    loadSchools.mockResolvedValue([
      { school_id: "demo-school", name: "Demo School", latitude: 19.076, longitude: 72.8777 },
      { school_id: "pune-school", name: "Demo School Pune", latitude: 18.5204, longitude: 73.8567 },
    ]);
    loadDashboardData.mockImplementation(async (location) => ({
      schoolName: "Forecast location",
      mode: "live",
      status: location.latitude === 18.5204 ? "YELLOW" : "GREEN",
      averagePm25: 70,
      peakPm25: 90,
      hourly: [{ time: "11:00", pm25: 70, status: "YELLOW" }],
      bestWindow: null,
      worstWindow: null,
      location,
    }));

    const app = renderApp();
    const schoolPicker = await screen.findByLabelText("Choose a school");
    await screen.findByText("Demo School", { selector: ".school-name" });

    fireEvent.change(schoolPicker, { target: { value: "pune-school" } });

    expect(await screen.findByText("Demo School Pune", { selector: ".school-name" })).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "YELLOW" })).toBeInTheDocument();
    expect(screen.getByText(/18\.5204.*73\.8567/, { selector: ".location-note" })).toBeInTheDocument();
    expect(loadDashboardData).toHaveBeenLastCalledWith(
      { latitude: 18.5204, longitude: 73.8567 },
      expect.any(Object),
    );
    await waitFor(() => expect(loadSchoolSmokeHint).toHaveBeenCalledWith("pune-school"));
    expect(screen.getByLabelText("Choose a school")).toHaveValue("pune-school");
    expect(JSON.parse(window.localStorage.getItem("school-air-alert-selected-school"))).toMatchObject({
      school_id: "pune-school", latitude: 18.5204, longitude: 73.8567,
    });

    app.unmount();
    renderApp();
    expect(await screen.findByLabelText("Choose a school")).toHaveValue("pune-school");
    await waitFor(() => expect(loadDashboardData).toHaveBeenLastCalledWith(
      { latitude: 18.5204, longitude: 73.8567 },
      expect.any(Object),
    ));
    expect(await screen.findByText("Demo School Pune", { selector: ".school-name" })).toBeInTheDocument();
  });

  it("selects a newly registered school's returned coordinates", async () => {
    let schools = [
      { school_id: "demo-school", name: "Demo School", latitude: 19.076, longitude: 72.8777 },
    ];
    loadSchools.mockImplementation(async () => schools);
    registerSchool.mockImplementation(async (school) => {
      schools = [...schools, {
        school_id: "pune-school", name: school.name,
        latitude: school.latitude, longitude: school.longitude,
      }];
      return { school_id: "pune-school", name: school.name, status: "created" };
    });
    loadDashboardData.mockImplementation(async (location) => ({
      schoolName: "Forecast location", mode: "live", status: "GREEN", averagePm25: 20,
      peakPm25: 30, hourly: [], bestWindow: null, worstWindow: null, location,
    }));

    renderApp();
    await screen.findByLabelText("Choose a school");
    fireEvent.click(screen.getByText("Register a school"));
    const registrationForm = screen.getByLabelText("School name").closest("form");
    fireEvent.change(within(registrationForm).getByLabelText("School name"), { target: { value: "Demo School Pune" } });
    fireEvent.change(within(registrationForm).getByLabelText("Latitude"), { target: { value: "18.5204" } });
    fireEvent.change(within(registrationForm).getByLabelText("Longitude"), { target: { value: "73.8567" } });
    expect(registrationForm.checkValidity()).toBe(true);
    fireEvent.click(within(registrationForm).getByRole("button", { name: "Create school" }));

    await waitFor(() => expect(registerSchool).toHaveBeenCalledWith({
      name: "Demo School Pune", latitude: 18.5204, longitude: 73.8567, language: "English",
    }));
    expect(await screen.findByText("Demo School Pune", { selector: ".school-name" })).toBeInTheDocument();
    expect(screen.getByLabelText("Choose a school")).toHaveValue("pune-school");
    expect(loadDashboardData).toHaveBeenLastCalledWith(
      { latitude: 18.5204, longitude: 73.8567 },
      expect.any(Object),
    );
  });

  it("keeps a restored school selected when the school list is temporarily incomplete", async () => {
    const selected = {
      school_id: "pune-school", name: "Demo School Pune", latitude: 18.5204, longitude: 73.8567,
    };
    window.localStorage.setItem("school-air-alert-selected-school", JSON.stringify(selected));
    loadDashboardData.mockImplementation(async (location) => ({
      schoolName: "Forecast location", mode: "live", status: "GREEN", averagePm25: 20,
      peakPm25: 30, hourly: [], bestWindow: null, worstWindow: null, location,
    }));

    renderApp();

    expect(await screen.findByLabelText("Choose a school")).toHaveValue("pune-school");
    expect(await screen.findByText("Demo School Pune", { selector: ".school-name" })).toBeInTheDocument();
    expect(loadDashboardData).toHaveBeenLastCalledWith(
      { latitude: 18.5204, longitude: 73.8567 },
      expect.any(Object),
    );
  });

  it("keeps both school forms and the location editor available when both disclosures are open", async () => {
    mockThemeDashboard();
    renderApp();

    await screen.findByLabelText("Choose a school");
    fireEvent.click(screen.getByText("Register a school"));
    fireEvent.click(screen.getByText("Subscribe by email"));

    const registrationForm = screen.getByLabelText("School name").closest("form");
    const subscriptionForm = screen.getByLabelText("Email address").closest("form");
    const schoolSection = screen.getByRole("region", { name: "Schools and email alerts" });
    const locationEditor = screen.getByRole("button", { name: "Update location" }).closest("form");

    expect(registrationForm.closest("details").open).toBe(true);
    expect(subscriptionForm.closest("details").open).toBe(true);
    expect(screen.getByRole("form", { name: "Register a school" })).toBe(registrationForm);
    expect(screen.getByRole("form", { name: "Subscribe by email" })).toBe(subscriptionForm);
    expect(schoolSection.nextElementSibling).toBe(locationEditor);
    expect(within(registrationForm).getByRole("button", { name: "Create school" })).toBeInTheDocument();
    expect(within(subscriptionForm).getByRole("button", { name: "Subscribe" })).toBeInTheDocument();
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
    fireEvent.change(screen.getByLabelText("Language"), { target: { value: "hi" } });
    expect(await screen.findByRole("heading", { name: "आज की स्थिति" })).toBeInTheDocument();
    expect(window.localStorage.getItem("school-air-alert-language")).toBe("hi");
  });

  it("keeps the selected language while navigating between pages", async () => {
    loadSchoolHistory.mockResolvedValue({
      school: { school_id: "demo-school", name: "Demo School" },
      days: 30, counts: { green: 0, yellow: 0, red: 0 }, daily: [], mode: "demo",
    });
    mockThemeDashboard();
    renderApp();
    const languageSelect = await screen.findByLabelText("Language");
    fireEvent.change(languageSelect, { target: { value: "hi" } });
    fireEvent.click(screen.getByRole("link", { name: "मासिक रिपोर्ट" }));

    expect(await screen.findByRole("heading", { name: "मासिक रिपोर्ट कार्ड" })).toBeInTheDocument();
    expect(screen.getByLabelText("भाषा")).toHaveValue("hi");
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

  it("renders saved daily forecast summaries without filling missing readings", async () => {
    loadSchoolHistory.mockResolvedValue({
      school: { school_id: "demo-school", name: "Demo School" },
      days: 30,
      counts: { green: 1, yellow: 1, red: 0 },
      daily: [
        { date: "2026-10-08", status: "GREEN", average_pm25: 24, peak_pm25: 31 },
        { date: "2026-10-09", status: "YELLOW", average_pm25: null, peak_pm25: null },
      ],
      mode: "live",
    });
    renderApp(["/report?school_id=demo-school"]);

    expect(await screen.findByText("2 saved days")).toBeInTheDocument();
    expect(screen.getByText("2026-10-08")).toBeInTheDocument();
    expect(screen.getByText("2026-10-09")).toBeInTheDocument();
    expect(screen.getByText("24 µg/m³")).toBeInTheDocument();
    expect(screen.getAllByText("—")).toHaveLength(2);
    expect(screen.getByText("Saved forecast status")).toBeInTheDocument();
  });

  it("shows the existing error state when report loading fails", async () => {
    loadSchools.mockRejectedValue(new Error("request failed"));
    renderApp(["/report?school_id=demo-school"]);

    expect(await screen.findByRole("heading", { name: "Could not load the forecast" })).toBeInTheDocument();
    expect(screen.getByText("The dashboard data is unavailable right now.")).toBeInTheDocument();
  });

  it("renders a printable poster for a requested school", async () => {
    loadSchoolStatus.mockResolvedValue({
      school: { school_id: "demo-school", name: "Demo School" },
      date: "2026-10-09", status: "GREEN", average_pm25: 32, peak_pm25: 45,
      best_window: null, worst_window: null, retrieved_at: "2026-10-09T00:00:00Z", mode: "demo",
      source: { provider: "Illustrative source", model: "Demo model" },
    });
    renderApp(["/poster?school_id=demo-school"]);
    expect(await screen.findByRole("heading", { name: "Demo School" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Print poster" })).toBeInTheDocument();
    expect(screen.getByRole("list").children).toHaveLength(3);
    expect(screen.getByText("32 µg/m³")).toBeInTheDocument();
    expect(screen.getByText("45 µg/m³")).toBeInTheDocument();
    expect(screen.getByText("Forecast source: Illustrative source")).toBeInTheDocument();
  });
});
