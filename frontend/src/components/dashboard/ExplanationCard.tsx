"use client";

import { useState } from "react";
import type { Explanation } from "@/lib/types";

interface Props {
  explanation: Explanation;
}

export default function ExplanationCard({ explanation }: Props) {
  const [expanded, setExpanded] = useState(false);
  const { ticker, allocation_pct, reasoning_text, metrics } = explanation;

  return (
    <div className="rounded-xl border border-gray-800 bg-gray-900/60 p-5 transition hover:border-gray-700">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-lg font-bold text-white">{ticker}</h3>
          <p className="text-sm text-emerald-400">{allocation_pct.toFixed(1)}% of portfolio</p>
        </div>
        <span className="rounded-full bg-gray-800 px-3 py-1 text-xs text-gray-400">
          {metrics.beta !== null ? `Beta ${metrics.beta.toFixed(2)}` : ""}
        </span>
      </div>

      <p className="mt-3 text-sm leading-relaxed text-gray-300">{reasoning_text}</p>

      <button onClick={() => setExpanded(!expanded)} className="mt-3 text-xs text-emerald-400 hover:underline">
        {expanded ? "Hide metrics" : "Show metrics"}
      </button>

      {expanded && (
        <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
          <Metric label="Predicted Return" value={metrics.predicted_return} fmt="pct" />
          <Metric label="Predicted Vol" value={metrics.predicted_volatility} fmt="pct" />
          <Metric label="Trend (20d)" value={metrics.trend_20} fmt="pct" />
          <Metric label="Trend (50d)" value={metrics.trend_50} fmt="pct" />
          <Metric label="SMI" value={metrics.smi} fmt="num" />
          <Metric label="Realized Vol" value={metrics.volatility} fmt="pct" />
        </div>
      )}
    </div>
  );
}

function Metric({ label, value, fmt }: { label: string; value: number | null; fmt: "pct" | "num" }) {
  const display = value == null ? "N/A" : fmt === "pct" ? `${(value * 100).toFixed(2)}%` : value.toFixed(3);
  return (
    <div className="rounded-lg bg-gray-800/50 px-3 py-2">
      <p className="text-gray-500">{label}</p>
      <p className="font-mono text-gray-200">{display}</p>
    </div>
  );
}
