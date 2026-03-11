from pydantic import BaseModel


class StockMetadataResponse(BaseModel):
    ticker: str
    name: str
    sector: str
    market_cap_bucket: str | None = None

    model_config = {"from_attributes": True}
