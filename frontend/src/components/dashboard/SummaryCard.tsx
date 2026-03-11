"use client";

import type { RecommendationDetail } from "@/lib/types";

function fmt(val: number, style: "percent" | "number" = "percent"): string {
  if (style === "percent") return (val * 100).toFixed(2) + "%";
  return val.toFixed(2);
}

export default function SummaryCard({ data }: { data: RecommendationDetail }) {
  const bt = data.backtest;
  const numStocks = Object.keys(data.ticker_weights).length;

  const cards = [
    { label: "Stocks Selected", value: String(numStocks), color: "text-white" },
    {
      label: "Cumulative Return",
      value: bt ? fmt(bt.cumulative_return) : "N/A",
      color: bt && bt.cumulative_return >= 0 ? "text-emerald-400" : "text-red-400",
    },
    { label: "Sharpe Ratio", value: bt ? fmt(bt.sharpe_ratio, "number") : "N/A", color: "text-cyan-400" },
    {
      label: "vs S&P 500",
      value: bt ? fmt(bt.benchmark_return) : "N/A",
      color: "text-gray-300",
    },
    {
      label: "Max Drawdown",
      value: bt ? fmt(bt.max_drawdown) : "N/A",
      color: "text-amber-400",
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
      {cards.map((c) => (
        <div key={c.label} className="rounded-xl border border-gray-800 bg-gray-900/60 p-4">
          <p className="text-xs text-gray-500">{c.label}</p>
          <p className={`mt-1 text-2xl font-bold ${c.color}`}>{c.value}</p>
        </div>
      ))}
    </div>
  );
}
