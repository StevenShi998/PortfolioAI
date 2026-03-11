"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { RecommendationDetail } from "@/lib/types";
import AllocationChart from "@/components/dashboard/AllocationChart";
import PerformanceChart from "@/components/dashboard/PerformanceChart";
import SummaryCard from "@/components/dashboard/SummaryCard";
import ExplanationCard from "@/components/dashboard/ExplanationCard";

function DashboardContent() {
  const params = useSearchParams();
  const router = useRouter();
  const [data, setData] = useState<RecommendationDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    const id = params.get("id");
    const load = async () => {
      try {
        const rec = id ? await api.getRecommendation(id) : await api.getLatestRecommendation();
        if (!cancelled) setData(rec);
      } catch (err: unknown) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load recommendation");
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    return () => { cancelled = true; };
  }, [params]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="space-y-3 text-center">
          <div className="mx-auto h-10 w-10 animate-spin rounded-full border-4 border-emerald-500 border-t-transparent" />
          <p className="text-sm text-gray-400">Loading your recommendations...</p>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4">
        <p className="text-red-400">{error || "No data available"}</p>
        <button onClick={() => router.push("/preferences")} className="rounded-lg bg-emerald-600 px-5 py-2 text-sm text-white">
          Generate New Recommendation
        </button>
      </div>
    );
  }

  return (
    <main className="mx-auto max-w-6xl px-4 py-10">
      <header className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Your Recommendations</h1>
          <p className="mt-1 text-sm text-gray-400">Generated {new Date(data.generated_at).toLocaleDateString()}</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => router.push("/history")}
            className="rounded-lg border border-gray-700 px-3 py-2 text-sm text-gray-300 transition hover:border-gray-500"
            title="Recommendation History"
            aria-label="Recommendation History"
          >
            <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5">
              <path d="M3 12a9 9 0 1 0 3-6.7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              <path d="M3 4v5h5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              <path d="M12 7v5l3 2" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
          <button
            onClick={() => router.push("/preferences")}
            className="rounded-lg border border-gray-700 px-3 py-2 text-sm text-gray-300 transition hover:border-gray-500"
            title="Start New Search"
            aria-label="Start New Search"
          >
            <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5">
              <path d="M11 4a7 7 0 1 0 4.9 12l4.6 4.6 1.4-1.4-4.6-4.6A7 7 0 0 0 11 4Z" stroke="currentColor" strokeWidth="2" />
              <path d="M11 8v6M8 11h6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </button>
        </div>
      </header>

      {/* Summary cards */}
      <SummaryCard data={data} />

      {/* Charts grid */}
      <div className="mt-8 grid gap-6 lg:grid-cols-2">
        <div className="rounded-2xl border border-gray-800 bg-gray-900/60 p-6">
          <h2 className="mb-4 text-lg font-semibold">Portfolio Allocation</h2>
          <AllocationChart weights={data.ticker_weights} />
        </div>
        <div className="rounded-2xl border border-gray-800 bg-gray-900/60 p-6">
          <h2 className="mb-4 text-lg font-semibold">Backtested Performance vs S&P 500</h2>
          {data.backtest ? <PerformanceChart backtest={data.backtest} /> : <p className="text-sm text-gray-500">No backtest data</p>}
        </div>
      </div>

      {/* Explanation cards */}
      <section className="mt-10">
        <h2 className="mb-4 text-xl font-bold">Why These Stocks?</h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {data.explanations.map((exp) => (
            <ExplanationCard key={exp.ticker} explanation={exp} />
          ))}
        </div>
      </section>
    </main>
  );
}

export default function DashboardPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-emerald-500 border-t-transparent" />
        </div>
      }
    >
      <DashboardContent />
    </Suspense>
  );
}
