# Agent Working Context

> **Last Updated:** 2026-03-11  
> **Current Version:** v0.2.8  
> **Next Target Version:** v0.2.9  
> **Stack:** FastAPI + Next.js + PostgreSQL + Redis + TensorFlow / Docker Compose

---

## 🎯 Current Sprint Goal

Next focus: **periodic training trigger / monitoring**, or other backlog items. Recommendation cap + risk-based diversification is **completed**.

---

## 🔧 In Progress (actively being changed)

*None.*

---

## ✅ Completed (concise technical overview)

- **Data loader DB path:** DB-only fetch from `price_series` in `data_loader.py`; no yfinance fallback; callers pass session.
- **Price ingestion:** `price_data_service.py` — yfinance adjusted daily bars → ensure `stock_metadata` → upsert `price_series` by (ticker, date). Supports initial backfill and daily incremental; scheduling deferred.
- **Model train vs serve + model_runs:** Train path saves artifact and inserts `model_runs`; serve path loads latest model from `model_runs`, runs backtest with user preferences, sets `Recommendation.model_run_id`. Fallback: if no run exists, train+record on-demand then serve.
- **Deterministic inference:** Variational LSTM uses `z_mean` only at inference (`training=False`), so same preferences + model run → same allocation.
- **Indicator preferences:** Optional `indicator_preferences` (momentum, low_volatility, value) wired API → service → pipeline → BacktestEngine. At each rebalance, feature-based scores (momentum, low vol, value) are z-scored and combined with user prefs; return tilt (strength `TILT_STRENGTH`) is added to model predictions before optimization, so allocations reflect how the user wants to weigh signals.
- **Dynamic sectors + market cap preference:** Sector choices in the preferences UI come from **GET /api/stocks/sectors** (distinct sectors from `stock_metadata`). User preference **market_cap_buckets** (list: small, mid, large) added; when non-empty, pipeline filters tickers by `stock_metadata.market_cap_bucket` before allocation. Empty = no market-cap filter. Backend: `UserPreference.market_cap_buckets`, pipeline `_load_ticker_market_cap_map` and `_filter_tickers(..., market_cap_buckets, ...)`. Frontend: 5-step wizard with sectors from API and new market-cap step. **Existing DBs:** add column `user_preferences.market_cap_buckets JSONB DEFAULT '[]'` if not using create_all() from scratch.
- **Recommendation history:** History icon and start-new-search icon on dashboard and preferences; **GET /api/recommendations** returns the user’s recommendations (id, generated_at, model_run_id, model_run_date, preference_snapshot). **Recommendation.preference_snapshot** (JSONB) stores sectors, risk_tolerance, excluded_tickers, indicator_preferences, market_cap_buckets at generation time. Frontend `/history` page lists rows with preference preview and “Model trained on ”; row click → `/dashboard?id=<id>`. **Existing DBs:** add column `recommendations.preference_snapshot JSONB NOT NULL DEFAULT '{}'` if the table was created before this change (no Alembic yet).
- **Recommendation cap (max 8 stocks) + risk-based diversification:** No recommendation has more than 8 stocks. Risk tolerance sets the effective max number of names: conservative → up to 8, moderate → up to 6, aggressive → up to 4 (config: `MAX_RECOMMENDED_STOCKS`, `RISK_TO_MAX_STOCKS` in `ml/config.py`). After each optimizer call in `BacktestEngine._rebalance()`, weights are truncated to the top N by weight (N = min(8, risk-based max)), zeroed elsewhere, and renormalized. Pipeline passes `risk_tolerance` into `BacktestEngine` for both serve and train paths. No DB or API shape changes.

---

## 🚫 Blockers / Known Issues


| Issue              | Location       | Severity | Notes                                      |
| ------------------ | -------------- | -------- | ------------------------------------------ |
| No Alembic         | backend/       | Medium   | Using create_all(); safe for dev, not prod |
| Redis unused by ML | ml/pipeline.py | Low      | Infrastructure ready, logic not hooked in  |


---

## 📋 Next Steps Queue (ordered by priority)

1. Decide and wire periodic training trigger (cron/APScheduler/Celery Beat) for `model_training_service.py` monthly run.
2. Add monitoring/alerting around model artifact existence and `model_runs` freshness.
3. *[Agent/owner adds more as needed]*

---

## 📐 Implementation Spec: Recommendation cap and risk-based diversification (implemented)

> **Status:** Implemented in v0.2.8. See `backend/app/ml/config.py` (MAX_RECOMMENDED_STOCKS, RISK_TO_MAX_STOCKS), `backend/app/ml/backtest_engine.py` (_truncate_weights_to_max_stocks, BacktestEngine.risk_tolerance, _rebalance truncation), and pipeline passing risk_tolerance into BacktestEngine.

**1. Cap: no more than 8 stocks per recommendation** — Enforced by truncating to top N (N ≤ 8) by weight after the optimizer and renormalizing in `_rebalance()`.

**2. Risk tolerance → number of stocks** — Conservative → 8, moderate → 6, aggressive → 4 (config `RISK_TO_MAX_STOCKS`). Effective N = min(MAX_RECOMMENDED_STOCKS, RISK_TO_MAX_STOCKS[risk_tolerance]); same top-N + renormalize in `_rebalance()`.

**3. No DB or API shape changes** — Only the number of non-zero weights in `ticker_weights` is limited.

---

## ⚠️ Agent Handoff Notes

> Critical context that would take a human 30 min to rediscover — write it here.

- `docker compose down -v` wipes ALL data including the DB; use `docker compose down` to stop without data loss.
- **Price data:** yfinance adjusted daily bars → `price_series` (OHLC adjusted via `auto_adjust=True`). Data loader is DB-only.
- **Ingestion:** `price_data_service.py` supports backfill and incremental; scheduling (cron/APScheduler, etc.) deferred.
- **ML pipeline** blocks ~60s; runs in ThreadPoolExecutor in `recommendation_service.py` so FastAPI stays responsive.
- **Data loader:** Do not change `calculate_features` or `create_tensors`; they require the exact MultiIndex DataFrame shape. If session or data missing, log and raise.
- **Model workflow:** Train path saves artifact + `model_runs`; serve path loads latest artifact, sets `Recommendation.model_run_id`. No run → on-demand train+record then serve.
- **Deterministic inference:** LSTM uses `z_mean` only at inference; sampling only when `training=True`.
- **Indicator preferences:** Optional dict `momentum`, `low_volatility`, `value`. Applied in `BacktestEngine._rebalance` as a return tilt from feature-based scores; strength from `TILT_STRENGTH` in config.
- **Sectors:** Distinct list from **GET /api/stocks/sectors** (from `stock_metadata`); preferences UI fetches this for sector choices.
- **Market cap filter:** User preference `market_cap_buckets` (small/mid/large). When set, pipeline restricts allocation to tickers whose `stock_metadata.market_cap_bucket` is in the list; empty = no filter.
- **Recommendation history (implemented):** History and start-new-search icons on dashboard and preferences; **GET /api/recommendations** lists user’s recommendations with `preference_snapshot` and `model_run_date`; `/history` page shows rows; row click → `/dashboard?id=<id>`. `Recommendation.preference_snapshot` populated at creation. Existing DBs need `ALTER TABLE recommendations ADD COLUMN preference_snapshot JSONB NOT NULL DEFAULT '{}'` if table predates this feature.
- **Recommendation cap + risk diversification (implemented):** (1) Hard cap: no more than 8 stocks per recommendation. (2) Risk tolerance sets max names: conservative 8, moderate 6, aggressive 4. Applied in `BacktestEngine._rebalance()` via top-N truncation + renormalize after optimizer; config in `ml/config.py` (MAX_RECOMMENDED_STOCKS, RISK_TO_MAX_STOCKS); pipeline passes risk_tolerance to engine. See Implementation Spec above for details.
- **Sync vs async:** Backtest uses sync session in thread; AsyncSession elsewhere — use sync session or `run_sync` in that path.
- CORS in `main.py` allows only `http://localhost:3000` — update before cloud deploy.
- JWT secret default `change-me-in-production` in .env — rotate for production.

---

## 🗂️ File Map Quick Reference

> Only the files most likely to be touched — see ONBOARDING.md §1.4 for full tree.


| What you want to change                                        | File                                                                                                                   |
| -------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| ML hyperparameters / ticker universe / tilt strength           | `backend/app/ml/config.py`                                                                                             |
| ML model architecture                                          | `backend/app/ml/variational_lstm.py`                                                                                   |
| Full pipeline orchestration                                    | `backend/app/ml/pipeline.py`                                                                                           |
| Data loader (fetch + features)                                 | `backend/app/ml/data_loader.py`                                                                                        |
| Walk-forward backtest + indicator tilt                         | `backend/app/ml/backtest_engine.py`                                                                                    |
| Portfolio optimization (alpha from risk_tolerance)             | `backend/app/ml/portfolio_optimizer.py`                                                                                |
| Recommendation cap (max 8) + risk-based max names              | `backend/app/ml/backtest_engine.py`, `backend/app/ml/config.py`                                                        |
| API endpoints (stocks: metadata + sectors)                     | `backend/app/api/*.py`                                                                                                 |
| User preferences (sectors, market_cap_buckets, indicators)     | `backend/app/models/user.py`, `schemas/preferences.py`                                                                 |
| DB schema (ORM models)                                         | `backend/app/models/*.py`                                                                                              |
| Price series / stock metadata                                  | `backend/app/models/price_series.py`, `stock.py`                                                                       |
| Recommendation flow + indicator_preferences                    | `backend/app/services/recommendation_service.py`                                                                       |
| Train + record model run                                       | `backend/app/services/model_training_service.py`                                                                       |
| Pydantic schemas                                               | `backend/app/schemas/*.py`                                                                                             |
| Frontend pages / API client / types                            | `frontend/src/app/`*, `lib/api.ts`, `lib/types.ts`                                                                     |
| Recommendation history (list, preference snapshot, model date) | `backend/app/api/recommendations.py`, `models/recommendation.py`, `recommendation_service.py`, `frontend` history page |
| Docker / Python deps                                           | `docker-compose.yml`, `backend/requirements.txt`                                                                       |


