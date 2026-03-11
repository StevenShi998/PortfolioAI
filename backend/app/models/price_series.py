from datetime import date
from sqlalchemy import String, Float, Date, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base

class PriceSeries(Base):
    __tablename__ = "price_series"

    ticker: Mapped[str] = mapped_column(
        String(10), 
        ForeignKey("stock_metadata.ticker", ondelete="RESTRICT"),
        nullable=False, 
        primary_key=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, primary_key=True, index = True)
    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[int] = mapped_column(Integer, nullable=False)
    dividends: Mapped[float] = mapped_column(Float, nullable=False)
    stock_splits: Mapped[float] = mapped_column(Float, nullable=False)