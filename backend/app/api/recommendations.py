import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..database import get_db
from ..models.user import User, UserPreference
from ..models.recommendation import Recommendation, BacktestResult, ExplanationSnapshot
from ..schemas.recommendation import (
    RecommendationRequest,
    RecommendationResponse,
    RecommendationDetailResponse,
    RecommendationHistoryResponse,
    RecommendationHistoryItemResponse,
)
from .deps import get_current_user
from ..services.recommendation_service import run_recommendation_pipeline

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


@router.post("/generate", response_model=RecommendationDetailResponse)
async def generate_recommendation(
    payload: RecommendationRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a new stock recommendation based on user preferences."""
    # Resolve preferences: use payload overrides or fetch saved preferences
    result = await db.execute(
        select(UserPreference)
        .where(UserPreference.user_id == user.id)
        .order_by(UserPreference.created_at.desc())
        .limit(1)
    )
    saved_pref = result.scalar_one_or_none()

    sectors = payload.sectors or (saved_pref.sectors if saved_pref else [])
    risk_tolerance = payload.risk_tolerance or (saved_pref.risk_tolerance if saved_pref else "moderate")
    excluded_tickers = payload.excluded_tickers or (saved_pref.excluded_tickers if saved_pref else [])
    indicator_preferences = payload.indicator_preferences if payload.indicator_preferences is not None else (saved_pref.indicator_preferences if saved_pref else {})
    market_cap_buckets = payload.market_cap_buckets if payload.market_cap_buckets is not None else (getattr(saved_pref, "market_cap_buckets", None) if saved_pref else [])

    try:
        rec, backtest, explanations = await run_recommendation_pipeline(
            db=db,
            user_id=user.id,
            sectors=sectors,
            risk_tolerance=risk_tolerance,
            excluded_tickers=excluded_tickers,
            indicator_preferences=indicator_preferences,
            market_cap_buckets=market_cap_buckets or [],
        )
    except Exception as e:
        logger.exception("Recommendation pipeline failed")
        raise HTTPException(status_code=500, detail=f"Recommendation generation failed: {str(e)}")

    return RecommendationDetailResponse(
        id=rec.id,
        ticker_weights=rec.ticker_weights,
        generated_at=rec.generated_at,
        backtest=backtest,
        explanations=explanations,
    )


@router.get("/latest", response_model=RecommendationDetailResponse)
async def get_latest_recommendation(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Recommendation)
        .where(Recommendation.user_id == user.id)
        .options(selectinload(Recommendation.backtest_result), selectinload(Recommendation.explanations))
        .order_by(Recommendation.generated_at.desc())
        .limit(1)
    )
    rec = result.scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="No recommendations found. Generate one first.")

    return RecommendationDetailResponse(
        id=rec.id,
        ticker_weights=rec.ticker_weights,
        generated_at=rec.generated_at,
        backtest=rec.backtest_result,
        explanations=rec.explanations or [],
    )


@router.get("", response_model=RecommendationHistoryResponse)
async def list_recommendations(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Recommendation)
        .where(Recommendation.user_id == user.id)
        .options(selectinload(Recommendation.model_run))
        .order_by(Recommendation.generated_at.desc())
    )
    rows = result.scalars().all()
    return RecommendationHistoryResponse(
        items=[
            RecommendationHistoryItemResponse(
                id=rec.id,
                generated_at=rec.generated_at,
                model_run_id=rec.model_run_id,
                model_run_date=rec.model_run.run_date if rec.model_run else None,
                preference_snapshot=rec.preference_snapshot or {},
            )
            for rec in rows
        ]
    )


@router.get("/{recommendation_id}", response_model=RecommendationDetailResponse)
async def get_recommendation(
    recommendation_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Recommendation)
        .where(Recommendation.id == recommendation_id, Recommendation.user_id == user.id)
        .options(selectinload(Recommendation.backtest_result), selectinload(Recommendation.explanations))
    )
    rec = result.scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    return RecommendationDetailResponse(
        id=rec.id,
        ticker_weights=rec.ticker_weights,
        generated_at=rec.generated_at,
        backtest=rec.backtest_result,
        explanations=rec.explanations or [],
    )
