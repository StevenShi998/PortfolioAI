import uuid
from datetime import datetime, timezone, date
from sqlalchemy import String, Float, Text, DateTime, Date, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    model_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("model_runs.id"), nullable=True)
    ticker_weights: Mapped[dict] = mapped_column(JSONB, nullable=False)
    preference_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)

    user: Mapped["User"] = relationship(back_populates="recommendations")
    model_run: Mapped["ModelRun"] = relationship()
    backtest_result: Mapped["BacktestResult | None"] = relationship(back_populates="recommendation", uselist=False, cascade="all, delete-orphan")
    explanations: Mapped[list["ExplanationSnapshot"]] = relationship(back_populates="recommendation", cascade="all, delete-orphan")


class BacktestResult(Base):
    __tablename__ = "backtest_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recommendation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recommendations.id", ondelete="CASCADE"), unique=True, index=True
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    cumulative_return: Mapped[float] = mapped_column(Float, nullable=False)
    annualized_return: Mapped[float] = mapped_column(Float, nullable=False)
    sharpe_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    max_drawdown: Mapped[float] = mapped_column(Float, nullable=False)
    benchmark_return: Mapped[float] = mapped_column(Float, nullable=False)
    daily_values: Mapped[dict] = mapped_column(JSONB, nullable=False)

    recommendation: Mapped["Recommendation"] = relationship(back_populates="backtest_result")


class ExplanationSnapshot(Base):
    __tablename__ = "explanation_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recommendation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recommendations.id", ondelete="CASCADE"), index=True
    )
    ticker: Mapped[str] = mapped_column(String(10), nullable=False)
    allocation_pct: Mapped[float] = mapped_column(Float, nullable=False)
    reasoning_text: Mapped[str] = mapped_column(Text, nullable=False)
    metrics: Mapped[dict] = mapped_column(JSONB, nullable=False)

    recommendation: Mapped["Recommendation"] = relationship(back_populates="explanations")
