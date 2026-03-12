# Dynamic Portfolio Optimization — Production

An ML stock recommendation web app with backtested allocations and plain-English explanations. Based on my Dynamic Portfolio Optimization notebook.

---

## Website functionalities

### Account, register, and preference selection

Sign up, sign in, and session handling. User and preferences are stored in PostgreSQL. After logging in, users set preferences in a step-by-step wizard.

![Landing and auth](pictures/frontpage.png)

### User preference input

User select from DB-backed list, risk tolerance, market cap, company exclusions, and indicator preferences (momentum, low volatility, value).

| Login page | Sectors |
|------------|---------|
| <img src="pictures/account_databaselinked.png" alt="Login page" style="width:500px;height:500px;object-fit:cover;display:block" /> | <img src="pictures/sectors.png" alt="Sectors" style="width:500px;height:500px;object-fit:cover;display:block" /> |

| Risk tolerance | Indicator preferences |
|----------------|-----------------------|
| <img src="pictures/risk_tolerance.png" alt="Risk tolerance" style="width:500px;height:500px;object-fit:cover;display:block" /> | <img src="pictures/indicator_pref.png" alt="Indicator preferences" style="width:500px;height:500px;object-fit:cover;display:block" /> |

### Portfolio recommendation

Dashboard with allocation chart, backtest performance, and a plain-English explanation of the recommendation.

![Recommendation dashboard](pictures/recommendation_page.png)

### Recommendation history

Past recommendations with preference snapshots and model-run dates. Click a row to open that dashboard.

![Recommendation history](pictures/recommendation_history.png)

---

## Model architecture

### Stage 1: Return and Volatility Prediction (Variational LSTM)

Learn a distribution of future returns $p(return | sequence)$ using a Variational LSTM.

- **Given:** Historical sequences of features (price, volume, technical indicators) for each asset over $\texttt{LOOKBACK} = 66$ days
- **Predict:** Mean return $\hat{\mu}$ and variance $\hat{\sigma}^2$ over $\texttt{FORECAST HORIZON} = 21$ days
- **Method:** Variational LSTM minimizing a time-weighted loss:

$$\mathcal{L} = \underbrace{\frac{1}{N}\sum_i w_i \cdot \text{NLL}_i}_{\text{time-weighted prediction}} + \underbrace{\beta \cdot \text{KL}(q(z|x) \| p(z))}_{\text{latent regularization}} + \underbrace{0.5 \cdot \text{direction penalty}}_{\text{sign mismatch}}$$

Where:
- **NLL** (Gaussian negative log-likelihood): rewards accurate predictions with appropriate uncertainty
- **KL divergence**: regularizes latent space to stay close to prior N(0,I)
- **Direction loss**: penalizes sign mismatches between predicted and actual returns

### Stage 2: Portfolio Allocation (Return-Drawdown Optimizer)

Optimize portfolio weights $w \in \mathbb{R}^n$ to maximize return/drawdown(proxy) ratio.

- **Given:** Predicted returns $\hat{\mu}$ and volatilities $\hat{\sigma}$ from Stage 1
- **Find:** Weights $w$ that solve:

$$\min_w \; -\text{ratio}(w)$$

$$\text{subject to} \quad \sum_{j=1}^{n} w_j = 1, \quad 0 \leq w_j \leq 1$$

Where:

$$\text{ratio} = \begin{cases}
\frac{\mu_p}{\text{MDD}} + \alpha \mu_p & \text{if } \mu_p > 0 \\
\mu_p \cdot \sqrt{\texttt{FORECAST HORIZON}} \cdot \text{MDD} & \text{if } \mu_p \leq 0
\end{cases}$$

- **Portfolio return:** $\mu_p = w^T \hat{\mu}$; this is the weighted sum of predicted returns for each asset
- **Portfolio volatility:** $\sigma_p = \sqrt{w^T \hat{H} w}$
- **Max-drawdown proxy:** $\text{MDD} = \max(10^{-4}, 2\sqrt{\texttt{FORECAST HORIZON}}\cdot\sigma_p)$; $10^{-4}$ is a small constant to handle the case when $\sigma_p \approx 0$
- **Covariance:** $\hat{H} = D\cdot\Sigma_{\text{corr}}\cdot D$ where $D = \text{diag}(\hat{\sigma}_1, \ldots, \hat{\sigma}_n)$
- **Method:** SLSQP optimizer (long-only, fully invested)

### Stage 3: Backtest (Monthly Rebalance)

Monthly rebalance backtest applies optimized weights (from Stage 2) to actual returns and compounds capital. Performance measured via Sharpe ratio and cumulative returns. 

For the Sharpe ratio, we use the following formula:
$$S = \alpha \cdot \frac{\mathbb{E}[R_p - R_f]}{\sigma_p} = \sqrt{252} \cdot \frac{\bar{R}_p - R_f}{\sigma_p}$$

where:
- $R_p$: portfolio return
- $R_f$: risk-free rate
- $\sigma_p$: standard deviation of portfolio (excess) returns
- $\alpha = \sqrt{252}$: annualization factor

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
