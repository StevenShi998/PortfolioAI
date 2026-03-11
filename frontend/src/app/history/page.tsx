"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { api } from "@/lib/api";
import type { RecommendationHistoryItem } from "@/lib/types";

function formatModelDate(modelRunDate: string | null): string {
  if (!modelRunDate) return "Model trained on unknown date";
  return `Model trained on ${new Date(modelRunDate).toLocaleDateString()}`;
}

function previewSnapshot(item: RecommendationHistoryItem): string {
  const snap = item.preference_snapshot || {};
  const sectors = (snap.sectors || []).slice(0, 2).join(", ") || "All sectors";
  const risk = snap.risk_tolerance || "moderate";
  const caps = (snap.market_cap_buckets || []).join(", ") || "all caps";
  return `Sectors: ${sectors} | Risk: ${risk} | Cap: ${caps}`;
}

export default function HistoryPage() {
  const router = useRouter();
  const [items, setItems] = useState<RecommendationHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const response = await api.getRecommendationHistory();
        if (!cancelled) setItems(response.items);
      } catch (err: unknown) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load history");
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="h-10 w-10 animate-spin rounded-full border-4 border-emerald-500 border-t-transparent" />
      </div>
    );
  }

  return (
    <main className="mx-auto max-w-5xl px-4 py-10">
      <header className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Recommendation History</h1>
          <p className="mt-1 text-sm text-gray-400">Review your previous runs and open any result.</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => router.push("/dashboard")}
            className="rounded-lg border border-gray-700 px-4 py-2 text-sm text-gray-300 transition hover:border-gray-500"
          >
            Dashboard
          </button>
          <button
            onClick={() => router.push("/preferences")}
            className="rounded-lg border border-gray-700 px-4 py-2 text-sm text-gray-300 transition hover:border-gray-500"
          >
            Start New Search
          </button>
        </div>
      </header>

      {error && <p className="mb-4 text-sm text-red-400">{error}</p>}
      {!error && items.length === 0 && (
        <div className="rounded-xl border border-gray-800 bg-gray-900/50 p-6 text-sm text-gray-400">
          No recommendation history yet. Run your first search from Preferences.
        </div>
      )}

      <div className="space-y-3">
        {items.map((item) => (
          <button
            key={item.id}
            onClick={() => router.push(`/dashboard?id=${item.id}`)}
            className="w-full rounded-xl border border-gray-800 bg-gray-900/60 p-4 text-left transition hover:border-emerald-500/60"
          >
            <div className="flex items-center justify-between">
              <p className="text-sm font-semibold text-gray-200">{new Date(item.generated_at).toLocaleString()}</p>
              <p className="text-xs text-gray-400">{formatModelDate(item.model_run_date)}</p>
            </div>
            <p className="mt-2 text-sm text-gray-400">{previewSnapshot(item)}</p>
          </button>
        ))}
      </div>
    </main>
  );
}
