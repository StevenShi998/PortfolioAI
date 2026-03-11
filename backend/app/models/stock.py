from datetime import datetime
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class StockMetadata(Base):
    __tablename__ = "stock_metadata"

    ticker: Mapped[str] = mapped_column(String(10), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sector: Mapped[str] = mapped_column(String(100), nullable=False)
    market_cap_bucket: Mapped[str | None] = mapped_column(String(20), nullable=True)
    last_price_update: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
