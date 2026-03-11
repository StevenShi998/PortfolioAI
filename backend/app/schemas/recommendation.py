from pydantic import BaseModel
from uuid import UUID
from datetime import datetime, date


class RecommendationRequest(BaseModel):
    """User can optionally override preferences at generation time."""
    sectors: list[str] | None = None
    risk_tolerance: str | None = None
    excluded_tickers: list[str] | None = None
    indicator_preferences: dict | None = None
    market_cap_buckets: list[str] | None = None


class BacktestResultResponse(BaseModel):
    start_date: date
    end_date: date
    cumulative_return: float
    annualized_return: float
    sharpe_ratio: float
    max_drawdown: float
    benchmark_return: float
    daily_values: list[dict]

    model_config = {"from_attributes": True}


class ExplanationResponse(BaseModel):
    ticker: str
    allocation_pct: float
    reasoning_text: str
    metrics: dict

    model_config = {"from_attributes": True}


class RecommendationResponse(BaseModel):
    id: UUID
    ticker_weights: dict[str, float]
    generated_at: datetime

    model_config = {"from_attributes": True}


class RecommendationDetailResponse(BaseModel):
    id: UUID
    ticker_weights: dict[str, float]
    generated_at: datetime
    backtest: BacktestResultResponse | None = None
    explanations: list[ExplanationResponse] = []

    model_config = {"from_attributes": True}


class RecommendationHistoryItemResponse(BaseModel):
    id: UUID
    generated_at: datetime
    model_run_id: UUID | None = None
    model_run_date: datetime | None = None
    preference_snapshot: dict = {}


class RecommendationHistoryResponse(BaseModel):
    items: list[RecommendationHistoryItemResponse]
