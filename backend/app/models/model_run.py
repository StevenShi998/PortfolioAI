import uuid
from datetime import datetime, timezone, date
from sqlalchemy import String, Float, DateTime, Date
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class ModelRun(Base):
    __tablename__ = "model_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    hyperparameters: Mapped[dict] = mapped_column(JSONB, nullable=False)
    validation_sharpe: Mapped[float | None] = mapped_column(Float, nullable=True)
    training_loss: Mapped[float | None] = mapped_column(Float, nullable=True)
    model_artifact_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ticker_universe: Mapped[dict] = mapped_column(JSONB, nullable=False)
    data_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    data_end_date: Mapped[date] = mapped_column(Date, nullable=False)
