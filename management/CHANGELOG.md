# Changelog

> All notable changes to Dynamic Portfolio Optimization are documented here.
> Format: [vMAJOR.MINOR.PATCH] — YYYY-MM-DD
> Versions are appended at the TOP (newest first).

---

## [v0.2.8] — 2026-03-03

### Updated

- **Recommendation cap (max 8 stocks) + risk-based diversification:** No recommendation may contain more than 8 stocks. Risk tolerance now sets the effective max number of names: conservative → up to 8, moderate → up to 6, aggressive → up to 4. After each optimizer step in `BacktestEngine._rebalance()`, weights are truncated to the top N by weight (N = min(8, risk-based max)), other weights zeroed, and the vector renormalized to sum to 1. Config: `MAX_RECOMMENDED_STOCKS` and `RISK_TO_MAX_STOCKS` in `backend/app/ml/config.py`; pipeline passes `risk_tolerance` into `BacktestEngine` for both serve and train paths. No DB or API response shape changes.

---

## [v0.2.7] — 2026-03-11

### Added

- **Recommendation history:** After login, users see a **history** icon and a **start new search** icon. The history page (**/history**) lists past recommendations; each row shows a preference preview and “Model trained on &lt;date&gt;”; clicking a row opens the dashboard for that recommendation. **Backend:** **GET /api/recommendations** returns the user’s list with `id`, `generated_at`, `model_run_id`, `model_run_date`, and `preference_snapshot` (JSONB: sectors, risk_tolerance, excluded_tickers, indicator_preferences, market_cap_buckets). **Frontend:** `getRecommendationHistory()` in `src/lib/api.ts`; types `RecommendationHistoryItem` and `RecommendationHistoryResponse`. **Existing DBs:** add column `recommendations.preference_snapshot JSONB` if not using create_all() from scratch.

---

## [v0.2.6] — 2026-03-11

### Updated

- **Dynamic sectors for preferences:** Sector choices in the preferences UI now come from the database. **GET /api/stocks/sectors** returns distinct sector names from `stock_metadata`; the frontend fetches this on load and uses it for the sector step (no more hardcoded list).
- **Market cap preference:** New user preference **market_cap_buckets** (list: small, mid, large). When the user selects one or more, the pipeline filters the ticker universe by `stock_metadata.market_cap_bucket` before allocation; when none are selected, no market-cap filter is applied. Backend: `UserPreference.market_cap_buckets`, `RecommendationRequest.market_cap_buckets`, pipeline `_load_ticker_market_cap_map` and `_filter_tickers(..., market_cap_buckets, ...)`. Frontend: new step in the preferences wizard (5 steps: sectors → risk → market cap → exclusions → indicators).

---

## [v0.2.5] — 2026-03-11

### Updated

- **Stock metadata from yfinance:** Price ingestion now fills `stock_metadata.sector`, `name`, and `market_cap_bucket` from yfinance when creating or updating rows. New tickers get sector/name/market cap from `Ticker.info` (with fallbacks to "Unknown" and null). On each run, metadata is refreshed from yfinance so existing rows that had "Unknown" or null are updated. Market cap is mapped to buckets: large (≥10B), mid (≥2B), small (<2B USD).

---

## [v0.2.4] — 2026-03-11

### Updated

- **Indicator preferences wired to pipeline:** Optional user preferences for Momentum, Low Volatility, and Value Orientation now influence allocations. `indicator_preferences` is passed from the API (payload or saved UserPreference) through the recommendation service and pipeline into `BacktestEngine`. At each rebalance, per-asset scores derived from existing features (trend_20, trend_50, volatility, smi) are z-scored and combined with the user’s selected indicators; a configurable return tilt (`TILT_STRENGTH` in `ml/config.py`) is added to model predictions before portfolio optimization. Frontend keys: `momentum`, `low_volatility`, `value`.

---

## [v0.2.3] — 2026-03-10

### Updated

- **Deterministic recommendations:** Variational LSTM now uses the latent mean (`z_mean`) only at inference (`training=False`), so the same user preferences and model run produce the same allocation every time. Sampling is still used during training for the reparameterization trick.

---

## [v0.2.2] — 2026-03-10

### Updated

- Implemented explicit ML train-vs-serve workflow: train path saves model weights artifact, serve path loads weights from `model_runs.model_artifact_path`.
- Added `model_runs` write path via `model_training_service.py` (records hyperparameters, ticker universe, data dates, artifact path, sharpe/training loss).
- Recommendation generation now reads latest `model_runs` row, serves with that model, and writes `Recommendation.model_run_id` for traceability.
- Added fallback policy: if no model run exists, recommendation flow trains and records one on-demand before serving.

---

## [v0.2.1] — 2026-03-10

### Updated

- Price ingestion source switched from Alpaca to yfinance due API key access issues.
- `backend/app/services/price_data_service.py` now fetches adjusted daily bars with yfinance and upserts into `price_series`.
- Ingestion keeps the same DB write contract: ensure `stock_metadata`, incremental fetch by last stored date, and idempotent upsert on `(ticker, date)`.

---

## [v0.2.0] — 2026-03-10

### Updated

- ML data loader is now DB-backed and reads OHLCV from `price_series` (no yfinance/cache fallback path).
- `DataLoader.fetch_data(session)` now requires a DB session and fails fast when session/data is missing.
- Pipeline callers now pass a dedicated sync SQLAlchemy session in the ML thread path.
- `backend/app/ml/data_loader_copy.py` removed after porting finalized logic to `backend/app/ml/data_loader.py`.

### Notes

- Added sync PostgreSQL driver dependency (`psycopg[binary]`) to support thread-side sync reads.
- Loader output contract is unchanged (MultiIndex columns: ticker × Open/High/Low/Close/Volume), so feature engineering and tensor creation remain compatible.

---

## [v0.1.0] — 2026-03-01

### Established

- Full Docker Compose stack: FastAPI (8000), Next.js (5000), PostgreSQL (5432), Redis (6379)
- JWT auth system: register, login, 24h token expiry (bcrypt + python-jose)
- 7-table PostgreSQL schema: users, user_preferences, recommendations,
backtest_results, explanation_snapshots, stock_metadata, model_runs
- ML pipeline (end-to-end):
  - yfinance data loader — 7 features (log_ret, volatility, trend_20, trend_50,
  beta, log_vol, smi), 4yr window
  - Variational LSTM — Input→LSTM(64)→Dense(32)[z_mean/z_log_var]→Sampling→
  Dense(64,relu)→Dense(1)[return_mean/log_var]
  - SLSQP portfolio optimizer — objective: Return/MaxDrawdown + α×Return
  - Walk-forward backtest — quarterly retrain, monthly rebalance, daily P&L vs SPY
  - Plain-English explanation generator per ticker
- 9 REST endpoints across auth / preferences / recommendations / stocks
- Next.js frontend: landing page, 4-step preferences wizard, recommendation dashboard
- Dashboard components: SummaryCard, AllocationChart (pie), PerformanceChart (line),
ExplanationCard
- Ticker universe: TSLA, HOOD, NVDA, LEU, AMZN, BE, GOOGL, ORCL, AAPL, ASPI, OKLO,
QQQ, SPY (SPY = benchmark only)
- Risk→Alpha mapping: conservative=0.3, moderate=0.72, aggressive=1.2
- Inline data cache: /app/data/raw_ticker_data.pkl (gitignored)
- Key hyperparameters: LOOKBACK=66, FORECAST_HORIZON=21, EPOCHS=10, HIDDEN_DIM=64,
LATENT_DIM=32, BATCH_SIZE=1024, LR=0.001

### Known Limitations at Baseline

- No Alembic migrations yet (uses create_all() on startup)
- model_runs table exists but is not wired into the recommendation pipeline
- No pagination on GET /recommendations endpoints
- Frontend has no error boundary components
- Redis cache is not yet used by the ML pipeline (reserved for future)

