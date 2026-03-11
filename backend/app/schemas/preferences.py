from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class PreferencesCreate(BaseModel):
    sectors: list[str] = []
    risk_tolerance: str = "moderate"
    excluded_tickers: list[str] = []
    indicator_preferences: dict = {}
    market_cap_buckets: list[str] = []


class PreferencesResponse(BaseModel):
    id: UUID
    user_id: UUID
    sectors: list[str]
    risk_tolerance: str
    excluded_tickers: list[str]
    indicator_preferences: dict
    market_cap_buckets: list[str]
    created_at: datetime

    model_config = {"from_attributes": True}
