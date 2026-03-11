"""Seed stock metadata on startup if the table is empty."""
import logging
from sqlalchemy import select, func
from .database import async_session
from .models.stock import StockMetadata

logger = logging.getLogger(__name__)

# S&P 500 (GICS) sector alignment: one entry per ALL_TICKERS so sector filtering works.
STOCK_CATALOG = [
    # Energy
    {"ticker": "XOM", "name": "Exxon Mobil Corporation", "sector": "Energy", "market_cap_bucket": "large"},
    {"ticker": "CVX", "name": "Chevron Corporation", "sector": "Energy", "market_cap_bucket": "large"},
    {"ticker": "COP", "name": "ConocoPhillips", "sector": "Energy", "market_cap_bucket": "large"},
    {"ticker": "LEU", "name": "Centrus Energy Corp.", "sector": "Energy", "market_cap_bucket": "small"},
    {"ticker": "OKLO", "name": "Oklo Inc.", "sector": "Energy", "market_cap_bucket": "small"},
    # Materials
    {"ticker": "LIN", "name": "Linde plc", "sector": "Materials", "market_cap_bucket": "large"},
    {"ticker": "APD", "name": "Air Products and Chemicals Inc.", "sector": "Materials", "market_cap_bucket": "large"},
    {"ticker": "SHW", "name": "The Sherwin-Williams Company", "sector": "Materials", "market_cap_bucket": "large"},
    # Industrials
    {"ticker": "CAT", "name": "Caterpillar Inc.", "sector": "Industrials", "market_cap_bucket": "large"},
    {"ticker": "HON", "name": "Honeywell International Inc.", "sector": "Industrials", "market_cap_bucket": "large"},
    {"ticker": "UPS", "name": "United Parcel Service Inc.", "sector": "Industrials", "market_cap_bucket": "large"},
    # Consumer Discretionary
    {"ticker": "AMZN", "name": "Amazon.com Inc.", "sector": "Consumer Discretionary", "market_cap_bucket": "large"},
    {"ticker": "TSLA", "name": "Tesla Inc.", "sector": "Consumer Discretionary", "market_cap_bucket": "large"},
    {"ticker": "HD", "name": "The Home Depot Inc.", "sector": "Consumer Discretionary", "market_cap_bucket": "large"},
    {"ticker": "NKE", "name": "Nike Inc.", "sector": "Consumer Discretionary", "market_cap_bucket": "large"},
    # Consumer Staples
    {"ticker": "PG", "name": "Procter & Gamble Co.", "sector": "Consumer Staples", "market_cap_bucket": "large"},
    {"ticker": "KO", "name": "The Coca-Cola Company", "sector": "Consumer Staples", "market_cap_bucket": "large"},
    {"ticker": "WMT", "name": "Walmart Inc.", "sector": "Consumer Staples", "market_cap_bucket": "large"},
    # Health Care
    {"ticker": "JNJ", "name": "Johnson & Johnson", "sector": "Health Care", "market_cap_bucket": "large"},
    {"ticker": "UNH", "name": "UnitedHealth Group Inc.", "sector": "Health Care", "market_cap_bucket": "large"},
    {"ticker": "PFE", "name": "Pfizer Inc.", "sector": "Health Care", "market_cap_bucket": "large"},
    # Financials
    {"ticker": "JPM", "name": "JPMorgan Chase & Co.", "sector": "Financials", "market_cap_bucket": "large"},
    {"ticker": "BAC", "name": "Bank of America Corp.", "sector": "Financials", "market_cap_bucket": "large"},
    {"ticker": "WFC", "name": "Wells Fargo & Company", "sector": "Financials", "market_cap_bucket": "large"},
    {"ticker": "HOOD", "name": "Robinhood Markets Inc.", "sector": "Financials", "market_cap_bucket": "mid"},
    # Information Technology
    {"ticker": "AAPL", "name": "Apple Inc.", "sector": "Information Technology", "market_cap_bucket": "large"},
    {"ticker": "MSFT", "name": "Microsoft Corporation", "sector": "Information Technology", "market_cap_bucket": "large"},
    {"ticker": "NVDA", "name": "NVIDIA Corporation", "sector": "Information Technology", "market_cap_bucket": "large"},
    {"ticker": "ORCL", "name": "Oracle Corporation", "sector": "Information Technology", "market_cap_bucket": "large"},
    # Communication Services
    {"ticker": "GOOGL", "name": "Alphabet Inc.", "sector": "Communication Services", "market_cap_bucket": "large"},
    {"ticker": "META", "name": "Meta Platforms Inc.", "sector": "Communication Services", "market_cap_bucket": "large"},
    {"ticker": "NFLX", "name": "Netflix Inc.", "sector": "Communication Services", "market_cap_bucket": "large"},
    # Utilities
    {"ticker": "NEE", "name": "NextEra Energy Inc.", "sector": "Utilities", "market_cap_bucket": "large"},
    {"ticker": "DUK", "name": "Duke Energy Corporation", "sector": "Utilities", "market_cap_bucket": "large"},
    {"ticker": "SO", "name": "The Southern Company", "sector": "Utilities", "market_cap_bucket": "large"},
    # Real Estate
    {"ticker": "PLD", "name": "Prologis Inc.", "sector": "Real Estate", "market_cap_bucket": "large"},
    {"ticker": "AMT", "name": "American Tower Corporation", "sector": "Real Estate", "market_cap_bucket": "large"},
    {"ticker": "EQIX", "name": "Equinix Inc.", "sector": "Real Estate", "market_cap_bucket": "large"},
    # ETFs / benchmark
    {"ticker": "QQQ", "name": "Invesco QQQ Trust", "sector": "ETF", "market_cap_bucket": "large"},
    {"ticker": "SPY", "name": "SPDR S&P 500 ETF Trust", "sector": "ETF", "market_cap_bucket": "large"},
]


async def seed_stock_metadata():
    async with async_session() as session:
        result = await session.execute(select(func.count()).select_from(StockMetadata))
        count = result.scalar()
        if count and count > 0:
            logger.info(f"Stock metadata already seeded ({count} records).")
            return

        for item in STOCK_CATALOG:
            session.add(StockMetadata(**item))
        await session.commit()
        logger.info(f"Seeded {len(STOCK_CATALOG)} stock metadata records.")
