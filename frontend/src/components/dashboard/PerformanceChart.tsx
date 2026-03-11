"use client";

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";
import type { BacktestResult } from "@/lib/types";

interface Props {
  backtest: BacktestResult;
}

export default function PerformanceChart({ backtest }: Props) {
  const dailyValues = backtest.daily_values;
  if (!dailyValues || dailyValues.length === 0) return <p className="text-sm text-gray-500">No performance data</p>;

  const benchmarkStart = 1.0;
  const benchmarkEnd = 1 + backtest.benchmark_return;
  const n = dailyValues.length;

  const chartData = dailyValues.map((d, i) => ({
    date: d.date,
    portfolio: Math.round(d.value * 10000) / 10000,
    benchmark: Math.round((benchmarkStart + (benchmarkEnd - benchmarkStart) * (i / Math.max(n - 1, 1))) * 10000) / 10000,
  }));

  return (
    <ResponsiveContainer width="100%" height={320}>
      <LineChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
        <XAxis
          dataKey="date"
          tick={{ fill: "#9ca3af", fontSize: 11 }}
          tickFormatter={(v) => {
            const d = new Date(v);
            return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
          }}
          interval={Math.max(Math.floor(chartData.length / 8), 1)}
        />
        <YAxis tick={{ fill: "#9ca3af", fontSize: 11 }} domain={["auto", "auto"]} />
        <Tooltip
          contentStyle={{ backgroundColor: "#1f2937", border: "1px solid #374151", borderRadius: 8, fontSize: 12 }}
          labelFormatter={(v) => `Date: ${v}`}
          formatter={(v: number, name: string) => [`${v.toFixed(4)}x`, name === "portfolio" ? "Portfolio" : "S&P 500"]}
        />
        <Legend />
        <Line type="monotone" dataKey="portfolio" stroke="#10b981" strokeWidth={2} dot={false} name="Portfolio" />
        <Line type="monotone" dataKey="benchmark" stroke="#6b7280" strokeWidth={2} strokeDasharray="5 5" dot={false} name="S&P 500" />
      </LineChart>
    </ResponsiveContainer>
  );
}
