import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import engine, Base
from .api import auth, preferences, recommendations, stocks
from .seed import seed_stock_metadata
from . import models as _models  # noqa: F401 -- ensure all tables are registered before create_all

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Creating database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all) #create all tables                                     
    await seed_stock_metadata()
    logger.info("Startup complete.")
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title="Dynamic Portfolio Optimization",
    description="AI-powered stock recommendation engine",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://frontend:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(preferences.router)
app.include_router(recommendations.router)
app.include_router(stocks.router)


@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}
