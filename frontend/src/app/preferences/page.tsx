"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { motion, AnimatePresence } from "framer-motion";

const RISK_LEVELS = [
  { value: "conservative", label: "Conservative", desc: "Prioritize stability and lower volatility" },
  { value: "moderate", label: "Moderate", desc: "Balance between growth and risk management" },
  { value: "aggressive", label: "Aggressive", desc: "Maximize growth potential, accept higher swings" },
];
const INDICATOR_OPTIONS = [
  { key: "momentum", label: "Momentum", desc: "Favor stocks with strong recent price trends" },
  { key: "low_volatility", label: "Low Volatility", desc: "Prefer stocks with steadier price action" },
  { key: "value", label: "Value Orientation", desc: "Look for stocks trading below their averages" },
];

const MARKET_CAP_OPTIONS = [
  { value: "small", label: "Small Cap", desc: "Smaller companies (under $7B market cap)" },
  { value: "mid", label: "Mid Cap", desc: "Mid-size companies ($7B – $20B)" },
  { value: "large", label: "Large Cap", desc: "Large companies ($20B+)" },
];

const TOTAL_STEPS = 5;

export default function PreferencesPage() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [sectorsList, setSectorsList] = useState<string[]>([]);
  const [sectors, setSectors] = useState<string[]>([]);
  const [risk, setRisk] = useState("moderate");
  const [marketCapBuckets, setMarketCapBuckets] = useState<string[]>([]);
  const [excluded, setExcluded] = useState("");
  const [indicators, setIndicators] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.getSectors().then(setSectorsList).catch(() => setSectorsList([]));
  }, []);

  const toggleSector = (s: string) =>
    setSectors((prev) => (prev.includes(s) ? prev.filter((x) => x !== s) : [...prev, s]));

  const toggleIndicator = (k: string) =>
    setIndicators((prev) => ({ ...prev, [k]: !prev[k] }));

  const toggleMarketCap = (v: string) =>
    setMarketCapBuckets((prev) => (prev.includes(v) ? prev.filter((x) => x !== v) : [...prev, v]));

  const handleGenerate = async () => {
    setError("");
    setLoading(true);
    try {
      await api.savePreferences({
        sectors,
        risk_tolerance: risk,
        excluded_tickers: excluded.split(",").map((t) => t.trim().toUpperCase()).filter(Boolean),
        indicator_preferences: indicators,
        market_cap_buckets: marketCapBuckets,
      });
      const rec = await api.generateRecommendation();
      router.push(`/dashboard?id=${rec.id}`);
    } catch (err: any) {
      setError(err.message || "Failed to generate recommendation");
      setLoading(false);
    }
  };

  const stepContent = [
    // Step 0: Sectors
    <div key="sectors" className="space-y-4">
      <h2 className="text-2xl font-bold">Which sectors interest you?</h2>
      <p className="text-sm text-gray-400">Select one or more. Leave empty for all sectors.</p>
      <div className="flex flex-wrap gap-3">
        {sectorsList.length === 0 && <p className="text-sm text-gray-500">Loading sectors…</p>}
        {sectorsList.map((s) => (
          <button
            key={s}
            onClick={() => toggleSector(s)}
            className={`rounded-full border px-5 py-2 text-sm font-medium transition ${
              sectors.includes(s) ? "border-emerald-500 bg-emerald-500/20 text-emerald-300" : "border-gray-700 text-gray-400 hover:border-gray-500"
            }`}
          >
            {s}
          </button>
        ))}
      </div>
    </div>,

    // Step 1: Risk
    <div key="risk" className="space-y-4">
      <h2 className="text-2xl font-bold">What is your risk tolerance?</h2>
      <div className="space-y-3">
        {RISK_LEVELS.map((r) => (
          <button
            key={r.value}
            onClick={() => setRisk(r.value)}
            className={`w-full rounded-xl border p-4 text-left transition ${
              risk === r.value ? "border-emerald-500 bg-emerald-500/10" : "border-gray-700 hover:border-gray-500"
            }`}
          >
            <span className="font-semibold">{r.label}</span>
            <p className="mt-1 text-sm text-gray-400">{r.desc}</p>
          </button>
        ))}
      </div>
    </div>,

    // Step 2: Market cap
    <div key="marketcap" className="space-y-4">
      <h2 className="text-2xl font-bold">Market cap preference?</h2>
      <p className="text-sm text-gray-400">Optional. Select one or more to limit allocation to those sizes. Leave empty for no filter.</p>
      <div className="space-y-3">
        {MARKET_CAP_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            onClick={() => toggleMarketCap(opt.value)}
            className={`w-full rounded-xl border p-4 text-left transition ${
              marketCapBuckets.includes(opt.value) ? "border-emerald-500 bg-emerald-500/10" : "border-gray-700 hover:border-gray-500"
            }`}
          >
            <span className="font-semibold">{opt.label}</span>
            <p className="mt-1 text-sm text-gray-400">{opt.desc}</p>
          </button>
        ))}
      </div>
    </div>,

    // Step 3: Exclusions
    <div key="exclusions" className="space-y-4">
      <h2 className="text-2xl font-bold">Any companies to exclude?</h2>
      <p className="text-sm text-gray-400">Optional. Enter ticker symbols separated by commas.</p>
      <input
        type="text"
        placeholder="e.g. TSLA, HOOD"
        value={excluded}
        onChange={(e) => setExcluded(e.target.value)}
        className="w-full rounded-lg border border-gray-700 bg-gray-800 px-4 py-3 text-sm focus:border-emerald-500 focus:outline-none"
      />
    </div>,

    // Step 4: Indicators
    <div key="indicators" className="space-y-4">
      <h2 className="text-2xl font-bold">Any indicator preferences?</h2>
      <p className="text-sm text-gray-400">Optional. These influence how the AI weighs different signals.</p>
      <div className="space-y-3">
        {INDICATOR_OPTIONS.map((opt) => (
          <button
            key={opt.key}
            onClick={() => toggleIndicator(opt.key)}
            className={`w-full rounded-xl border p-4 text-left transition ${
              indicators[opt.key] ? "border-emerald-500 bg-emerald-500/10" : "border-gray-700 hover:border-gray-500"
            }`}
          >
            <span className="font-semibold">{opt.label}</span>
            <p className="mt-1 text-sm text-gray-400">{opt.desc}</p>
          </button>
        ))}
      </div>
    </div>,
  ];

  return (
    <main className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-lg space-y-6">
        <div className="flex justify-end gap-2">
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
            onClick={() => {
              setStep(0);
              setSectors([]);
              setRisk("moderate");
              setMarketCapBuckets([]);
              setExcluded("");
              setIndicators({});
            }}
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
        {/* Progress bar */}
        <div className="flex items-center gap-2">
          {Array.from({ length: TOTAL_STEPS }).map((_, i) => (
            <div key={i} className={`h-1.5 flex-1 rounded-full transition-colors ${i <= step ? "bg-emerald-500" : "bg-gray-800"}`} />
          ))}
        </div>
        <p className="text-xs text-gray-500">Step {step + 1} of {TOTAL_STEPS}</p>

        <AnimatePresence mode="wait">
          <motion.div
            key={step}
            initial={{ opacity: 0, x: 30 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -30 }}
            transition={{ duration: 0.2 }}
          >
            {stepContent[step]}
          </motion.div>
        </AnimatePresence>

        {error && <p className="text-sm text-red-400">{error}</p>}

        <div className="flex justify-between pt-2">
          <button
            onClick={() => (step > 0 ? setStep(step - 1) : router.push("/"))}
            className="rounded-lg border border-gray-700 px-5 py-2.5 text-sm text-gray-400 transition hover:border-gray-500"
          >
            Back
          </button>

          {step < TOTAL_STEPS - 1 ? (
            <button
              onClick={() => setStep(step + 1)}
              className="rounded-lg bg-emerald-600 px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-emerald-500"
            >
              Continue
            </button>
          ) : (
            <button
              onClick={handleGenerate}
              disabled={loading}
              className="rounded-lg bg-emerald-600 px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-emerald-500 disabled:opacity-50"
            >
              {loading ? "Generating..." : "Generate Recommendations"}
            </button>
          )}
        </div>
      </div>
    </main>
  );
}
