from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.middleware.auth import get_current_user
from app.models.brand import Brand
from app.models.user import User
from app.schemas.brand import BrandCreate, BrandResponse, BrandUpdate

router = APIRouter()


@router.get("", response_model=list[BrandResponse])
async def list_brands(
    keyword: str = Query("", description="搜索关键字"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = select(Brand).order_by(Brand.created_at.desc())
    if keyword:
        q = q.where(Brand.name.ilike(f"%{keyword}%"))
    q = q.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    return [BrandResponse.model_validate(b, from_attributes=True) for b in result.scalars().all()]


@router.post("", response_model=BrandResponse, status_code=status.HTTP_201_CREATED)
async def create_brand(body: BrandCreate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    brand = Brand(**body.model_dump(), created_by=user.id)
    db.add(brand)
    await db.commit()
    await db.refresh(brand)
    return BrandResponse.model_validate(brand, from_attributes=True)


@router.get("/{brand_id}", response_model=BrandResponse)
async def get_brand(brand_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(Brand).where(Brand.id == brand_id))
    brand = result.scalar_one_or_none()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    return BrandResponse.model_validate(brand, from_attributes=True)


@router.put("/{brand_id}", response_model=BrandResponse)
async def update_brand(brand_id: str, body: BrandUpdate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(Brand).where(Brand.id == brand_id))
    brand = result.scalar_one_or_none()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(brand, k, v)
    await db.commit()
    await db.refresh(brand)
    return BrandResponse.model_validate(brand, from_attributes=True)


@router.delete("/{brand_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_brand(brand_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(Brand).where(Brand.id == brand_id))
    brand = result.scalar_one_or_none()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    await db.delete(brand)
    await db.commit()
