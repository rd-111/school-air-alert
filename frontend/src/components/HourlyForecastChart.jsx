import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export default function HourlyForecastChart({ hourly, bestWindow, labels }) {
  if (!hourly?.length) {
    return <p className="chart-empty">{labels.noHourlyData}</p>;
  }

  return (
    <div className="chart-wrap" role="img" aria-label={labels.chartDescription}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={hourly} margin={{ top: 14, right: 14, bottom: 4, left: 0 }}>
          <CartesianGrid stroke="var(--chart-grid)" strokeDasharray="4 4" />
          {bestWindow && (
            <ReferenceArea x1={bestWindow.start} x2={bestWindow.end} fill="var(--chart-highlight)" fillOpacity={0.22} />
          )}
          <XAxis dataKey="time" tick={{ fill: "var(--muted)", fontSize: 12 }} tickLine={false} axisLine={false} minTickGap={28} interval="preserveStartEnd" />
          <YAxis tick={{ fill: "var(--muted)", fontSize: 12 }} tickLine={false} axisLine={false} width={48} />
          <Tooltip
            cursor={{ stroke: "var(--chart-grid)" }}
            contentStyle={{ backgroundColor: "var(--chart-tooltip)", borderColor: "var(--chart-tooltip-border)", borderRadius: 12, color: "var(--ink)", boxShadow: "var(--shadow-hover)", fontSize: 14 }}
            labelStyle={{ color: "var(--ink)" }}
            itemStyle={{ color: "var(--ink)" }}
            formatter={(value) => [`${value} ${labels.pm25Unit}`, labels.pm25Short]}
          />
          <Line
            type="monotone"
            dataKey="pm25"
            name={labels.pm25Short}
            stroke="var(--chart-line)"
            strokeWidth={3}
            dot={false}
            activeDot={{ r: 5, fill: "var(--surface)", stroke: "var(--chart-line)", strokeWidth: 2 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
