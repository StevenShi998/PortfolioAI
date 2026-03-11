"""
Orchestrates the full recommendation pipeline:
  preferences -> ticker filtering -> ML prediction -> optimization -> backtest -> explanation
"""
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_sync_db_session
from ..models.model_run import ModelRun
from ..models.recommendation import Recommendation, BacktestResult, ExplanationSnapshot
from ..ml.pipeline import MLPipeline
from .model_training_service import train_and_record_model_run

logger = logging.getLogger(__name__)

_pipeline: MLPipeline | None = None
_executor = ThreadPoolExecutor(max_workers=1)


def get_pipeline() -> MLPipeline:
    global _pipeline
    if _pipeline is None: #initialize
        _pipeline = MLPipeline()
    return _pipeline


def _run_pipeline_with_sync_session(
    pipeline: MLPipeline,
    model_artifact_path: str,
    sectors: list[str],
    risk_tolerance: str,
    excluded_tickers: list[str],
    indicator_preferences: dict,
    market_cap_buckets: list[str],
) -> dict:
    with get_sync_db_session() as sync_db:
        return pipeline.serve_with_model(
            db_session=sync_db,
            model_artifact_path=model_artifact_path,
            sectors=sectors,
            risk_tolerance=risk_tolerance,
            excluded_tickers=excluded_tickers,
            indicator_preferences=indicator_preferences,
            market_cap_buckets=market_cap_buckets,
        )


def _train_model_run_with_sync_session(risk_tolerance: str) -> dict[str, str]:
    with get_sync_db_session() as sync_db:
        model_run = train_and_record_model_run(session=sync_db, risk_tolerance=risk_tolerance)
        return {
            "model_run_id": str(model_run.id),
            "model_artifact_path": str(model_run.model_artifact_path),
        }


async def run_recommendation_pipeline(
    db: AsyncSession,
    user_id: UUID,
    sectors: list[str],
    risk_tolerance: str,
    excluded_tickers: list[str],
    indicator_preferences: dict | None = None,
    market_cap_buckets: list[str] | None = None,
) -> tuple[Recommendation, BacktestResult, list[ExplanationSnapshot]]:
    """
    Run the full ML pipeline in a thread pool and persist results.
    Returns the Recommendation, BacktestResult, and list of ExplanationSnapshots.
    """
    pipeline = get_pipeline()
    latest_model_result = await db.execute(select(ModelRun).order_by(ModelRun.run_date.desc()).limit(1))
    latest_model_run = latest_model_result.scalar_one_or_none()

    model_run_id: UUID | None = latest_model_run.id if latest_model_run else None
    model_artifact_path = latest_model_run.model_artifact_path if latest_model_run else None

    loop = asyncio.get_running_loop()
    if not model_run_id or not model_artifact_path:
        logger.warning("No model_runs found. Training a model run on-demand before serving recommendation.")
        trained = await loop.run_in_executor(
            _executor,
            lambda: _train_model_run_with_sync_session(risk_tolerance=risk_tolerance),
        )
        model_run_id = UUID(trained["model_run_id"])
        model_artifact_path = trained["model_artifact_path"]

    prefs = indicator_preferences if indicator_preferences is not None else {}
    caps = market_cap_buckets if market_cap_buckets is not None else []
    preference_snapshot = {
        "sectors": sectors,
        "risk_tolerance": risk_tolerance,
        "excluded_tickers": excluded_tickers,
        "indicator_preferences": prefs,
        "market_cap_buckets": caps,
    }
    result = await loop.run_in_executor(
        _executor,
        lambda: _run_pipeline_with_sync_session(
            pipeline=pipeline,
            model_artifact_path=model_artifact_path,
            sectors=sectors,
            risk_tolerance=risk_tolerance,
            excluded_tickers=excluded_tickers,
            indicator_preferences=prefs,
            market_cap_buckets=caps,
        ),
    )

    rec = Recommendation(
        user_id=user_id,
        model_run_id=model_run_id,
        ticker_weights=result["ticker_weights"],
        preference_snapshot=preference_snapshot,
        generated_at=datetime.now(timezone.utc),
    )
    db.add(rec)
    await db.flush()

    bt = BacktestResult(
        recommendation_id=rec.id,
        start_date=result["backtest"]["start_date"],
        end_date=result["backtest"]["end_date"],
        cumulative_return=result["backtest"]["cumulative_return"],
        annualized_return=result["backtest"]["annualized_return"],
        sharpe_ratio=result["backtest"]["sharpe_ratio"],
        max_drawdown=result["backtest"]["max_drawdown"],
        benchmark_return=result["backtest"]["benchmark_return"],
        daily_values=result["backtest"]["daily_values"],
    )
    db.add(bt)

    explanations = []
    for exp in result["explanations"]:
        snap = ExplanationSnapshot(
            recommendation_id=rec.id,
            ticker=exp["ticker"],
            allocation_pct=exp["allocation_pct"],
            reasoning_text=exp["reasoning_text"],
            metrics=exp["metrics"],
        )
        db.add(snap)
        explanations.append(snap)

    await db.commit()
    await db.refresh(rec)
    await db.refresh(bt)
    for s in explanations:
        await db.refresh(s)

    return rec, bt, explanations
