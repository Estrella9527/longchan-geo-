"""
Analysis service — computes GEO metrics from task results.

Metrics:
- Visibility: % of answers that mention the brand
- Ranking: average position of brand mention in answers
- Sentiment: positive/neutral/negative classification
- Source analysis: domain frequency from extracted sources
"""
import re
from collections import Counter
from urllib.parse import urlparse

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.brand import Brand
from app.models.task import Task, TaskResult


async def get_brand_analysis(
    db: AsyncSession,
    brand_id: str,
    days: int = 30,
) -> dict:
    """Compute GEO analysis metrics for a brand."""
    # Get brand
    brand = (await db.execute(select(Brand).where(Brand.id == brand_id))).scalar_one_or_none()
    if not brand:
        return {"error": "Brand not found"}

    brand_name = brand.name.lower()
    brand_keywords = [brand_name]
    # Add brand name without common suffixes as alternative
    for suffix in ("品牌", "公司", "集团"):
        if brand_name.endswith(suffix) and len(brand_name) > len(suffix):
            brand_keywords.append(brand_name[:-len(suffix)])

    # Get all task results for this brand's tasks
    results = (await db.execute(
        select(TaskResult)
        .join(Task, Task.id == TaskResult.task_id)
        .where(Task.brand_id == brand_id)
        .where(Task.status == "completed")
        .order_by(TaskResult.created_at.desc())
    )).scalars().all()

    if not results:
        return {
            "brand_name": brand.name,
            "total_results": 0,
            "visibility": {"score": 0, "mentioned_count": 0, "total": 0},
            "ranking": {"avg_position": 0, "positions": []},
            "sentiment": {"positive": 0, "neutral": 0, "negative": 0},
            "sources": {"domains": [], "total_sources": 0},
            "trend": [],
        }

    # --- Visibility ---
    mentioned = 0
    for r in results:
        answer = (r.answer_text or "").lower()
        if any(kw in answer for kw in brand_keywords):
            mentioned += 1

    visibility_score = round(mentioned / len(results) * 100, 1) if results else 0

    # --- Ranking (position of brand mention in answer) ---
    positions = []
    for r in results:
        answer = (r.answer_text or "").lower()
        # Find first position of brand mention (by paragraph)
        paragraphs = [p.strip() for p in answer.split("\n") if p.strip()]
        for i, p in enumerate(paragraphs):
            if any(kw in p for kw in brand_keywords):
                positions.append(i + 1)
                break

    avg_position = round(sum(positions) / len(positions), 1) if positions else 0

    # --- Sentiment (simple keyword-based) ---
    positive_words = {"好", "优秀", "推荐", "可靠", "优质", "领先", "首选", "信赖", "满意", "出色", "高品质", "专业"}
    negative_words = {"差", "问题", "投诉", "差评", "劣质", "不推荐", "差劲", "糟糕", "不满", "缺陷", "不靠谱"}

    pos_count = 0
    neg_count = 0
    neu_count = 0
    for r in results:
        answer = r.answer_text or ""
        has_pos = any(w in answer for w in positive_words)
        has_neg = any(w in answer for w in negative_words)
        if has_pos and not has_neg:
            pos_count += 1
        elif has_neg and not has_pos:
            neg_count += 1
        else:
            neu_count += 1

    # --- Source analysis ---
    domain_counter: Counter = Counter()
    total_sources = 0
    for r in results:
        sources = r.sources if isinstance(r.sources, list) else []
        for s in sources:
            url = s.get("url", "") if isinstance(s, dict) else ""
            if url:
                try:
                    domain = urlparse(url).netloc
                    if domain:
                        domain_counter[domain] += 1
                        total_sources += 1
                except Exception:
                    pass

    top_domains = [
        {"domain": d, "count": c, "percentage": round(c / total_sources * 100, 1)}
        for d, c in domain_counter.most_common(10)
    ] if total_sources > 0 else []

    # --- Trend (group by date) ---
    date_groups: dict[str, dict] = {}
    for r in results:
        date_key = r.created_at.strftime("%Y-%m-%d") if r.created_at else "unknown"
        if date_key not in date_groups:
            date_groups[date_key] = {"total": 0, "mentioned": 0}
        date_groups[date_key]["total"] += 1
        answer = (r.answer_text or "").lower()
        if any(kw in answer for kw in brand_keywords):
            date_groups[date_key]["mentioned"] += 1

    trend = sorted([
        {
            "date": date,
            "visibility": round(g["mentioned"] / g["total"] * 100, 1) if g["total"] > 0 else 0,
            "total": g["total"],
            "mentioned": g["mentioned"],
        }
        for date, g in date_groups.items()
    ], key=lambda x: x["date"])

    return {
        "brand_name": brand.name,
        "total_results": len(results),
        "visibility": {
            "score": visibility_score,
            "mentioned_count": mentioned,
            "total": len(results),
        },
        "ranking": {
            "avg_position": avg_position,
            "positions": positions[:50],
        },
        "sentiment": {
            "positive": pos_count,
            "neutral": neu_count,
            "negative": neg_count,
        },
        "sources": {
            "domains": top_domains,
            "total_sources": total_sources,
        },
        "trend": trend,
    }


async def get_competitor_analysis(
    db: AsyncSession,
    brand_ids: list[str],
) -> list[dict]:
    """Compare GEO metrics across multiple brands."""
    results = []
    for bid in brand_ids[:5]:  # Max 5 brands
        analysis = await get_brand_analysis(db, bid)
        if "error" not in analysis:
            results.append({
                "brand_id": bid,
                "brand_name": analysis["brand_name"],
                "visibility": analysis["visibility"]["score"],
                "avg_position": analysis["ranking"]["avg_position"],
                "sentiment_positive": analysis["sentiment"]["positive"],
                "sentiment_negative": analysis["sentiment"]["negative"],
                "total_results": analysis["total_results"],
            })
    return results


async def export_task_results_csv(
    db: AsyncSession,
    task_id: str,
) -> list[dict]:
    """Get all task results formatted for CSV export."""
    results = (await db.execute(
        select(TaskResult)
        .where(TaskResult.task_id == task_id)
        .order_by(TaskResult.created_at)
    )).scalars().all()

    rows = []
    for r in results:
        sources = r.sources if isinstance(r.sources, list) else []
        source_urls = "; ".join(
            s.get("url", "") for s in sources if isinstance(s, dict)
        )
        rows.append({
            "question": r.question_text,
            "answer": r.answer_text,
            "model": r.model_name,
            "sources": source_urls,
            "source_count": len(sources),
            "created_at": r.created_at.isoformat() if r.created_at else "",
        })
    return rows
