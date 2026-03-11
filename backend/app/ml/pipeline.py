"""
Top-level ML pipeline that the recommendation service calls.
Handles preference filtering, backtest execution, and explanation generation.
"""
import logging

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.stock import StockMetadata
from .config import ALL_TICKERS, ALPHA, START_DATE, END_DATE
from .backtest_engine import BacktestEngine
from .data_loader import DataLoader
from .explanation_generator import generate_explanations

logger = logging.getLogger(__name__)


class MLPipeline:
    """Stateless pipeline: each call to run() is self-contained."""

    def serve_with_model(
        self,
        db_session: Session,
        model_artifact_path: str,
        sectors: list[str] | None = None,
        risk_tolerance: str = "moderate",
        excluded_tickers: list[str] | None = None,
        indicator_preferences: dict | None = None,
        market_cap_buckets: list[str] | None = None,
    ) -> dict:
        """
        Full end-to-end: filter tickers -> backtest -> explain.
        Returns dict with keys: ticker_weights, backtest, explanations.
        """
        ticker_sector_map = self._load_ticker_sector_map(db_session)
        ticker_market_cap_map = self._load_ticker_market_cap_map(db_session)
        tickers = self._filter_tickers(
            sectors, excluded_tickers, market_cap_buckets,
            ticker_sector_map, ticker_market_cap_map,
        )
        alpha = self._alpha_for_risk(risk_tolerance)
        prefs = indicator_preferences or {}

        logger.info("Running pipeline with %d tickers, alpha=%.2f, indicator_prefs=%s", len(tickers), alpha, prefs)

        engine = BacktestEngine(
            tickers=tickers + ["SPY"],
            start_date=START_DATE,
            end_date=END_DATE,
            db_session=db_session,
            mode="serve",
            model_artifact_path=model_artifact_path,
            alpha=alpha,
            indicator_preferences=prefs,
            risk_tolerance=risk_tolerance,
        )
        final_weights, metrics, _ = engine.run()

        # For explanations we need features & predictions for the last date
        assets = [t for t in tickers if t != "SPY"]
        loader = DataLoader(tickers + ["SPY"], START_DATE, END_DATE)
        df = loader.fetch_data(session=db_session)
        feature_df = loader.calculate_features(df)
        X_all, _, _, valid_dates = loader.create_tensors(feature_df)

        X_last = X_all[-1]
        pred_mean, pred_log_var, _ = engine.model(X_last, training=False)
        pred_returns = pred_mean.numpy().flatten()
        pred_vols = np.exp(0.5 * pred_log_var.numpy().flatten())

        explanations = generate_explanations(assets, final_weights, feature_df, pred_returns, pred_vols)

        return {
            "ticker_weights": final_weights,
            "backtest": {
                "start_date": metrics.start_date,
                "end_date": metrics.end_date,
                "cumulative_return": metrics.cumulative_return,
                "annualized_return": metrics.annualized_return,
                "sharpe_ratio": metrics.sharpe_ratio,
                "max_drawdown": metrics.max_drawdown,
                "benchmark_return": metrics.benchmark_return,
                "daily_values": metrics.daily_values,
            },
            "explanations": explanations,
        }

    def train_and_save(
        self,
        db_session: Session,
        model_artifact_path: str,
        tickers: list[str] | None = None,
        risk_tolerance: str = "moderate",
    ) -> dict:
        train_tickers = list(tickers or [t for t in ALL_TICKERS if t != "SPY"])
        alpha = self._alpha_for_risk(risk_tolerance)
        engine = BacktestEngine(
            tickers=train_tickers + ["SPY"],
            start_date=START_DATE,
            end_date=END_DATE,
            db_session=db_session,
            mode="train",
            save_model_path=model_artifact_path,
            alpha=alpha,
            risk_tolerance=risk_tolerance,
        )
        final_weights, metrics, run_info = engine.run()
        return {
            "ticker_weights": final_weights,
            "backtest": {
                "start_date": metrics.start_date,
                "end_date": metrics.end_date,
                "cumulative_return": metrics.cumulative_return,
                "annualized_return": metrics.annualized_return,
                "sharpe_ratio": metrics.sharpe_ratio,
                "max_drawdown": metrics.max_drawdown,
                "benchmark_return": metrics.benchmark_return,
                "daily_values": metrics.daily_values,
            },
            "training_loss": run_info.get("training_loss"),
            "model_artifact_path": run_info.get("model_artifact_path"),
            "ticker_universe": train_tickers + ["SPY"],
            "alpha": alpha,
        }

    @staticmethod
    def _load_ticker_sector_map(session: Session) -> dict[str, str]:
        """Load ticker -> sector from stock_metadata (single source of truth)."""
        result = session.execute(select(StockMetadata.ticker, StockMetadata.sector))
        return {row[0]: row[1] for row in result.all()}

    @staticmethod
    def _load_ticker_market_cap_map(session: Session) -> dict[str, str | None]:
        """Load ticker -> market_cap_bucket from stock_metadata."""
        result = session.execute(select(StockMetadata.ticker, StockMetadata.market_cap_bucket))
        return {row[0]: row[1] for row in result.all()}

    @staticmethod
    def _filter_tickers(
        sectors: list[str] | None,
        excluded: list[str] | None,
        market_cap_buckets: list[str] | None,
        ticker_sector_map: dict[str, str],
        ticker_market_cap_map: dict[str, str | None],
    ) -> list[str]:
        base = [t for t in ALL_TICKERS if t != "SPY"]

        if sectors:
            sector_set = {s.lower() for s in sectors}
            base = [t for t in base if ticker_sector_map.get(t, "").lower() in sector_set]

        if market_cap_buckets:
            cap_set = {c.lower() for c in market_cap_buckets}
            base = [t for t in base if (ticker_market_cap_map.get(t) or "").lower() in cap_set]

        if excluded:
            ex_set = {e.upper() for e in excluded}
            base = [t for t in base if t not in ex_set]

        if not base:
            base = [t for t in ALL_TICKERS if t != "SPY"]
            logger.warning("Ticker filter produced empty set; falling back to full universe.")

        return base

    @staticmethod
    def _alpha_for_risk(risk_tolerance: str) -> float:
        mapping = {
            "conservative": 0.3,
            "moderate": 0.72,
            "aggressive": 1.2,
        }
        return mapping.get(risk_tolerance.lower(), 0.72)
