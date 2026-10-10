const values = [
  24, 22, 21, 23, 25, 28, 34, 39, 42, 38, 32, 29,
  27, 30, 35, 41, 45, 43, 39, 35, 31, 28, 26, 25,
];

export const mockDashboardData = {
  schoolName: "Demo School",
  status: "GREEN",
  advice: "Normal outdoor activities are fine.",
  averagePm25: 32,
  peakPm25: 45,
  hourly: values.map((pm25, hour) => ({
    time: `${String(hour).padStart(2, "0")}:00`,
    pm25,
  })),
  bestWindow: { start: "11:00", end: "12:00", label: "11:00–12:00" },
  worstWindow: { start: "17:00", end: "18:00", label: "17:00–18:00" },
  noSuitableWindow: false,
  activityGuidance: ["pe", "sports", "recess", "assembly", "bus_wait"].map(
    (activity) => ({ activity, guidance_code: "GENERAL_POLICY" }),
  ),
};
