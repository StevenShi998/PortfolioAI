"""
Walk-forward backtest engine.
Ported from Previous/Project/src/backtest_engine.py with the sample_ages bug fixed.
"""
import logging
from pathlib import Path
from dataclasses import dataclass, field
from datetime import date

import os

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"
import tensorflow as tf  # noqa: E402

tf.config.threading.set_intra_op_parallelism_threads(2)
tf.config.threading.set_inter_op_parallelism_threads(2)

from .config import (  # noqa: E402
    LOOKBACK,
    BATCH_SIZE,
    EPOCHS,
    LEARNING_RATE,
    HIDDEN_DIM,
    LATENT_DIM,
    ALPHA,
    TILT_STRENGTH,
    MAX_RECOMMENDED_STOCKS,
    RISK_TO_MAX_STOCKS,
)
from .data_loader import DataLoader  # noqa: E402
from .variational_lstm import VariationalLSTM  # noqa: E402
from .portfolio_optimizer import PortfolioOptimizer  # noqa: E402

logger = logging.getLogger(__name__)


class EpochProgressCallback(tf.keras.callbacks.Callback):
    """Print one line per epoch so the user sees training progress."""

    def __init__(self, stage: str = "Training", total_epochs: int = EPOCHS):
        super().__init__()
        self.stage = stage
        self.total_epochs = total_epochs

    def on_epoch_end(self, epoch: int, logs: dict | None = None):
        logs = logs or {}
        loss = logs.get("loss")
        if isinstance(loss, (int, float)):
            print(f"  {self.stage} — Epoch {epoch + 1}/{self.total_epochs} — loss: {loss:.6f}", flush=True)
        else:
            print(f"  {self.stage} — Epoch {epoch + 1}/{self.total_epochs}", flush=True)


@dataclass
class BacktestMetrics:
    cumulative_return: float = 0.0
    annualized_return: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    benchmark_return: float = 0.0
    daily_values: list[dict] = field(default_factory=list)
    start_date: date | None = None
    end_date: date | None = None


def _zscore(x: np.ndarray) -> np.ndarray:
    """Z-score across elements; if std is 0 return zeros."""
    mean, std = x.mean(), x.std()
    if std is None or std == 0:
        return np.zeros_like(x, dtype=np.float64)
    return (x - mean) / std


def _truncate_weights_to_max_stocks(
    weights: np.ndarray,
    max_n: int,
) -> np.ndarray:
    """
    Keep only the top max_n positions by weight; zero the rest and renormalize.
    Returns a new array of same shape, summing to 1.
    """
    max_n = min(max_n, len(weights))
    if max_n <= 0 or weights.size == 0:
        return weights
    if np.all(weights <= 0):
        return weights
    top_idx = np.argsort(weights)[::-1][:max_n]
    out = np.zeros_like(weights, dtype=weights.dtype)
    out[top_idx] = weights[top_idx]
    total = out.sum()
    if total > 0:
        out = out / total
    return out


class BacktestEngine:
    def __init__(
        self,
        tickers: list[str],
        start_date: str,
        end_date: str,
        db_session: Session,
        mode: str = "train",
        model_artifact_path: str | None = None,
        save_model_path: str | None = None,
        initial_capital: float = 100_000.0,
        alpha: float = ALPHA,
        indicator_preferences: dict | None = None,
        tilt_strength: float = TILT_STRENGTH,
        risk_tolerance: str = "moderate",
    ):
        self.tickers = tickers
        self.start_date = start_date
        self.end_date = end_date
        self.db_session = db_session
        self.mode = mode
        self.model_artifact_path = model_artifact_path
        self.save_model_path = save_model_path
        self.initial_capital = initial_capital
        self.alpha = alpha
        self.indicator_preferences = indicator_preferences or {}
        self.tilt_strength = tilt_strength
        self.risk_tolerance = (risk_tolerance or "moderate").lower()

        self.loader = DataLoader(tickers, start_date, end_date)
        self.optimizer = PortfolioOptimizer(alpha=alpha)
        self.model: VariationalLSTM | None = None
        self.training_loss: float | None = None

    def run(self) -> tuple[dict[str, float], BacktestMetrics, dict[str, float | str | None]]:
        """
        Execute the full walk-forward backtest.
        Returns (final_weights, metrics).
        """
        df = self.loader.fetch_data(session=self.db_session)
        feature_df = self.loader.calculate_features(df)
        X_all, y_all, assets, valid_dates = self.loader.create_tensors(feature_df)

        if X_all.size == 0 or X_all.ndim < 4:
            raise RuntimeError(
                f"Insufficient data to run backtest. Tensor shape: {X_all.shape}. "
                "Check that tickers are valid and the date range has enough trading days."
            )

        n_features = X_all.shape[3]
        warmup_days = min(126, len(valid_dates) // 3)
        if warmup_days < 10:
            raise RuntimeError(
                f"Only {len(valid_dates)} valid dates available (need at least 30 for warmup). "
                "Try a wider date range or more tickers."
            )

        logger.info("Tensor shape: %s, warmup=%d, total_days=%d", X_all.shape, warmup_days, len(valid_dates))

        self.model = VariationalLSTM(input_dim=n_features, hidden_dim=HIDDEN_DIM, latent_dim=LATENT_DIM)
        self.model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=LEARNING_RATE))

        # Build the model first, then either train or load pretrained weights.
        _ = self.model(tf.zeros((1, LOOKBACK, n_features), dtype=tf.float32), training=False)
        if self.mode == "serve":
            if not self.model_artifact_path:
                raise ValueError("model_artifact_path is required in serve mode")
            self.model.load_weights(self.model_artifact_path)
            logger.info("Loaded model weights from %s", self.model_artifact_path)
        else:
            X_warmup = X_all[:warmup_days].reshape(-1, LOOKBACK, n_features)
            y_warmup = y_all[:warmup_days].flatten()
            logger.info("Warmup training on %d samples, %d epochs...", len(y_warmup), EPOCHS)
            print("Warmup training...", flush=True)
            warmup_history = self.model.fit(
                X_warmup,
                y_warmup,
                epochs=EPOCHS,
                batch_size=BATCH_SIZE,
                verbose=0,
                shuffle=True,
                callbacks=[EpochProgressCallback(stage="Warmup", total_epochs=EPOCHS)],
            )
            self.training_loss = float(warmup_history.history.get("loss", [None])[-1]) if warmup_history.history else None
            logger.info("Warmup training complete.")

        # --- initial weights via prediction on last warmup day ---
        current_weights = self._rebalance(X_all[warmup_days - 1], feature_df, valid_dates[warmup_days - 1], assets)

        current_capital = self.initial_capital
        portfolio_values: list[float] = []
        portfolio_dates: list[pd.Timestamp] = []
        retrain_count = 0

        for t in range(warmup_days, len(valid_dates)):
            current_date = valid_dates[t]

            # --- retrain quarterly (every 3 months) at quarter-end ---
            is_quarter_end = (t == len(valid_dates) - 1) or (
                t < len(valid_dates) - 1
                and valid_dates[t + 1].month != current_date.month
                and current_date.month in (3, 6, 9, 12)
            )
            if is_quarter_end and self.mode == "train":
                retrain_count += 1
                X_train = X_all[:t].reshape(-1, LOOKBACK, n_features)
                y_train = y_all[:t].flatten()

                n_days = t
                n_assets_count = len(assets)
                sample_ages = np.repeat(np.arange(n_days)[::-1], n_assets_count).astype(np.float32)

                train_ds = (
                    tf.data.Dataset.from_tensor_slices((X_train, y_train, sample_ages))
                    .shuffle(buffer_size=min(len(y_train), 10000))
                    .batch(BATCH_SIZE)
                    .prefetch(tf.data.AUTOTUNE)
                )
                logger.info("Retrain #%d at %s on %d samples...", retrain_count, current_date.date(), len(y_train))
                print(f"Retrain #{retrain_count} at {current_date.date()}...", flush=True)
                retrain_history = self.model.fit(
                    train_ds,
                    epochs=EPOCHS,
                    verbose=0,
                    callbacks=[EpochProgressCallback(stage=f"Retrain {retrain_count}", total_epochs=EPOCHS)],
                )
                if retrain_history.history and retrain_history.history.get("loss"):
                    self.training_loss = float(retrain_history.history["loss"][-1])

            # --- rebalance at month-start ---
            is_month_start = (t == warmup_days) or (valid_dates[t - 1].month != current_date.month)
            if is_month_start:
                current_weights = self._rebalance(X_all[t], feature_df, current_date, assets)

            # --- daily P&L ---
            asset_ret_cols = [f"{a}_log_ret" for a in assets]
            try:
                actual = feature_df.loc[current_date, asset_ret_cols].values.astype(float)
            except KeyError:
                actual = y_all[t]
            portfolio_ret = float(np.sum(current_weights * actual))
            current_capital *= np.exp(portfolio_ret)

            portfolio_values.append(current_capital)
            portfolio_dates.append(current_date)

        # --- compute benchmark ---
        spy_close = df["SPY"]["Close"]
        spy_aligned = spy_close.reindex(portfolio_dates, method="ffill")
        benchmark_return = float(spy_aligned.iloc[-1] / spy_aligned.iloc[0]) - 1.0 if len(spy_aligned) > 1 else 0.0

        # --- compute metrics ---
        values_series = pd.Series(portfolio_values, index=portfolio_dates)
        returns = values_series.pct_change().dropna()
        cumulative_return = float(values_series.iloc[-1] / values_series.iloc[0]) - 1.0
        n_years = max(len(returns) / 252, 1e-6)
        annualized_return = float((1 + cumulative_return) ** (1 / n_years) - 1)
        sharpe = float(returns.mean() / returns.std() * np.sqrt(252)) if returns.std() > 0 else 0.0

        cum_max = values_series.cummax()
        drawdown = (values_series - cum_max) / cum_max
        max_dd = float(drawdown.min())

        daily_values = [
            {"date": str(d.date()), "value": round(v / self.initial_capital, 6)}
            for d, v in zip(portfolio_dates, portfolio_values)
        ]

        final_weights = {a: round(float(w), 6) for a, w in zip(assets, current_weights) if w > 0.001}

        metrics = BacktestMetrics(
            cumulative_return=round(cumulative_return, 6),
            annualized_return=round(annualized_return, 6),
            sharpe_ratio=round(sharpe, 4),
            max_drawdown=round(max_dd, 6),
            benchmark_return=round(benchmark_return, 6),
            daily_values=daily_values,
            start_date=portfolio_dates[0].date() if portfolio_dates else None,
            end_date=portfolio_dates[-1].date() if portfolio_dates else None,
        )
        logger.info(
            "Backtest complete: cum_ret=%.2f%%, sharpe=%.2f, max_dd=%.2f%%, %d retrains",
            cumulative_return * 100, sharpe, max_dd * 100, retrain_count,
        )
        run_info: dict[str, float | str | None] = {
            "training_loss": self.training_loss,
            "model_artifact_path": self.model_artifact_path,
        }
        if self.mode == "train" and self.save_model_path:
            save_path = Path(self.save_model_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            self.model.save_weights(str(save_path))
            run_info["model_artifact_path"] = str(save_path)
            logger.info("Saved model weights to %s", save_path)
        return final_weights, metrics, run_info
    
    #indicater preference (value, mom, volatility)
    def _indicator_tilt(self, feature_df: pd.DataFrame, current_date: pd.Timestamp, assets: list[str]) -> np.ndarray:
        """Compute return tilt from indicator_preferences using feature_df at current_date. Returns shape (n_assets,)."""
        if not self.indicator_preferences or self.tilt_strength <= 0:
            return np.zeros(len(assets))

        try:
            row = feature_df.loc[current_date]
        except KeyError:
            return np.zeros(len(assets))

        momentum_scores = []
        low_vol_scores = []
        value_scores = []
        for a in assets:
            t20 = row.get(f"{a}_trend_20", np.nan)
            t50 = row.get(f"{a}_trend_50", np.nan)
            vol = row.get(f"{a}_volatility", np.nan)
            smi = row.get(f"{a}_smi", np.nan)
            if np.isnan(t20):
                t20 = 0.0
            if np.isnan(t50):
                t50 = 0.0
            if np.isnan(vol) or vol <= 0:
                vol = 1e-6
            if np.isnan(smi):
                smi = 0.0
            momentum_scores.append((float(t20) + float(t50) + float(smi)) / 3.0)
            low_vol_scores.append(1.0 / (1.0 + float(vol)))
            value_scores.append(-(float(t20) + float(t50)) / 2.0)

        momentum_arr = np.array(momentum_scores, dtype=np.float64)
        low_vol_arr = np.array(low_vol_scores, dtype=np.float64)
        value_arr = np.array(value_scores, dtype=np.float64)

        mom_z = _zscore(momentum_arr)
        lowvol_z = _zscore(low_vol_arr)
        value_z = _zscore(value_arr)

        prefs = self.indicator_preferences
        w_mom = 1.0 if prefs.get("momentum") else 0.0
        w_lowvol = 1.0 if prefs.get("low_volatility") else 0.0
        w_value = 1.0 if prefs.get("value_orientation") or prefs.get("value") else 0.0
        total = w_mom + w_lowvol + w_value
        if total <= 0:
            return np.zeros(len(assets))
        w_mom /= total
        w_lowvol /= total
        w_value /= total

        tilt = self.tilt_strength * (w_mom * mom_z + w_lowvol * lowvol_z + w_value * value_z)
        return tilt

    def _rebalance(
        self, X_t: np.ndarray, feature_df: pd.DataFrame, current_date: pd.Timestamp, assets: list[str]
    ) -> np.ndarray:
        pred_mean, pred_log_var, _ = self.model(X_t, training=False)
        pred_returns = pred_mean.numpy().flatten()
        pred_vols = np.exp(0.5 * pred_log_var.numpy().flatten())

        tilt = self._indicator_tilt(feature_df, current_date, assets)
        adjusted_returns = pred_returns + tilt.astype(pred_returns.dtype)

        date_loc = feature_df.index.get_loc(current_date)
        past_start = max(0, date_loc - 60)
        past_df = feature_df.iloc[past_start:date_loc]
        asset_ret_cols = [f"{a}_log_ret" for a in assets]
        hist_corr = past_df[asset_ret_cols].corr().values

        sigma_hat = self.optimizer.construct_covariance(pred_vols, hist_corr)
        weights = self.optimizer.optimize(adjusted_returns, sigma_hat, past_df[asset_ret_cols].values)
        max_stocks = min(
            MAX_RECOMMENDED_STOCKS,
            RISK_TO_MAX_STOCKS.get(self.risk_tolerance, RISK_TO_MAX_STOCKS["moderate"]),
        )
        weights = _truncate_weights_to_max_stocks(weights, max_stocks)
        return weights
