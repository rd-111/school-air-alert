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
        <LineChart data={hourly} margin={{ top: 16, right: 12, bottom: 4, left: -12 }}>
          <CartesianGrid stroke="#e2e9e6" strokeDasharray="4 4" />
          {bestWindow && (
            <ReferenceArea x1={bestWindow.start} x2={bestWindow.end} fill="#8ecfb1" fillOpacity={0.25} />
          )}
          <XAxis dataKey="time" tickLine={false} axisLine={false} minTickGap={24} />
          <YAxis tickLine={false} axisLine={false} width={42} />
          <Tooltip formatter={(value) => [`${value} ${labels.pm25Unit}`, labels.pm25Short]} />
          <Line
            type="monotone"
            dataKey="pm25"
            name={labels.pm25Short}
            stroke="#176b52"
            strokeWidth={3}
            dot={false}
            activeDot={{ r: 5 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
