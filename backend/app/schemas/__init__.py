"""
Pydantic schemas for API request/response validation and serialization.
Used by the API layer to validate incoming bodies and shape outgoing JSON.
"""

from .auth import UserCreate, UserLogin, UserResponse, TokenResponse
from .preferences import PreferencesCreate, PreferencesResponse
from .recommendation import (
    RecommendationRequest,
    RecommendationResponse,
    BacktestResultResponse,
    ExplanationResponse,
    RecommendationDetailResponse,
)
from .stock import StockMetadataResponse

__all__ = [
    "UserCreate", "UserLogin", "UserResponse", "TokenResponse",
    "PreferencesCreate", "PreferencesResponse",
    "RecommendationRequest", "RecommendationResponse",
    "BacktestResultResponse", "ExplanationResponse", "RecommendationDetailResponse",
    "StockMetadataResponse",
]
