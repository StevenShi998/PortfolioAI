from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database import get_db
from ..models.user import User, UserPreference
from ..schemas.preferences import PreferencesCreate, PreferencesResponse
from .deps import get_current_user

router = APIRouter(prefix="/api/preferences", tags=["preferences"])

@router.post("", response_model=PreferencesResponse)
async def save_preferences(
    payload: PreferencesCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pref = UserPreference(
        user_id=user.id,
        sectors=payload.sectors,
        risk_tolerance=payload.risk_tolerance,
        excluded_tickers=payload.excluded_tickers,
        indicator_preferences=payload.indicator_preferences,
        market_cap_buckets=payload.market_cap_buckets,
    )
    db.add(pref)
    await db.commit()
    await db.refresh(pref)
    return pref


@router.get("/latest", response_model=PreferencesResponse)
async def get_latest_preferences(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserPreference)
        .where(UserPreference.user_id == user.id)
        .order_by(UserPreference.created_at.desc())
        .limit(1)
    )
    pref = result.scalar_one_or_none()
    if not pref:
        raise HTTPException(status_code=404, detail="No preferences found. Please set your preferences first.")
    return pref
