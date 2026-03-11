const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class ApiClient {
  private token: string | null = null;

  constructor() {
    if (typeof window !== "undefined") {
      this.token = localStorage.getItem("token");
    }
  }

  setToken(token: string) {
    this.token = token;
    if (typeof window !== "undefined") {
      localStorage.setItem("token", token);
    }
  }

  clearToken() {
    this.token = null;
    if (typeof window !== "undefined") {
      localStorage.removeItem("token");
    }
  }

  isAuthenticated(): boolean {
    return !!this.token;
  }

  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(options.headers as Record<string, string>),
    };
    if (this.token) {
      headers["Authorization"] = `Bearer ${this.token}`;
    }
    const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || `Request failed (${res.status})`);
    }
    return res.json();
  }

  register(email: string, password: string) {
    return this.request<{ id: string; email: string }>("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
  }

  async login(email: string, password: string) {
    const data = await this.request<{ access_token: string }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    this.setToken(data.access_token);
    return data;
  }

  savePreferences(prefs: {
    sectors: string[];
    risk_tolerance: string;
    excluded_tickers: string[];
    indicator_preferences: Record<string, boolean>;
    market_cap_buckets: string[];
  }) {
    return this.request("/api/preferences", { method: "POST", body: JSON.stringify(prefs) });
  }

  getLatestPreferences() {
    return this.request<import("./types").PreferencesResponse>("/api/preferences/latest");
  }

  generateRecommendation(overrides?: {
    sectors?: string[];
    risk_tolerance?: string;
    excluded_tickers?: string[];
    indicator_preferences?: Record<string, boolean>;
    market_cap_buckets?: string[];
  }) {
    return this.request<import("./types").RecommendationDetail>(
      "/api/recommendations/generate",
      { method: "POST", body: JSON.stringify(overrides || {}) },
    );
  }

  getLatestRecommendation() {
    return this.request<import("./types").RecommendationDetail>("/api/recommendations/latest");
  }

  getRecommendation(id: string) {
    return this.request<import("./types").RecommendationDetail>(`/api/recommendations/${id}`);
  }

  getRecommendationHistory() {
    return this.request<import("./types").RecommendationHistoryResponse>("/api/recommendations");
  }

  getStockMetadata() {
    return this.request<import("./types").StockMetadata[]>("/api/stocks/metadata");
  }

  getSectors() {
    return this.request<string[]>("/api/stocks/sectors");
  }
}

export const api = new ApiClient();
