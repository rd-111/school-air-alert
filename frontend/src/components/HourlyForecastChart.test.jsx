import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import HourlyForecastChart from "./HourlyForecastChart.jsx";
import en from "../i18n/en.json";

vi.mock("recharts", () => ({
  CartesianGrid: () => null,
  Line: () => null,
  LineChart: ({ data, children }) => (
    <div data-testid="line-chart" data-point-count={data.length}>{children}</div>
  ),
  ReferenceArea: () => null,
  ResponsiveContainer: ({ children }) => <div>{children}</div>,
  Tooltip: ({ formatter }) => <div data-testid="tooltip-value">{formatter(61.537499999999994)[0]}</div>,
  XAxis: ({ interval, minTickGap }) => (
    <div data-testid="x-axis" data-interval={interval} data-min-tick-gap={minTickGap} />
  ),
  YAxis: () => null,
}));

describe("hourly forecast chart", () => {
  it("keeps every data point and spaces axis labels while retaining tooltip values", () => {
    const hourly = Array.from({ length: 24 }, (_, hour) => ({
      time: `${String(hour).padStart(2, "0")}:00`,
      pm25: hour + 0.25,
    }));

    render(<HourlyForecastChart hourly={hourly} labels={en} />);

    expect(screen.getByTestId("line-chart")).toHaveAttribute("data-point-count", "24");
    expect(screen.getByTestId("x-axis")).toHaveAttribute("data-interval", "preserveStartEnd");
    expect(screen.getByTestId("x-axis")).toHaveAttribute("data-min-tick-gap", "48");
    expect(screen.getByTestId("tooltip-value")).toHaveTextContent("61.5 µg/m³");
  });
});
