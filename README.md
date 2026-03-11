# Dynamic Portfolio Optimization — Production

Portfolio project: an AI-powered stock recommendation web app with backtested allocations and plain-English explanations. Built with Cursor assistance.

---

## Website functionalities

### User account and auth

Sign up, sign in, and session handling. User and preferences are stored in PostgreSQL.

![Landing and auth](pictures/frontpage.png)

![Account and database](pictures/account_databaselinked.png)

### Preference selection (wizard)

Step-by-step flow: sectors (from DB), risk tolerance, market cap, company exclusions, and indicator preferences (momentum, low volatility, value).

| Sectors | Risk tolerance | Indicator preferences |
|--------|----------------|------------------------|
| <img src="pictures/sectors.png" width="280" alt="Sectors" /> | <img src="pictures/risk_tolerance.png" width="280" alt="Risk tolerance" /> | <img src="pictures/indicator_pref.png" width="280" alt="Indicator preferences" /> |

### Portfolio recommendation

Dashboard with allocation chart, backtest performance, and a plain-English explanation of the recommendation.

![Recommendation dashboard](pictures/recommendation_page.png)

### Recommendation history

Past recommendations with preference snapshots and model-run dates. Click a row to open that dashboard.

![Recommendation history](pictures/recommendation_history.png)

---

## Under the hood

**Stack:** Python (FastAPI), PostgreSQL 16, Redis, Next.js (React, Tailwind). ML pipeline: Variational LSTM for return/volatility forecasts, return–drawdown optimizer (SLSQP), and walk-forward backtest.

**Data and API:** Stock metadata and price series live in Postgres. REST API covers auth, user preferences, sectors (from DB), and recommendations. Preferences and recommendation history are persisted and tied to model-run metadata.

**Full technical derivation and workflow** (model loss, optimizer formulation, backtest formulas): see **[notebook/README.md](notebook/README.md)**.

![Workflow overview](pictures/pic/workflow.png)

### Logic behind the scenes

The pipeline has three stages: predict returns and volatilities, optimize weights, then backtest.

![Logic behind the scenes](pictures/pic/logic_stages.png)

**Stage 1: Return and Volatility Prediction (Variational LSTM)**  
Learn a distribution of future returns \(p(\text{return} \mid \text{sequence})\) using a Variational LSTM.

- **Given:** Historical sequences of features (price, volume, technical indicators) for each asset over LOOKBACK = 66 days.
- **Predict:** Mean return \(\hat{\mu}\) and variance \(\hat{\sigma}^2\) over FORECAST HORIZON = 21 days.
- **Method:** Variational LSTM minimizing a time-weighted loss (time-weighted NLL + KL latent regularization + direction penalty). NLL rewards accurate predictions with appropriate uncertainty; KL keeps the latent space close to the prior; direction loss penalizes sign mismatches between predicted and actual returns.

**Stage 2: Portfolio Allocation (Return–Drawdown Optimizer)**  
Optimize portfolio weights \(w \in \mathbb{R}^n\) to maximize return/drawdown(proxy) ratio.

- **Given:** Predicted returns \(\hat{\mu}\) and volatilities \(\hat{\sigma}\) from Stage 1.
- **Find:** Weights \(w\) that solve \(\min_w -\text{ratio}(w)\) subject to \(\sum w_j = 1\), \(0 \le w_j \le 1\).
- **Ratio:** When \(\mu_p > 0\), ratio = \(\mu_p/\text{MDD} + \alpha\mu_p\); otherwise scaled by \(\mu_p\), FORECAST HORIZON, and MDD. Portfolio return \(\mu_p = w^T\hat{\mu}\); volatility \(\sigma_p = \sqrt{w^T \hat{H} w}\); max-drawdown proxy \(\text{MDD} = \max(10^{-4}, 2\sqrt{\text{HORIZON}}\cdot\sigma_p)\). Covariance \(\hat{H} = D\,\Sigma_{\text{corr}}\,D\) with \(D = \text{diag}(\hat{\sigma}_1, \ldots, \hat{\sigma}_n)\). Method: SLSQP (long-only, fully invested).

**Stage 3: Backtest (Monthly Rebalance)**  
Apply optimized weights to actual returns and compound capital. Performance measured via Sharpe ratio and cumulative returns.

- **Sharpe:** \(S = \sqrt{252} \cdot (\bar{R}_p - R_f) / \sigma_p\), with \(R_p\) portfolio return, \(R_f\) risk-free rate, \(\sigma_p\) standard deviation of excess returns.

---

## Project management and versioning

The **`management/`** folder is the central hub for this project: version tracking, current progress, and context for both humans and AI.

- **[AGENT_CONTEXT.md](management/AGENT_CONTEXT.md)** — Sprint goal, in progress, completed work, blockers, next steps, file map.
- **[CHANGELOG.md](management/CHANGELOG.md)** — Versioned releases (e.g. v0.2.8).
- **[ONBOARDING.md](management/ONBOARDING.md)** — Onboarding and project context.

This reflects how the project was run (planning, versions, handoff) as project-management experience.

---

**Note:** I'm working on model tuning for live interaction. This repo is a portfolio showcase and is not set up for local run.

## Architecture

| Service   | Description                         |
|-----------|-------------------------------------|
| frontend  | Next.js React app (Tailwind CSS)    |
| backend   | FastAPI Python API + ML engine      |
| postgres  | PostgreSQL 16 database              |
| redis     | Redis cache                         |

## Local Development (without Docker)

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Start PostgreSQL and Redis locally, then:
export DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/portfolio_opt
export REDIS_URL=redis://localhost:6379/0
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Project Structure

```
Production/
├── PLAN.md                  # Living plan document
├── README.md                # This file
├── docker-compose.yml       # One-command deployment
├── .env.example             # Environment template
├── pictures/                # App screenshots and technical images
│   └── pic/                 # Workflow and ML visuals for notebook
├── notebook/                # Technical derivation (Variational LSTM, optimizer, backtest)
│   ├── README.md
│   └── pic/
├── management/              # Version and project-management hub
│   ├── AGENT_CONTEXT.md
│   ├── CHANGELOG.md
│   └── ONBOARDING.md
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py          # FastAPI application
│       ├── config.py        # Settings (from env vars)
│       ├── database.py      # Async SQLAlchemy engine
│       ├── seed.py          # Stock metadata seeder
│       ├── models/          # SQLAlchemy ORM models
│       ├── schemas/         # Pydantic request/response schemas
│       ├── api/             # Route handlers
│       ├── services/        # Business logic (auth, recommendations)
│       └── ml/              # ML engine
│           ├── config.py            # Hyperparameters
│           ├── data_loader.py       # Yahoo Finance + features
│           ├── variational_lstm.py  # Variational LSTM model
│           ├── portfolio_optimizer.py # SLSQP weight optimizer
│           ├── backtest_engine.py   # Walk-forward backtest
│           ├── explanation_generator.py # Plain-English reasoning
│           └── pipeline.py          # End-to-end orchestrator
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   └── src/
│       ├── app/             # Next.js pages
│       │   ├── page.tsx             # Landing + auth
│       │   ├── preferences/page.tsx # Step-by-step wizard
│       │   └── dashboard/page.tsx   # Results dashboard
│       ├── components/      # React components
│       │   └── dashboard/
│       │       ├── AllocationChart.tsx
│       │       ├── PerformanceChart.tsx
│       │       ├── SummaryCard.tsx
│       │       └── ExplanationCard.tsx
│       └── lib/
│           ├── api.ts       # API client
│           └── types.ts     # TypeScript interfaces
└── model_artifacts/         # Saved model weights (gitignored)
```
