"""
ORM: Python classes that map to Postgres tables. 
Used by /api and /services to write (create/update) and read (query) the database
"""
from .user import User, UserPreference
from .recommendation import Recommendation, BacktestResult, ExplanationSnapshot
from .stock import StockMetadata
from .model_run import ModelRun
from .price_series import PriceSeries

__all__ = [
    "User", "UserPreference",
    "Recommendation", "BacktestResult", "ExplanationSnapshot",
    "StockMetadata", "ModelRun", "PriceSeries",
]
