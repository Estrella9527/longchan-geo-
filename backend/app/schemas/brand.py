from datetime import datetime

from pydantic import BaseModel


class BrandCreate(BaseModel):
    name: str
    industry: str = ""
    target_audience: str = ""
    selling_points: str = ""
    price_range: str = ""
    description: str = ""


class BrandUpdate(BaseModel):
    name: str | None = None
    industry: str | None = None
    target_audience: str | None = None
    selling_points: str | None = None
    price_range: str | None = None
    description: str | None = None


class BrandResponse(BaseModel):
    id: str
    name: str
    industry: str
    target_audience: str
    selling_points: str
    price_range: str
    description: str
    created_by: str
    created_at: datetime
    updated_at: datetime
