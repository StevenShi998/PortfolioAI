"""
Data loading and feature engineering.
Ported from Previous/Project/src/data_loader.py -- stripped GPU helpers to keep
the production backend CPU-only (TensorFlow handles its own GPU for the LSTM).
"""
import logging
from typing import Tuple

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import LOOKBACK, FORECAST_HORIZON, ALL_TICKERS, START_DATE, END_DATE
from ..models.price_series import PriceSeries

logger = logging.getLogger(__name__)


class DataLoader:
    def __init__(
        self,
        tickers: list[str] | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        data_dir: str = "data",
        forecast_horizon: int = FORECAST_HORIZON,
    ):
        self.tickers = tickers or list(ALL_TICKERS)
        if "SPY" not in self.tickers:
            self.tickers.append("SPY")
        self.start_date = start_date or START_DATE
        self.end_date = end_date or END_DATE
        self.lookback = LOOKBACK
        self.forecast_horizon = forecast_horizon
        self.data_dir = data_dir

    def fetch_data(self, session: Session) -> pd.DataFrame:
        return self.fetch_data_from_db(session=session)

    def fetch_data_from_db(
        self,
        session: Session,
        tickers: list[str] | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> pd.DataFrame:
        if session is None:
            logger.error("DataLoader requires a DB session for DB-backed data reads.")
            raise ValueError("DB session required")

        requested_tickers = tickers or self.tickers
        requested_start = pd.Timestamp(start_date or self.start_date).date()
        requested_end = pd.Timestamp(end_date or self.end_date).date()
        ohlcv_fields = ["Open", "High", "Low", "Close", "Volume"]

        stmt = (
            select(PriceSeries)
            .where(
                PriceSeries.ticker.in_(requested_tickers),
                PriceSeries.date >= requested_start,
                PriceSeries.date <= requested_end,
            )
            .order_by(PriceSeries.date, PriceSeries.ticker)
        )
        rows = session.execute(stmt).scalars().all()
        if not rows:
            logger.error(
                "No price data in DB for tickers=%s between %s and %s",
                requested_tickers,
                requested_start,
                requested_end,
            )
            raise ValueError("No price data in DB for the requested range")

        raw_df = pd.DataFrame(
            [
                {
                    "date": row.date,
                    "ticker": row.ticker,
                    "Open": row.open,
                    "High": row.high,
                    "Low": row.low,
                    "Close": row.close,
                    "Volume": row.volume,
                }
                for row in rows
            ]
        )
        present_tickers = set(raw_df["ticker"].unique())
        missing_tickers = [ticker for ticker in requested_tickers if ticker not in present_tickers]
        if missing_tickers:
            logger.error(
                "Missing DB price data for tickers=%s in requested range %s to %s",
                missing_tickers,
                requested_start,
                requested_end,
            )
            raise ValueError("No price data in DB for the requested range")

        data = raw_df.pivot(index="date", columns="ticker", values=ohlcv_fields)
        data = data.swaplevel(0, 1, axis=1)
        ordered_columns = pd.MultiIndex.from_product([requested_tickers, ohlcv_fields])
        data = data.reindex(columns=ordered_columns)
        data.index = pd.to_datetime(data.index)
        return data.sort_index()

    def calculate_features(self, df: pd.DataFrame) -> pd.DataFrame:
        spy_close = df["SPY"]["Close"]
        spy_returns = np.log(spy_close / spy_close.shift(1))

        processed: list[pd.DataFrame] = []
        for ticker in self.tickers:
            if ticker == "SPY":
                continue
            t_data = df[ticker].copy()
            close = t_data["Close"]
            volume = t_data["Volume"]

            log_ret = np.log(close / close.shift(1))
            volatility = log_ret.rolling(window=9).std() * np.sqrt(252)
            ema_20 = close.ewm(span=20, adjust=False).mean()
            ema_50 = close.ewm(span=50, adjust=False).mean()
            trend_20 = (close - ema_20) / ema_20
            trend_50 = (close - ema_50) / ema_50
            rolling_cov = log_ret.rolling(window=60).cov(spy_returns)
            rolling_var = spy_returns.rolling(window=60).var()
            beta = rolling_cov / rolling_var
            log_vol = np.log(volume + 1e-8)

            n_period, k_period, d_period = 10, 5, 10
            hh = t_data["High"].rolling(window=n_period).max()
            ll = t_data["Low"].rolling(window=n_period).min()
            midpoint = (hh + ll) / 2
            diff = close - midpoint
            range_len = hh - ll
            smooth1_diff = diff.ewm(span=k_period, adjust=False).mean()
            smooth2_diff = smooth1_diff.ewm(span=d_period, adjust=False).mean()
            smooth1_range = range_len.ewm(span=k_period, adjust=False).mean()
            smooth2_range = smooth1_range.ewm(span=d_period, adjust=False).mean()
            smi = 100 * (smooth2_diff / (0.5 * smooth2_range + 1e-8))
            smi_normalized = smi / 100.0

            if self.forecast_horizon == 1:
                target_return = log_ret.shift(-1)
            else:
                target_return = log_ret.rolling(window=self.forecast_horizon).sum().shift(-self.forecast_horizon)

            features = pd.DataFrame(
                {
                    f"{ticker}_log_ret": log_ret,
                    f"{ticker}_volatility": volatility,
                    f"{ticker}_trend_20": trend_20,
                    f"{ticker}_trend_50": trend_50,
                    f"{ticker}_beta": beta,
                    f"{ticker}_log_vol": log_vol,
                    f"{ticker}_smi": smi_normalized,
                    f"{ticker}_target": target_return,
                },
                index=t_data.index,
            )
            processed.append(features)

        return pd.concat(processed, axis=1)

    def create_tensors(
        self, feature_df: pd.DataFrame
    ) -> Tuple[np.ndarray, np.ndarray, list[str], pd.DatetimeIndex]:
        feature_df = feature_df.dropna()
        assets = [t for t in self.tickers if t != "SPY"]
        feature_names = ["log_ret", "volatility", "trend_20", "trend_50", "beta", "log_vol", "smi"]

        dates = feature_df.index
        data_values = feature_df.values
        col_map = {name: i for i, name in enumerate(feature_df.columns)}

        X_all, y_all, valid_dates = [], [], []

        for i in range(self.lookback, len(dates)):
            X_t, y_t = [], []
            for asset in assets:
                asset_cols = [col_map[f"{asset}_{f}"] for f in feature_names]
                target_col = col_map[f"{asset}_target"]
                start_row = i - self.lookback + 1
                seq = data_values[start_row : i + 1, asset_cols]
                target = data_values[i, target_col]
                X_t.append(seq)
                y_t.append(target)
            X_all.append(np.array(X_t))
            y_all.append(np.array(y_t))
            valid_dates.append(dates[i])

        return np.array(X_all), np.array(y_all), assets, pd.DatetimeIndex(valid_dates)
