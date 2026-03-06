"""
Analysis API — GEO metrics, competitor analysis, CSV export.

GET  /api/v1/analysis/brand/{brand_id}     — Brand GEO analysis
GET  /api/v1/analysis/competitor           — Multi-brand comparison
GET  /api/v1/analysis/export/{task_id}     — Export task results as CSV
"""
import csv
import io
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.services.analysis.analysis_service import (
    get_brand_analysis,
    get_competitor_analysis,
    export_task_results_csv,
)

router = APIRouter()


@router.get("/brand/{brand_id}")
async def brand_analysis(
    brand_id: str,
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get GEO analysis metrics for a brand."""
    result = await get_brand_analysis(db, brand_id, days)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/competitor")
async def competitor_analysis(
    brand_ids: str = Query(..., description="Comma-separated brand IDs"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Compare GEO metrics across multiple brands."""
    ids = [bid.strip() for bid in brand_ids.split(",") if bid.strip()]
    if len(ids) < 2:
        raise HTTPException(status_code=400, detail="At least 2 brand IDs required")
    return await get_competitor_analysis(db, ids)


@router.get("/export/{task_id}")
async def export_results_csv(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Export task results as CSV file."""
    rows = await export_task_results_csv(db, task_id)
    if not rows:
        raise HTTPException(status_code=404, detail="No results found")

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=task_{task_id}_results.csv"},
    )
