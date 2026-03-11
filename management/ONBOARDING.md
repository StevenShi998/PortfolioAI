# Dynamic Portfolio Optimization -- Onboarding Guide

> Your reference for understanding, running, checking, and modifying every part of this project.

---

## Table of Contents

- [Dynamic Portfolio Optimization -- Onboarding Guide](#dynamic-portfolio-optimization----onboarding-guide)
  - [Table of Contents](#table-of-contents)
  - [1. Project Overview](#1-project-overview)
    - [1.1 What This Project Does](#11-what-this-project-does)
    - [1.2 Architecture](#12-architecture)
    - [1.3 Tech Stack](#13-tech-stack)
    - [1.4 Complete File Map](#14-complete-file-map)
  - [2. Quick Start](#2-quick-start)
    - [2.1 Prerequisites](#21-prerequisites)
    - [2.2 Environment Setup](#22-environment-setup)
    - [2.3 Start Everything](#23-start-everything)
    - [2.4 Access the App](#24-access-the-app)
    - [2.5 Stop / Restart](#25-stop--restart)
    - [2.6 Quick Verification](#26-quick-verification)
  - [3. Backend Deep Dive](#3-backend-deep-dive)
    - [3.1 API Endpoint Reference](#31-api-endpoint-reference)
      - [Public Endpoints (no auth required)](#public-endpoints-no-auth-required)
      - [Auth Endpoints](#auth-endpoints)
      - [Authenticated Endpoints (require `Authorization: Bearer <token>`)](#authenticated-endpoints-require-authorization-bearer-token)
    - [3.2 Authentication Flow](#32-authentication-flow)
    - [3.3 Service Layer](#33-service-layer)
    - [3.4 Key Config (`backend/app/config.py`)](#34-key-config-backendappconfigpy)
  - [4. ML Engine](#4-ml-engine)
    - [4.1 Pipeline Stages](#41-pipeline-stages)
    - [4.2 Hyperparameter Reference (`backend/app/ml/config.py`)](#42-hyperparameter-reference-backendappmlconfigpy)
    - [4.3 Ticker Universe (`backend/app/ml/config.py`)](#43-ticker-universe-backendappmlconfigpy)
    - [4.4 Market cap filter (optional)](#44-market-cap-filter-optional)
    - [4.5 Indicator Preferences (optional)](#45-indicator-preferences-optional)
    - [4.6 Risk Tolerance → Alpha Mapping](#46-risk-tolerance--alpha-mapping)
    - [4.7 Model Objective Function](#47-model-objective-function)
    - [4.8 Data Source and Refresh](#48-data-source-and-refresh)
  - [5. Frontend](#5-frontend)
    - [5.1 Pages](#51-pages)
    - [5.2 User Flow](#52-user-flow)
    - [5.3 Dashboard Components](#53-dashboard-components)
    - [5.4 API Client (`src/lib/api.ts`)](#54-api-client-srclibapits)
    - [5.5 Styling](#55-styling)
    - [5.6 Frontend Development](#56-frontend-development)
  - [6. Database](#6-database)
    - [6.1 Schema Overview](#61-schema-overview)
    - [6.2 Table Details](#62-table-details)
    - [6.3 Connecting to the Database Directly](#63-connecting-to-the-database-directly)
    - [6.4 Useful SQL Queries](#64-useful-sql-queries)
    - [6.5 Redis Inspection](#65-redis-inspection)
    - [6.6 Database Reset](#66-database-reset)
    - [6.7 Future: Alembic Migrations](#67-future-alembic-migrations)
  - [7. Health Checks \& Troubleshooting](#7-health-checks--troubleshooting)
    - [7.1 Diagnostic Commands](#71-diagnostic-commands)
    - [7.2 Common Issues \& Fixes](#72-common-issues--fixes)
      - [Backend exits with code 137 (OOM)](#backend-exits-with-code-137-oom)
      - [ML loader fails with missing DB data](#ml-loader-fails-with-missing-db-data)
      - [Port already in use](#port-already-in-use)
      - [Frontend shows "Failed to fetch" errors](#frontend-shows-failed-to-fetch-errors)
      - [Database connection errors](#database-connection-errors)
      - [ML pipeline takes too long](#ml-pipeline-takes-too-long)
    - [7.3 Log Locations](#73-log-locations)
  - [8. Development Workflows](#8-development-workflows)
    - [8.1 Adding a New Ticker](#81-adding-a-new-ticker)
    - [8.2 Modifying the Frontend UI](#82-modifying-the-frontend-ui)
    - [8.3 Adding a New API Endpoint](#83-adding-a-new-api-endpoint)
    - [8.4 Modifying the ML Model](#84-modifying-the-ml-model)
    - [8.5 Training the Model and Testing the Train/Serve Workflow (Docker)](#85-training-the-model-and-testing-the-trainserve-workflow-docker)
    - [8.6 Updating Dependencies](#86-updating-dependencies)
    - [8.7 Deploying Updates](#87-deploying-updates)
    - [8.8 Backup \& Restore Database](#88-backup--restore-database)

---

## 1. Project Overview

### 1.1 What This Project Does

An AI-powered stock portfolio optimizer that:

1. Collects user preferences (sectors, risk tolerance, market cap, exclusions, indicator preferences)
2. Runs a Variational LSTM model on 4 years of market data
3. Optimizes portfolio weights using SLSQP
4. Backtests the strategy against the S&P 500
5. Presents results through an interactive dashboard

### 1.2 Architecture

```
┌─────────────┐     HTTP      ┌─────────────┐    SQL/async    ┌────────────┐
│   Next.js   │ ◄───────────► │   FastAPI    │ ◄────────────► │ PostgreSQL │
│  Frontend   │   REST API    │   Backend    │                │  Database  │
│  (port 3000)│               │  (port 8000) │                │ (port 5432)│
└─────────────┘               └──────┬───────┘                └────────────┘
                                     │
                              ┌──────┴───────┐    cache      ┌────────────┐
                              │  ML Engine   │ ◄───────────► │   Redis    │
                              │ (TensorFlow) │               │ (port 6379)│
                              └──────────────┘               └────────────┘
```

**Data flow**: User → Frontend → Backend API → ML Pipeline (data fetch → features → LSTM → optimize with user preferences [sectors, market_cap_buckets, risk_tolerance, indicator_preferences] → backtest) → Database → Frontend Dashboard

### 1.3 Tech Stack


| Layer        | Technology                 | Version |
| ------------ | -------------------------- | ------- |
| Frontend     | Next.js (React)            | 15.x    |
| Styling      | Tailwind CSS               | 4.x     |
| Charts       | Recharts                   | 2.x     |
| Animations   | Framer Motion              | 11.x    |
| Backend API  | FastAPI                    | 0.115.x |
| Server       | Uvicorn                    | 0.34.x  |
| ORM          | SQLAlchemy (async)         | 2.0.x   |
| Database     | PostgreSQL                 | 16      |
| Cache        | Redis                      | 7       |
| ML Framework | TensorFlow                 | 2.16.x  |
| Data Source  | PostgreSQL `price_series` (ingested via yfinance adjusted bars) | --      |
| Auth         | JWT (python-jose) + bcrypt | --      |
| Containers   | Docker Compose             | --      |


### 1.4 Complete File Map

```
Production/
├── docker-compose.yml          # Orchestrates all 4 services
├── .env.example                # Environment variable template
├── .gitignore                  # Git ignore rules
├── README.md                   # Quick-start instructions
├── PLAN.md                     # Living architectural plan
├── ONBOARDING.md               # This file
├── model_artifacts/            # Saved model weights (gitignored)
│
├── backend/
│   ├── Dockerfile              # Python 3.11-slim image for backend
│   ├── requirements.txt        # Python dependencies
│   └── app/
│       ├── __init__.py
│       ├── main.py             # FastAPI app, CORS, startup (table creation + seeding)
│       ├── config.py           # Pydantic settings (DB URL, JWT secret, etc.)
│       ├── database.py         # SQLAlchemy async + sync session factories
│       ├── seed.py             # Seeds stock_metadata table with 12 tickers
│       │
│       ├── models/             # SQLAlchemy ORM models (7 tables)
│       │   ├── __init__.py     # Exports all models
│       │   ├── user.py         # User, UserPreference
│       │   ├── stock.py        # StockMetadata
│       │   ├── recommendation.py # Recommendation, BacktestResult, ExplanationSnapshot
│       │   └── model_run.py    # ModelRun (training run metadata)
│       │
│       ├── schemas/            # Pydantic request/response schemas
│       │   ├── __init__.py     # Exports all schemas
│       │   ├── auth.py         # UserCreate, UserLogin, UserResponse, TokenResponse
│       │   ├── preferences.py  # PreferencesCreate, PreferencesResponse
│       │   ├── recommendation.py # RecommendationRequest/Response/Detail
│       │   └── stock.py        # StockMetadataResponse
│       │
│       ├── api/                # FastAPI route handlers (9 endpoints)
│       │   ├── __init__.py
│       │   ├── deps.py         # get_current_user JWT dependency
│       │   ├── auth.py         # POST /register, POST /login
│       │   ├── preferences.py  # POST /preferences, GET /preferences/latest
│       │   ├── recommendations.py # POST /generate, GET /latest, GET /{id}
│       │   └── stocks.py       # GET /stocks/metadata
│       │
│       ├── services/           # Business logic layer
│       │   ├── __init__.py
│       │   ├── auth_service.py # Password hashing (bcrypt), JWT creation
│       │   ├── recommendation_service.py # Loads latest model_run, serves recommendation, persists results
│       │   ├── price_data_service.py # yfinance -> ensure stock_metadata -> upsert price_series
│       │   └── model_training_service.py # Train model, save artifact, insert model_runs row
│       │
│       └── ml/                 # Machine learning engine
│           ├── __init__.py
│           ├── config.py       # Hyperparameters, ticker universe, sector map
│           ├── data_loader.py  # DB-backed fetch from price_series, 7 features, tensor creation
│           ├── variational_lstm.py # Variational LSTM model (TensorFlow/Keras)
│           ├── portfolio_optimizer.py # SLSQP optimization
│           ├── backtest_engine.py # Walk-forward backtest (train mode + serve/load mode)
│           ├── explanation_generator.py # Plain-English stock explanations
│           └── pipeline.py     # Orchestrates train-and-save and serve-with-model workflows
│
└── frontend/
    ├── Dockerfile              # Multi-stage Node 20 build
    ├── package.json            # npm dependencies
    ├── tsconfig.json           # TypeScript config
    ├── next.config.mjs         # Next.js config (standalone output)
    ├── postcss.config.mjs      # Tailwind PostCSS
    ├── .env.local              # NEXT_PUBLIC_API_URL=http://localhost:8000
    └── src/
        ├── app/
        │   ├── layout.tsx      # Root layout (HTML, body, font)
        │   ├── globals.css     # Tailwind CSS imports
        │   ├── page.tsx        # Landing page (hero + auth forms)
        │   ├── preferences/
        │   │   └── page.tsx    # 5-step preferences wizard (sectors from API, market cap step)
        │   └── dashboard/
        │       └── page.tsx    # Recommendation dashboard
        ├── lib/
        │   ├── api.ts          # API client (fetch wrapper with JWT)
        │   └── types.ts        # TypeScript interfaces
        └── components/
            └── dashboard/
                ├── SummaryCard.tsx      # Metrics overview (5 cards)
                ├── AllocationChart.tsx  # Pie chart (Recharts)
                ├── PerformanceChart.tsx # Line chart (portfolio vs S&P 500)
                └── ExplanationCard.tsx  # Per-stock explanation with expandable metrics
```

---

## 2. Quick Start

### 2.1 Prerequisites

- Docker Desktop (with at least 4 GB memory allocated)
- Git (optional, for version control)

### 2.2 Environment Setup

```bash
cd Production/

# The .env.example is already configured for Docker Compose defaults.
# For production, copy and customize:
cp .env.example .env
# Edit .env to set a real JWT_SECRET_KEY
```

### 2.3 Start Everything

```bash
# Build and start all 4 services
docker compose up -d --build

# Check everything is running
docker compose ps

Expected output: 4 services (postgres, redis, backend, frontend) all "Up".
```

### 2.4 Access the App


| Service            | URL                                                                  |
| ------------------ | -------------------------------------------------------------------- |
| Frontend           | [http://localhost:3000](http://localhost:3000)                       |
| Backend API        | [http://localhost:8000](http://localhost:8000)                       |
| API Docs (Swagger) | [http://localhost:8000/docs](http://localhost:8000/docs)             |
| Health Check       | [http://localhost:8000/api/health](http://localhost:8000/api/health) |
| Test Account       | Email: `test@example.com`  Password: `testpass123`                   |

### 2.5 Stop / Restart

```bash
# Stop all services (preserves data)
docker compose down

# Stop and DELETE all data (fresh start)
docker compose down -v

# Restart just the backend (after code changes)
docker compose up -d --build backend

# Restart just the frontend
docker compose up -d --build frontend

# View logs for a specific service
docker compose logs backend --tail 50 -f
docker compose logs frontend --tail 50 -f
```

### 2.6 Quick Verification

```bash
# Health check
curl http://localhost:8000/api/health
# Expected: {"status":"healthy"}

# Stock metadata
curl http://localhost:8000/api/stocks/metadata
# Expected: JSON array with 12 tickers
```

---

## 3. Backend Deep Dive

### 3.1 API Endpoint Reference

#### Public Endpoints (no auth required)

**Health Check**

```bash
GET /api/health
# Response: {"status": "healthy"}
```

**Stock Metadata**

```bash
GET /api/stocks/metadata
# Response: [{"ticker":"AAPL","name":"Apple Inc.","sector":"Technology",...}, ...]
```

**Distinct Sectors** (for preferences UI)

```bash
GET /api/stocks/sectors
# Response: ["Communication Services", "Energy", "ETF", "Financials", ...]
```

#### Auth Endpoints

**Register**

```bash
POST /api/auth/register
Content-Type: application/json

{"email": "user@example.com", "password": "securepassword"}

# 201: {"id": "uuid", "email": "user@example.com", "created_at": "..."}
# 400: {"detail": "Email already registered"}
# 422: Validation error (bad email format, missing fields)
```

**Login**

```bash
POST /api/auth/login
Content-Type: application/json

{"email": "user@example.com", "password": "securepassword"}

# 200: {"access_token": "eyJ...", "token_type": "bearer"}
# 401: {"detail": "Invalid email or password"}
```

#### Authenticated Endpoints (require `Authorization: Bearer <token>`)

**Save Preferences**

```bash
POST /api/preferences
Authorization: Bearer <token>
Content-Type: application/json

{
  "sectors": ["Technology", "Energy"],
  "risk_tolerance": "moderate",        # conservative | moderate | aggressive
  "excluded_tickers": ["TSLA"],
  "indicator_preferences": {"momentum": true},
  "market_cap_buckets": ["large", "mid"]   # optional: small, mid, large; empty = no filter
}

# 200: Full preferences object
```

**Get Latest Preferences**

```bash
GET /api/preferences/latest
Authorization: Bearer <token>

# 200: Preferences object
# 404: No preferences saved yet
```

**Generate Recommendation** (triggers full ML pipeline, ~60s)

```bash
POST /api/recommendations/generate
Authorization: Bearer <token>
Content-Type: application/json

{
  "sectors": ["Technology", "Energy"],
  "risk_tolerance": "moderate",
  "excluded_tickers": [],
  "indicator_preferences": { "momentum": true, "low_volatility": false, "value": true },
  "market_cap_buckets": ["large"]
}

# 200: Full recommendation with ticker_weights, backtest, explanations
# 500: Pipeline failure (check backend logs)
```

**Get Latest Recommendation**

```bash
GET /api/recommendations/latest
Authorization: Bearer <token>

# 200: Full recommendation detail
# 404: No recommendations yet
```

**Get Recommendation by ID**

```bash
GET /api/recommendations/{uuid}
Authorization: Bearer <token>

# 200: Full recommendation detail
# 404: Not found
# 422: Invalid UUID format
```

### 3.2 Authentication Flow

```
Register → password hashed with bcrypt → stored in users table
                                              │
Login → verify bcrypt hash → generate JWT ────┘
                                 │
                    JWT contains: sub=user_id, exp=24h
                                 │
    Authenticated requests ──────┘
    Authorization: Bearer <jwt>
         │
    get_current_user dependency decodes JWT → loads User from DB
```

- JWT secret: set via `JWT_SECRET_KEY` in `.env`
- Token expiry: 24 hours (configurable in `config.py`)
- Password: bcrypt hashed, never stored in plain text

### 3.3 Service Layer

- `**auth_service.py**`: `hash_password()`, `verify_password()`, `create_access_token()`
- `**recommendation_service.py**`: Wraps ML execution in a `ThreadPoolExecutor`, loads latest `model_runs` artifact for serving, and persists `Recommendation`/`BacktestResult`/`ExplanationSnapshot` with `model_run_id`.
- `**model_training_service.py**`: Provides the train-and-record entrypoint (save model artifact + insert `model_runs`).

### 3.4 Key Config (`backend/app/config.py`)


| Setting         | Env Var                       | Default                                                               |
| --------------- | ----------------------------- | --------------------------------------------------------------------- |
| Database URL    | `DATABASE_URL`                | `postgresql+asyncpg://postgres:postgres@localhost:5432/portfolio_opt` |
| Redis URL       | `REDIS_URL`                   | `redis://localhost:6379/0`                                            |
| JWT Secret      | `JWT_SECRET_KEY`              | `change-me-in-production`                                             |
| Token Expiry    | `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` (24h)                                                          |
| Model Artifacts | `MODEL_ARTIFACTS_DIR`         | `model_artifacts`                                                     |


---

## 4. ML Engine

### 4.1 Pipeline Stages

```
1. Ticker Filtering    → Filter by user's sector and market-cap preferences (from stock_metadata), remove exclusions
        │
2. Data Fetch          → Read from PostgreSQL `price_series` (11+ tickers, 2022-01-01 to now)
        │                  Requires DB session; no yfinance fallback in loader
        │
3. Feature Engineering → 7 features per asset per day:
        │                  log_ret, volatility, trend_20, trend_50, beta, log_vol, smi
        │
4. Tensor Creation     → Shape: (N_days × N_assets × LOOKBACK × 7)
        │
5. Model Select + Walk-Forward:
        │  ├── Serve: load latest model artifact from `model_runs`
        │  ├── Fallback: train+record model run if none exists
        │  ├── Warmup: train on first 1/3 of data
        │  ├── Quarterly Retrain: re-fit model every quarter-end
        │  ├── Monthly Rebalance: re-optimize portfolio weights each month (optionally tilted by indicator_preferences: momentum, low_volatility, value)
        │  └── Daily P&L: track portfolio value vs S&P 500
        │
6. Explanation Generation → Plain-English reasoning for each stock pick
```

### 4.2 Hyperparameter Reference (`backend/app/ml/config.py`)


| Parameter          | Current Value | Effect                                          |
| ------------------ | ------------- | ----------------------------------------------- |
| `LOOKBACK`         | 66            | Trading days in each input sequence (~3 months) |
| `FORECAST_HORIZON` | 21            | Days ahead for return prediction (~1 month)     |
| `BATCH_SIZE`       | 1024          | Training batch size                             |
| `EPOCHS`           | 10            | Training epochs per retrain cycle               |
| `LEARNING_RATE`    | 0.001         | Adam optimizer learning rate                    |
| `HIDDEN_DIM`       | 64            | LSTM hidden layer size                          |
| `LATENT_DIM`       | 32            | Variational latent dimension                    |
| `ALPHA`            | 0.72          | Default risk-return tradeoff (moderate)         |
| `TILT_STRENGTH`    | 0.15          | Strength of indicator-preference tilt on returns (0 = no tilt) |
| `MAX_RECOMMENDED_STOCKS` | 8       | Hard cap: no recommendation has more than this many stocks    |
| `RISK_TO_MAX_STOCKS`    | see below | Max names by risk: conservative 8, moderate 6, aggressive 4   |
| `START_DATE`       | 2022-01-01    | Data start                                      |
| `END_DATE`         | 2026-03-01    | Data end                                        |


**Tuning tips:**

- Increase `HIDDEN_DIM`/`LATENT_DIM` for more expressive models (needs more memory)
- Increase `EPOCHS` for better convergence (slower training)
- Decrease `ALPHA` for more conservative portfolios, increase for aggressive
- The current values are optimized for Docker containers with 4GB memory

### 4.3 Ticker Universe (`backend/app/ml/config.py`)

```python
ALL_TICKERS = ["TSLA", "HOOD", "NVDA", "LEU", "AMZN", "BE", "GOOGL", "ORCL", "AAPL", "ASPI", "OKLO", "QQQ", "SPY"]
```

SPY is always included as the benchmark. QQQ is included in the investment universe. Sector and market-cap filtering use `stock_metadata`: the pipeline loads ticker → sector and ticker → market_cap_bucket from the DB. The preferences UI gets the list of sector choices from **GET /api/stocks/sectors** (distinct sectors from `stock_metadata`), so the options reflect what exists in the database.

### 4.4 Market cap filter (optional)

User preference **market_cap_buckets** (list: `"small"`, `"mid"`, `"large"`). When non-empty, the pipeline restricts the ticker universe to tickers whose `stock_metadata.market_cap_bucket` is in the list; when empty, no market-cap filter is applied. Buckets align with ingestion (e.g. large ≥$10B, mid ≥$2B, small &lt;$2B).

### 4.5 Indicator Preferences (optional)

User-selected indicators (Momentum, Low Volatility, Value Orientation) are passed as `indicator_preferences` from the API into the pipeline and applied in `BacktestEngine._rebalance`. At each rebalance, per-asset scores from existing features (trend_20, trend_50, volatility, smi) are z-scored and combined with the user’s choices; a return tilt of strength `TILT_STRENGTH` is added to model predictions before optimization, so allocations favor the selected signals. Keys: `momentum`, `low_volatility`, `value`.

### 4.6 Risk Tolerance → Alpha Mapping


| Risk Tolerance | Alpha Value | Behavior                                     |
| -------------- | ----------- | -------------------------------------------- |
| Conservative   | 0.3         | Prioritizes stability, lower drawdowns       |
| Moderate       | 0.72        | Balanced risk-return                         |
| Aggressive     | 1.2         | Maximizes returns, accepts higher volatility |

Risk tolerance also sets the **max number of stocks** in a recommendation (diversification): conservative → up to 8, moderate → up to 6, aggressive → up to 4 (`RISK_TO_MAX_STOCKS` in config). After the portfolio optimizer runs at each rebalance, weights are truncated to the top N by weight, the rest zeroed, and renormalized so the allocation respects both the global cap (8) and the risk-based N. Applied in `BacktestEngine._rebalance()`.

### 4.7 Model Objective Function

The optimizer maximizes: `Return / Max_Drawdown + alpha * Return`

This balances risk-adjusted returns (Calmar-like ratio) with raw return amplification.

### 4.8 Data Source and Refresh

The ML loader reads market data directly from PostgreSQL table `price_series` (DB-only path).

To refresh market data, run the ETL/backfill process (`backend/app/services/price_data_service.py`) that writes yfinance adjusted bars into `price_series`.

---

## 5. Frontend

### 5.1 Pages


| Route          | File                           | Description                                                                                             |
| -------------- | ------------------------------ | ------------------------------------------------------------------------------------------------------- |
| `/`            | `src/app/page.tsx`             | Landing page with hero section, 3 feature cards, and login/register forms                               |
| `/preferences` | `src/app/preferences/page.tsx` | 5-step wizard: sectors (from GET /api/stocks/sectors) → risk → market cap → exclusions → indicators     |
| `/dashboard`   | `src/app/dashboard/page.tsx`   | Recommendation display with charts and explanations. Supports `?id=<uuid>` for specific recommendations |
| `/history`     | `src/app/history/page.tsx`     | List of past recommendations (preference preview + model date); row click opens dashboard for that recommendation |


### 5.2 User Flow

```
Landing (/) → Register/Login → Preferences (/preferences) → Generate → Dashboard (/dashboard). From dashboard or preferences, **History** opens /history; **Start new search** returns to preferences. From /history, clicking a row opens Dashboard for that recommendation.
```

### 5.3 Dashboard Components


| Component          | File                                        | What It Renders                                                             |
| ------------------ | ------------------------------------------- | --------------------------------------------------------------------------- |
| `SummaryCard`      | `components/dashboard/SummaryCard.tsx`      | 5 metrics: stocks count, cumulative return, Sharpe, benchmark, max drawdown |
| `AllocationChart`  | `components/dashboard/AllocationChart.tsx`  | Pie chart of portfolio allocation                                           |
| `PerformanceChart` | `components/dashboard/PerformanceChart.tsx` | Line chart: portfolio value vs S&P 500 over time                            |
| `ExplanationCard`  | `components/dashboard/ExplanationCard.tsx`  | Per-stock card with reasoning text and expandable metrics table             |


### 5.4 API Client (`src/lib/api.ts`)

All backend communication goes through this module. It:

- Stores JWT token in `localStorage` under key `token`
- Automatically attaches `Authorization: Bearer <token>` to authenticated requests
- Provides typed methods: `register()`, `login()`, `savePreferences()`, `getLatestPreferences()`, `generateRecommendation()`, `getLatestRecommendation()`, `getRecommendation(id)`, `getRecommendationHistory()`, `getStockMetadata()`

### 5.5 Styling

- **Tailwind CSS** for all styling (no separate CSS files)
- **Color theme**: Emerald/green accents on dark slate backgrounds
- **Animations**: Framer Motion for page transitions and component entry

### 5.6 Frontend Development

```bash
# Rebuild frontend after changes
docker compose up -d --build frontend

# Or run locally (faster iteration):
cd frontend
npm install
npm run dev
# Runs on http://localhost:3000, proxies API to http://localhost:8000
```

---

## 6. Database

### 6.1 Schema Overview

```
┌──────────┐     1:N      ┌──────────────────┐
│  users   │ ──────────── │ user_preferences  │
│          │              └──────────────────┘
│          │     1:N      ┌──────────────────┐     1:1     ┌──────────────────┐
│          │ ──────────── │ recommendations   │ ────────── │ backtest_results  │
└──────────┘              │                  │             └──────────────────┘
                          │                  │     1:N     ┌──────────────────────┐
                          │                  │ ────────── │ explanation_snapshots │
                          └──────────────────┘             └──────────────────────┘

┌──────────────────┐     ┌──────────────┐
│  stock_metadata  │     │  model_runs  │
│  (seeded data)   │     │ (active: train provenance + artifact path) │
└──────────────────┘     └──────────────┘
```

### 6.2 Table Details

`**users**`


| Column        | Type      | Notes           |
| ------------- | --------- | --------------- |
| id            | UUID (PK) | Auto-generated  |
| email         | VARCHAR   | Unique, indexed |
| password_hash | VARCHAR   | bcrypt hash     |
| created_at    | TIMESTAMP | Auto-set        |
| updated_at    | TIMESTAMP | Auto-updated    |


`**user_preferences**`


| Column                | Type            | Notes                                           |
| --------------------- | --------------- | ----------------------------------------------- |
| id                    | UUID (PK)       | Auto-generated                                  |
| user_id               | UUID (FK→users) |                                                 |
| sectors               | JSONB           | e.g. `["Technology", "Energy"]`                 |
| risk_tolerance        | VARCHAR         | "conservative", "moderate", "aggressive"        |
| excluded_tickers      | JSONB           | e.g. `["TSLA"]`                                 |
| indicator_preferences | JSONB           | e.g. `{"momentum": true}`                       |
| market_cap_buckets    | JSONB           | e.g. `["small", "mid", "large"]`; empty = no filter |
| created_at            | TIMESTAMP       | Each save creates a new row (history preserved) |


`**stock_metadata**`


| Column            | Type         | Notes             |
| ----------------- | ------------ | ----------------- |
| ticker            | VARCHAR (PK) | e.g. "AAPL"       |
| name              | VARCHAR      | e.g. "Apple Inc." |
| sector            | VARCHAR      | e.g. "Technology" |
| market_cap_bucket | VARCHAR      | Nullable          |
| last_price_update | TIMESTAMP    | Nullable          |


`**recommendations**`


| Column               | Type                 | Notes                                                                 |
| -------------------- | -------------------- | --------------------------------------------------------------------- |
| id                   | UUID (PK)            | Auto-generated                                                        |
| user_id               | UUID (FK→users)      |                                                                       |
| model_run_id          | UUID (FK→model_runs) | Nullable                                                              |
| ticker_weights        | JSONB                | e.g. `{"AAPL": 0.25, "AMZN": 0.34}`                                  |
| generated_at          | TIMESTAMP            |                                                                       |
| preference_snapshot   | JSONB                | Optional; snapshot of preferences at generation (sectors, risk_tolerance, etc.) |

**Existing DBs:** If the table was created before this column existed, add it with: `ALTER TABLE recommendations ADD COLUMN IF NOT EXISTS preference_snapshot JSONB;`


`**backtest_results**`


| Column            | Type                      | Notes                           |
| ----------------- | ------------------------- | ------------------------------- |
| id                | UUID (PK)                 |                                 |
| recommendation_id | UUID (FK→recommendations) | Unique (1:1)                    |
| start_date        | DATE                      |                                 |
| end_date          | DATE                      |                                 |
| cumulative_return | FLOAT                     |                                 |
| annualized_return | FLOAT                     |                                 |
| sharpe_ratio      | FLOAT                     |                                 |
| max_drawdown      | FLOAT                     | Negative number                 |
| benchmark_return  | FLOAT                     | S&P 500 return over same period |
| daily_values      | JSONB                     | Array of `{date, value}`        |


`**explanation_snapshots**`


| Column            | Type                      | Notes                                                 |
| ----------------- | ------------------------- | ----------------------------------------------------- |
| id                | UUID (PK)                 |                                                       |
| recommendation_id | UUID (FK→recommendations) |                                                       |
| ticker            | VARCHAR                   |                                                       |
| allocation_pct    | FLOAT                     |                                                       |
| reasoning_text    | TEXT                      | Plain-English explanation                             |
| metrics           | JSONB                     | `{predicted_return, predicted_volatility, beta, ...}` |


`**model_runs**`


| Column              | Type      | Notes    |
| ------------------- | --------- | -------- |
| id                  | UUID (PK) |          |
| run_date            | TIMESTAMP |          |
| hyperparameters     | JSONB     |          |
| validation_sharpe   | FLOAT     | Nullable |
| training_loss       | FLOAT     | Nullable |
| model_artifact_path | VARCHAR   | Nullable |
| ticker_universe     | JSONB     |          |
| data_start_date     | DATE      |          |
| data_end_date       | DATE      |          |


### 6.3 Connecting to the Database Directly

```bash
# Via Docker (recommended)
docker compose exec postgres psql -U postgres -d portfolio_opt

# From host machine (if you have psql installed)
psql -h localhost -p 5432 -U postgres -d portfolio_opt
# Password: postgres
```

### 6.4 Useful SQL Queries

```sql
-- List all tables
\dt

-- Count users
SELECT COUNT(*) FROM users;

-- View all users (without password hashes)
SELECT id, email, created_at FROM users;

-- View latest preferences for each user
SELECT DISTINCT ON (user_id) *
FROM user_preferences
ORDER BY user_id, created_at DESC;

-- View all recommendations with backtest summary
SELECT r.id, r.user_id, r.generated_at, r.ticker_weights,
       b.cumulative_return, b.sharpe_ratio, b.max_drawdown
FROM recommendations r
JOIN backtest_results b ON b.recommendation_id = r.id
ORDER BY r.generated_at DESC;

-- View explanations for a specific recommendation
SELECT ticker, allocation_pct, reasoning_text
FROM explanation_snapshots
WHERE recommendation_id = '<uuid>'
ORDER BY allocation_pct DESC;

-- View stock metadata
SELECT * FROM stock_metadata ORDER BY sector, ticker;

-- Check database size
SELECT pg_size_pretty(pg_database_size('portfolio_opt'));

-- Check table sizes
SELECT relname AS table, pg_size_pretty(pg_total_relation_size(relid))
FROM pg_catalog.pg_statio_user_tables
ORDER BY pg_total_relation_size(relid) DESC;
```

### 6.5 Redis Inspection

```bash
# Connect to Redis CLI
docker compose exec redis redis-cli

# Inside Redis CLI:
KEYS *           # List all keys
DBSIZE           # Count keys
INFO memory      # Memory usage
FLUSHDB          # Clear all cache (safe to do)
```

### 6.6 Database Reset

```bash
# Full reset (drops all data, re-seeds stock metadata on restart)
docker compose down -v
docker compose up -d

# Just clear recommendations (keep users)
docker compose exec postgres psql -U postgres -d portfolio_opt -c "
  DELETE FROM explanation_snapshots;
  DELETE FROM backtest_results;
  DELETE FROM recommendations;
"
```

### 6.7 Future: Alembic Migrations

The current setup uses `Base.metadata.create_all()` on startup (auto-creates missing tables). For schema changes in production, switch to Alembic:

```bash
# Initialize Alembic (one-time)
cd backend
alembic init alembic

# After modifying a model, generate a migration
alembic revision --autogenerate -m "description of change"

# Apply migrations
alembic upgrade head
```

---

## 7. Health Checks & Troubleshooting

### 7.1 Diagnostic Commands

```bash
# Check all services
docker compose ps

# Check if backend is responsive
curl http://localhost:8000/api/health

# View backend logs (last 50 lines, follow)
docker compose logs backend --tail 50 -f

# View frontend logs
docker compose logs frontend --tail 50 -f

# View postgres logs
docker compose logs postgres --tail 20

# Check backend container resource usage
docker stats production-backend-1

# Run a quick end-to-end test
curl -sf http://localhost:8000/api/health && \
curl -sf http://localhost:8000/api/stocks/metadata | python3 -c "import sys,json; print(f'{len(json.load(sys.stdin))} stocks')" && \
curl -sf http://localhost:3000 > /dev/null && \
echo "All services OK"
```

### 7.2 Common Issues & Fixes

#### Backend exits with code 137 (OOM)

The ML pipeline is memory-intensive. The backend container has a 4GB limit.

**Fix**: Increase memory in `docker-compose.yml`:

```yaml
backend:
  deploy:
    resources:
      limits:
        memory: 6g
```

Or reduce model size in `backend/app/ml/config.py` (lower `HIDDEN_DIM`, `LATENT_DIM`, `EPOCHS`).

#### ML loader fails with missing DB data

**Symptoms**: Errors like `DB session required` or `No price data in DB for the requested range`.

**Fixes**:

1. Ensure the ML pipeline is calling `DataLoader.fetch_data(session=...)`.
2. Ensure requested tickers exist in `stock_metadata` first.
3. Verify `price_series` has rows for all requested tickers and dates.
4. Re-run your price ETL/backfill (e.g. `python3 -m app.services.price_data_service --full-backfill`) if data is incomplete.

#### Port already in use

```bash
# Find what's using the port
lsof -i :8000   # or :3000, :5432, :6379

# Kill the process
kill <PID>

# Or use different ports in docker-compose.yml
```

#### Frontend shows "Failed to fetch" errors

1. Check backend is running: `curl http://localhost:8000/api/health`
2. Check CORS: `backend/app/main.py` allows `http://localhost:3000`
3. Check `frontend/.env.local` has `NEXT_PUBLIC_API_URL=http://localhost:8000`

#### Database connection errors

```bash
# Check postgres is healthy
docker compose exec postgres pg_isready -U postgres

# Restart postgres
docker compose restart postgres

# Check connection from backend
docker compose exec backend python3 -c "
from sqlalchemy import create_engine
e = create_engine('postgresql://postgres:postgres@postgres:5432/portfolio_opt')
with e.connect() as c:
    print('Connected:', c.execute(text('SELECT 1')).scalar())
from sqlalchemy import text
"
```

#### ML pipeline takes too long

The pipeline runs quarterly retraining (~10 cycles) and should complete in ~60 seconds. If it takes much longer:

1. Check CPU usage: `docker stats production-backend-1`
2. Reduce training: Lower `EPOCHS` in `backend/app/ml/config.py`
3. Check data loading: Look for `DataLoader` DB read errors in backend logs

### 7.3 Log Locations


| Log                  | How to Access                                                          |
| -------------------- | ---------------------------------------------------------------------- |
| Backend (FastAPI)    | `docker compose logs backend`                                          |
| Frontend (Next.js)   | `docker compose logs frontend`                                         |
| PostgreSQL           | `docker compose logs postgres`                                         |
| Redis                | `docker compose logs redis`                                            |
| ML Pipeline progress | `docker compose logs backend` (look for `INFO:app.ml.backtest_engine`) |


---

## 8. Development Workflows

### 8.1 Adding a New Ticker

1. **Edit the ticker universe** in `backend/app/ml/config.py`:

```python
ALL_TICKERS = [..., "NEW_TICKER", ...]

TICKER_SECTOR_MAP = {
    ...,
    "NEW_TICKER": "SectorName",
}
```

2. **Add stock metadata** in `backend/app/seed.py`:

```python
StockMetadata(ticker="NEW_TICKER", name="Company Name", sector="SectorName")
```

3. **Rebuild and restart**:

```bash
# Reset the stock metadata seed 
docker compose exec postgres psql -U postgres -d portfolio_opt -c "DELETE FROM stock_metadata;"

# Re-run metadata + price ETL/backfill so the new ticker exists in stock_metadata and price_series
# (command depends on your local ETL script/service)
docker compose exec backend python3 -m app.services.price_data_service --full-backfill

# Rebuild backend
docker compose up -d --build backend
```

### 8.2 Modifying the Frontend UI

1. Edit files in `frontend/src/`
2. Rebuild: `docker compose up -d --build frontend`
3. For faster iteration, run locally:

```bash
cd frontend
npm install
npm run dev
```

**Key styling patterns**:

- All styles use Tailwind utility classes
- Color theme: `emerald-400/500/600` for accents, `slate-800/900/950` for backgrounds
- Animations: Framer Motion `motion.div` with `initial`, `animate`, `exit` props

### 8.3 Adding a New API Endpoint

1. **Create the route** in `backend/app/api/new_route.py`:

```python
from fastapi import APIRouter, Depends
from ..api.deps import get_current_user

router = APIRouter(prefix="/api/new", tags=["new"])

@router.get("/example")
async def example(user = Depends(get_current_user)):
    return {"message": "hello"}
```

1. **Register it** in `backend/app/main.py`:

```python
from .api.new_route import router as new_router
app.include_router(new_router)
```

1. **Add frontend API method** in `frontend/src/lib/api.ts`
2. **Rebuild**: `docker compose up -d --build backend`

### 8.4 Modifying the ML Model

The model lives in `backend/app/ml/variational_lstm.py`. To change architecture:

1. Edit the model class (add layers, change dimensions)
2. Update `config.py` if you add new hyperparameters
3. Delete cached data and model artifacts:

```bash
docker compose exec backend rm -rf /app/data/ /app/model_artifacts/*
```

1. Rebuild: `docker compose up -d --build backend`

**Current model architecture**:

```
Input → LSTM(64) → Dense(32) [z_mean] + Dense(32) [z_log_var]
    → Sampling (training only) / z_mean (inference) → Dense(64, relu) → Dense(1) [return_mean] + Dense(1) [return_log_var]
```

At **inference**, the model uses `z_mean` only (no sampling), so recommendations are deterministic for the same preferences and model run. **Loss function**: Negative log-likelihood + β × KL divergence + 0.5 × directional loss, weighted by recency.

### 8.5 Training the Model and Testing the Train/Serve Workflow (Docker)

Use this procedure to train the model (save artifact + insert `model_runs`) and verify that recommendations use the latest run and set `model_run_id`.

**1. Start services**

From the project root (where `docker-compose.yml` lives):

```bash
docker compose up -d postgres redis backend
```

Wait until the backend is up (e.g. `docker compose ps`).

**2. Ensure price data exists**

If `price_series` is empty, run ingestion once (full backfill):

```bash
docker compose exec backend python3 -m app.services.price_data_service --full-backfill
```

For incremental daily update only, omit `--full-backfill`.

**3. Train the model**

```bash
docker compose exec backend python3 -m app.services.model_training_service --risk-tolerance moderate
```

Optional risk profiles: `conservative`, `moderate` (default), `aggressive`.

The script prints a dict with `model_run_id`, `run_date`, `model_artifact_path`, `data_start_date`, `data_end_date`. Training can take 1–2 minutes.

**4. Verify training**

Check that a row was inserted and the artifact was written:

```bash
# Latest model_runs row
docker compose exec postgres psql -U postgres -d portfolio_opt -c "SELECT id, run_date, model_artifact_path, data_start_date, data_end_date FROM model_runs ORDER BY run_date DESC LIMIT 1;"

# Artifact on disk (host path; backend writes to /app/model_artifacts)
ls ./model_artifacts
```

You should see one row and a file like `run_<uuid>.weights.h5`.

**5. Test the recommendation (serve path)**

Get a JWT, then call the generate endpoint:

```bash
# Register (if needed)
curl -s -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"testpass123"}'

# Login
curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"testpass123"}'
```

Copy the `access_token` from the login response, then:

```bash
curl -s -X POST http://localhost:8000/api/recommendations/generate \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{}'
```

Replace `<YOUR_ACCESS_TOKEN>` with the token.

**6. Verify the recommendation used the latest model run**

```bash
docker compose exec postgres psql -U postgres -d portfolio_opt -c "SELECT id, model_run_id, generated_at FROM recommendations ORDER BY generated_at DESC LIMIT 1;"
```

`model_run_id` should match the `id` from step 4 (the run created in step 3).

**7. Optional: confirm serve path reuses the same run**

Generate another recommendation with the same token; the new row should have the same `model_run_id` (no new training).

---

**Quick reference — train only (no verification):**

```bash
docker compose exec backend python3 -m app.services.model_training_service --risk-tolerance moderate
```

This saves weights under `MODEL_ARTIFACTS_DIR` (default `./model_artifacts`) and inserts one row into `model_runs`.

### 8.6 Updating Dependencies

```bash
# Backend (Python)
# Edit backend/requirements.txt, then:
docker compose up -d --build backend

# Frontend (npm)
# Edit frontend/package.json, then:
docker compose up -d --build frontend
```

### 8.7 Deploying Updates

```bash
# Rebuild everything (after pulling new code)
docker compose up -d --build

# Rebuild specific service
docker compose up -d --build backend
docker compose up -d --build frontend

# Zero-downtime: rebuild then restart
docker compose build backend
docker compose up -d --no-deps backend
```

### 8.8 Backup & Restore Database

```bash
# Backup
docker compose exec postgres pg_dump -U postgres portfolio_opt > backup.sql

# Restore
docker compose exec -T postgres psql -U postgres -d portfolio_opt < backup.sql
```

