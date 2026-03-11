from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database import get_db
from ..models.stock import StockMetadata
from ..schemas.stock import StockMetadataResponse

router = APIRouter(prefix="/api/stocks", tags=["stocks"])


@router.get("/metadata", response_model=list[StockMetadataResponse])
async def get_stock_metadata(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(StockMetadata).order_by(StockMetadata.sector, StockMetadata.ticker))
    stocks = result.scalars().all()
    return stocks


@router.get("/sectors", response_model=list[str])
async def get_sectors(db: AsyncSession = Depends(get_db)):
    """Return distinct sector names from stock_metadata for preference UI. Excludes 'Unknown'."""
    result = await db.execute(
        select(StockMetadata.sector)
        .distinct()
        .where(
            StockMetadata.sector.isnot(None),
            StockMetadata.sector != "",
            StockMetadata.sector != "Unknown",
        )
        .order_by(StockMetadata.sector)
    )
    return [row[0] for row in result.all()]
