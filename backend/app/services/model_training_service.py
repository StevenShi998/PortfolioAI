"""
Training job entrypoint for periodic model training and model_runs recording.
"""
from __future__ import annotations

import argparse
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_sync_db_session
from ..ml.config import (
    ALL_TICKERS,
    ALPHA,
    BATCH_SIZE,
    EPOCHS,
    FORECAST_HORIZON,
    HIDDEN_DIM,
    LATENT_DIM,
    LEARNING_RATE,
    LOOKBACK,
)
from ..ml.pipeline import MLPipeline
from ..models.model_run import ModelRun

logger = logging.getLogger(__name__)


def _build_artifact_path(run_id: uuid.UUID) -> str:
    settings = get_settings()
    artifacts_dir = Path(settings.model_artifacts_dir)
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    return str(artifacts_dir / f"run_{run_id}.weights.h5")


def train_and_record_model_run(
    session: Session,
    risk_tolerance: str = "moderate",
) -> ModelRun:
    pipeline = MLPipeline()
    run_id = uuid.uuid4()
    artifact_path = _build_artifact_path(run_id)

    result = pipeline.train_and_save(
        db_session=session,
        model_artifact_path=artifact_path,
        tickers=[t for t in ALL_TICKERS if t != "SPY"],
        risk_tolerance=risk_tolerance,
    )

    model_run = ModelRun(
        id=run_id,
        run_date=datetime.now(timezone.utc),
        hyperparameters={
            "LOOKBACK": LOOKBACK,
            "FORECAST_HORIZON": FORECAST_HORIZON,
            "BATCH_SIZE": BATCH_SIZE,
            "EPOCHS": EPOCHS,
            "LEARNING_RATE": LEARNING_RATE,
            "HIDDEN_DIM": HIDDEN_DIM,
            "LATENT_DIM": LATENT_DIM,
            "ALPHA": ALPHA,
            "risk_tolerance": risk_tolerance,
        },
        validation_sharpe=result["backtest"]["sharpe_ratio"],
        training_loss=result.get("training_loss"),
        model_artifact_path=str(result["model_artifact_path"]),
        ticker_universe={"tickers": result["ticker_universe"]},
        data_start_date=result["backtest"]["start_date"],
        data_end_date=result["backtest"]["end_date"],
    )
    session.add(model_run)
    session.commit()
    session.refresh(model_run)
    logger.info("Trained and recorded model run %s -> %s", model_run.id, model_run.model_artifact_path)
    return model_run


def _parse_cli_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train model and insert a row into model_runs.")
    parser.add_argument(
        "--risk-tolerance",
        type=str,
        default="moderate",
        choices=["conservative", "moderate", "aggressive"],
        help="Risk profile used to derive alpha at training time.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_cli_args()
    print("Training model (loading data & running walk-forward backtest)...", flush=True)
    with get_sync_db_session() as session:
        model_run = train_and_record_model_run(session=session, risk_tolerance=args.risk_tolerance)
    print("Training complete.", flush=True)
    print(
        {
            "model_run_id": str(model_run.id),
            "run_date": model_run.run_date.isoformat(),
            "model_artifact_path": model_run.model_artifact_path,
            "data_start_date": model_run.data_start_date.isoformat(),
            "data_end_date": model_run.data_end_date.isoformat(),
        }
    )


if __name__ == "__main__":
    main()
