import { mockDashboardData } from "./mockData.js";

// The backend currently exposes health only. Replace this demo provider when
// the F9 status response is available; route all future HTTP through this file.
export async function loadDashboardData() {
  return mockDashboardData;
}
