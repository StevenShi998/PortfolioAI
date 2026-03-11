"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";

const FEATURES = [
  { title: "AI-Driven Analysis", desc: "Variational deep learning models analyze thousands of data points to surface opportunities." },
  { title: "Backtested Results", desc: "Every recommendation is validated against historical market data and benchmarked against the S&P 500." },
  { title: "Plain-English Explanations", desc: "No jargon. Understand exactly why each stock is recommended in simple terms." },
];

export default function LandingPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"idle" | "login" | "register">("idle");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      if (mode === "register") {
        await api.register(email, password);
      }
      await api.login(email, password);
      router.push("/preferences");
    } catch (err: any) {
      setError(err.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  if (mode !== "idle") {
    return (
      <main className="flex min-h-screen items-center justify-center px-4">
        <form onSubmit={handleSubmit} className="w-full max-w-sm space-y-5 rounded-2xl border border-gray-800 bg-gray-900 p-8">
          <h2 className="text-2xl font-bold">{mode === "login" ? "Welcome Back" : "Create Account"}</h2>
          {error && <p className="text-sm text-red-400">{error}</p>}
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="w-full rounded-lg border border-gray-700 bg-gray-800 px-4 py-3 text-sm focus:border-emerald-500 focus:outline-none"
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={6}
            className="w-full rounded-lg border border-gray-700 bg-gray-800 px-4 py-3 text-sm focus:border-emerald-500 focus:outline-none"
          />
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-emerald-600 py-3 text-sm font-semibold text-white transition hover:bg-emerald-500 disabled:opacity-50"
          >
            {loading ? "Please wait..." : mode === "login" ? "Log In" : "Sign Up & Continue"}
          </button>
          <p className="text-center text-xs text-gray-500">
            {mode === "login" ? "Don't have an account?" : "Already have an account?"}{" "}
            <button type="button" onClick={() => setMode(mode === "login" ? "register" : "login")} className="text-emerald-400 underline">
              {mode === "login" ? "Sign up" : "Log in"}
            </button>
          </p>
          <button type="button" onClick={() => setMode("idle")} className="block w-full text-center text-xs text-gray-600 hover:text-gray-400">
            Back
          </button>
        </form>
      </main>
    );
  }

  return (
    <main className="flex min-h-screen flex-col">
      {/* Hero */}
      <section className="flex flex-1 flex-col items-center justify-center px-4 text-center">
        <h1 className="text-5xl font-extrabold tracking-tight sm:text-6xl">
          <span className="bg-gradient-to-r from-emerald-400 to-cyan-400 bg-clip-text text-transparent">PortfolioAI</span>
        </h1>
        <p className="mt-4 max-w-xl text-lg text-gray-400">
          AI-powered stock recommendations backed by data. Get a personalized portfolio in minutes, explained in plain English.
        </p>
        <div className="mt-8 flex gap-3">
          <button
            onClick={() => setMode("register")}
            className="rounded-lg bg-emerald-600 px-6 py-3 text-sm font-semibold text-white transition hover:bg-emerald-500"
          >
            Get Started
          </button>
          <button
            onClick={() => setMode("login")}
            className="rounded-lg border border-gray-700 px-6 py-3 text-sm font-semibold text-gray-300 transition hover:border-gray-500"
          >
            Log In
          </button>
        </div>
      </section>

      {/* Features */}
      <section className="mx-auto grid max-w-5xl grid-cols-1 gap-6 px-6 pb-20 sm:grid-cols-3">
        {FEATURES.map((f) => (
          <div key={f.title} className="rounded-xl border border-gray-800 bg-gray-900/60 p-6">
            <h3 className="text-lg font-semibold text-emerald-400">{f.title}</h3>
            <p className="mt-2 text-sm leading-relaxed text-gray-400">{f.desc}</p>
          </div>
        ))}
      </section>
    </main>
  );
}
