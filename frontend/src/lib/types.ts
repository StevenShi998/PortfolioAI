export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface UserResponse {
  id: string;
  email: string;
  created_at: string;
}

export interface Preferences {
  sectors: string[];
  risk_tolerance: string;
  excluded_tickers: string[];
  indicator_preferences: Record<string, boolean>;
  market_cap_buckets: string[];
}

export interface PreferencesResponse extends Preferences {
  id: string;
  user_id: string;
  created_at: string;
}

export interface BacktestResult {
  start_date: string;
  end_date: string;
  cumulative_return: number;
  annualized_return: number;
  sharpe_ratio: number;
  max_drawdown: number;
  benchmark_return: number;
  daily_values: { date: string; value: number }[];
}

export interface Explanation {
  ticker: string;
  allocation_pct: number;
  reasoning_text: string;
  metrics: {
    predicted_return: number;
    predicted_volatility: number;
    trend_20: number | null;
    trend_50: number | null;
    beta: number | null;
    smi: number | null;
    volatility: number | null;
  };
}

export interface RecommendationDetail {
  id: string;
  ticker_weights: Record<string, number>;
  generated_at: string;
  backtest: BacktestResult | null;
  explanations: Explanation[];
}

export interface RecommendationHistoryItem {
  id: string;
  generated_at: string;
  model_run_id: string | null;
  model_run_date: string | null;
  preference_snapshot: {
    sectors?: string[];
    risk_tolerance?: string;
    excluded_tickers?: string[];
    indicator_preferences?: Record<string, boolean>;
    market_cap_buckets?: string[];
  };
}

export interface RecommendationHistoryResponse {
  items: RecommendationHistoryItem[];
}

export interface StockMetadata {
  ticker: string;
  name: string;
  sector: string;
  market_cap_bucket: string | null;
}
