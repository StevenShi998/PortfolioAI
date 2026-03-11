"""
Ingest daily price bars from yfinance into price_series.

This service is designed for:
- initial backfill
- daily incremental updates (idempotent via upsert)
"""
from __future__ import annotations

import argparse
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Iterable

import yfinance as yf
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from ..database import get_sync_db_session
from ..ml.config import ALL_TICKERS, START_DATE, END_DATE
from ..models.price_series import PriceSeries
from ..models.stock import StockMetadata

logger = logging.getLogger(__name__)


def _parse_date(value: str | date | None) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.fromisoformat(value).date()


def _resolve_tickers(tickers: Iterable[str] | None) -> list[str]:
    if tickers is None:
        return list(ALL_TICKERS)
    return [t.strip().upper() for t in tickers if t.strip()]


# Market cap bucket thresholds (USD)
_MARKET_CAP_LARGE_B = 20.5
_MARKET_CAP_MID_B = 7.4


def _market_cap_bucket(market_cap: float | None) -> str | None:
    """Map numeric market cap (USD) to small / mid / large."""
    if market_cap is None or market_cap <= 0:
        return None
    b = market_cap / 1e9
    if b >= _MARKET_CAP_LARGE_B:
        return "large"
    if b >= _MARKET_CAP_MID_B:
        return "mid"
    return "small"


def _fetch_yf_metadata(ticker: str) -> dict[str, str | None]:
    """
    Fetch sector, name, and market_cap_bucket from yfinance Ticker.info.
    Returns dict with keys: sector, name, market_cap_bucket (fallbacks: Unknown, ticker, None).
    """
    out: dict[str, str | None] = {"sector": "Unknown", "name": ticker, "market_cap_bucket": None}
    try:
        info = yf.Ticker(ticker).info
        if not isinstance(info, dict):
            return out
        sector = info.get("sector") or info.get("industry")
        if sector and isinstance(sector, str):
            out["sector"] = sector.strip() or "Unknown"
        name = info.get("longName") or info.get("shortName")
        if name and isinstance(name, str):
            out["name"] = name.strip()[:255] or ticker
        mc = info.get("marketCap")
        if mc is not None and isinstance(mc, (int, float)):
            out["market_cap_bucket"] = _market_cap_bucket(float(mc))
    except Exception as e:
        logger.debug("yfinance info failed for %s: %s", ticker, e)
    return out


def _ensure_stock_metadata(session: Session, tickers: list[str]) -> int:
    existing = set(
        session.execute(select(StockMetadata.ticker).where(StockMetadata.ticker.in_(tickers))).scalars().all()
    )
    missing = [t for t in tickers if t not in existing]
    for ticker in missing:
        meta = _fetch_yf_metadata(ticker)
        session.add(
            StockMetadata(
                ticker=ticker,
                name=meta["name"] or ticker,
                sector=meta["sector"] or "Unknown",
                market_cap_bucket=meta["market_cap_bucket"],
                last_price_update=None,
            )
        )
    return len(missing)


def _incremental_start_dates(
    session: Session,
    tickers: list[str],
    fallback_start: date,
) -> dict[str, date]:
    rows = session.execute(
        select(PriceSeries.ticker, func.max(PriceSeries.date))
        .where(PriceSeries.ticker.in_(tickers))
        .group_by(PriceSeries.ticker)
    ).all()
    max_by_ticker = {ticker: max_date for ticker, max_date in rows}
    starts: dict[str, date] = {}
    for ticker in tickers:
        max_date = max_by_ticker.get(ticker)
        starts[ticker] = (max_date + timedelta(days=1)) if max_date else fallback_start
    return starts


def _fetch_daily_bars_yf(ticker: str, start: date, end: date) -> list[dict]:
    """Fetch daily OHLCV + dividends/splits from yfinance. Returns list of row dicts."""
    if start > end:
        return []

    # yfinance end is exclusive; use next day to include end_date
    end_exclusive = (end + timedelta(days=1)).isoformat()
    start_str = start.isoformat()

    try:
        hist = yf.Ticker(ticker).history(start=start_str, end=end_exclusive, auto_adjust=True)
    except Exception as e:
        logger.warning("yfinance fetch failed for %s %s–%s: %s", ticker, start_str, end_exclusive, e)
        return []

    if hist is None or hist.empty:
        return []

    rows = []
    for ts, row in hist.iterrows():
        if hasattr(ts, "date"):
            row_date = ts.date() if hasattr(ts, "date") else ts
        else:
            row_date = ts
        if isinstance(row_date, datetime):
            row_date = row_date.date()
        open_ = row.get("Open")
        high = row.get("High")
        low = row.get("Low")
        close = row.get("Close")
        volume = row.get("Volume")
        if open_ is None or high is None or low is None or close is None:
            continue
        rows.append({
            "ticker": ticker,
            "date": row_date,
            "open": float(open_),
            "high": float(high),
            "low": float(low),
            "close": float(close),
            "volume": int(volume) if volume is not None and (not isinstance(volume, float) or volume == volume) else 0,
            "dividends": float(row.get("Dividends", 0) or 0),
            "stock_splits": float(row.get("Stock Splits", 0) or 0),
        })
    return rows


def _upsert_price_rows(session: Session, rows: list[dict]) -> int:
    if not rows:
        return 0

    stmt = pg_insert(PriceSeries).values(rows)
    upsert_stmt = stmt.on_conflict_do_update(
        index_elements=[PriceSeries.ticker, PriceSeries.date],
        set_={
            "open": stmt.excluded.open,
            "high": stmt.excluded.high,
            "low": stmt.excluded.low,
            "close": stmt.excluded.close,
            "volume": stmt.excluded.volume,
            "dividends": stmt.excluded.dividends,
            "stock_splits": stmt.excluded.stock_splits,
        },
    )
    session.execute(upsert_stmt)
    return len(rows)


def run_ingest(
    session: Session,
    *,
    full_backfill: bool = False,
    tickers: Iterable[str] | None = None,
    start_date: str | date | None = None,
    end_date: str | date | None = None,
) -> dict[str, int | str]:
    """
    Run ingestion from yfinance into price_series.

    - full_backfill=True: fetch full range for all tickers
    - full_backfill=False: fetch incrementally from max(date)+1 per ticker
    """
    selected_tickers = _resolve_tickers(tickers)
    if not selected_tickers:
        raise ValueError("No tickers provided for ingestion")

    default_start = _parse_date(start_date) or _parse_date(START_DATE)
    default_end = _parse_date(END_DATE) if full_backfill else datetime.now(timezone.utc).date()
    resolved_end = _parse_date(end_date) or default_end
    if default_start is None:
        raise ValueError("Unable to resolve start date for ingestion")
    if resolved_end < default_start:
        raise ValueError("end_date must be greater than or equal to start_date")

    inserted_or_updated = 0
    fetched_rows = 0

    with session.begin():
        metadata_inserted = _ensure_stock_metadata(session, selected_tickers)

        if full_backfill or start_date is not None:
            start_by_ticker = {ticker: default_start for ticker in selected_tickers}
        else:
            start_by_ticker = _incremental_start_dates(session, selected_tickers, fallback_start=default_start)

        now_utc = datetime.now(timezone.utc)
        for ticker in selected_tickers:
            ticker_start = start_by_ticker[ticker]
            rows = _fetch_daily_bars_yf(ticker=ticker, start=ticker_start, end=resolved_end)
            fetched_rows += len(rows)
            inserted_or_updated += _upsert_price_rows(session, rows)

            meta = _fetch_yf_metadata(ticker)
            session.execute(
                pg_insert(StockMetadata)
                .values(
                    ticker=ticker,
                    name=meta["name"] or ticker,
                    sector=meta["sector"] or "Unknown",
                    market_cap_bucket=meta["market_cap_bucket"],
                    last_price_update=now_utc,
                )
                .on_conflict_do_update(
                    index_elements=[StockMetadata.ticker],
                    set_={
                        "name": meta["name"] or ticker,
                        "sector": meta["sector"] or "Unknown",
                        "market_cap_bucket": meta["market_cap_bucket"],
                        "last_price_update": now_utc,
                    },
                )
            )

    summary: dict[str, int | str] = {
        "tickers": len(selected_tickers),
        "stock_metadata_inserted": metadata_inserted,
        "bars_fetched": fetched_rows,
        "rows_upserted": inserted_or_updated,
        "mode": "full_backfill" if (full_backfill or start_date is not None) else "incremental",
    }
    logger.info("Price ingestion summary: %s", summary)
    return summary


def _parse_cli_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest daily bars from yfinance into price_series.")
    parser.add_argument("--full-backfill", action="store_true", help="Fetch full configured date range.")
    parser.add_argument("--start-date", type=str, default=None, help="Optional ISO date (YYYY-MM-DD).")
    parser.add_argument("--end-date", type=str, default=None, help="Optional ISO date (YYYY-MM-DD).")
    parser.add_argument(
        "--tickers",
        type=str,
        default=None,
        help="Comma-separated tickers. Defaults to ALL_TICKERS from ml.config.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_cli_args()
    tickers = [t.strip() for t in args.tickers.split(",")] if args.tickers else None
    with get_sync_db_session() as session:
        summary = run_ingest(
            session=session,
            full_backfill=args.full_backfill,
            start_date=args.start_date,
            end_date=args.end_date,
            tickers=tickers,
        )
    print(summary)


if __name__ == "__main__":
    main()
