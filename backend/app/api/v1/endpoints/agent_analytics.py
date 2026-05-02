import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status
from sqlalchemy import Integer as SAInteger, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.models import Brand, CrawlerLog, User
from app.schemas.schemas import CrawlerLogOut
from app.services.analytics.crawler_parser import parse_log_lines

router = APIRouter(prefix="/agent-analytics", tags=["agent-analytics"])


@router.get("/{brand_id}/summary")
async def get_crawler_summary(
    brand_id: uuid.UUID,
    days: int = Query(default=30, ge=1, le=365),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get AI crawler activity summary — visit counts, error rates, top paths per crawler."""
    # Verify brand access
    result = await db.execute(
        select(Brand).where(Brand.id == brand_id, Brand.organization_id == user.organization_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Brand not found")

    since = datetime.now(timezone.utc) - timedelta(days=days)

    # Crawler breakdown
    crawler_result = await db.execute(
        select(
            CrawlerLog.crawler_type,
            func.count(CrawlerLog.id).label("total_visits"),
            func.max(CrawlerLog.timestamp).label("last_seen"),
            func.sum(func.cast(CrawlerLog.status_code >= 400, SAInteger)).label("error_count"),
            func.sum(CrawlerLog.response_size_bytes).label("total_bytes"),
        )
        .where(CrawlerLog.brand_id == brand_id, CrawlerLog.timestamp >= since)
        .group_by(CrawlerLog.crawler_type)
        .order_by(func.count(CrawlerLog.id).desc())
    )

    crawlers = []
    total_visits = 0
    for row in crawler_result:
        ct = row.crawler_type.value if hasattr(row.crawler_type, "value") else row.crawler_type
        visits = row.total_visits
        errors = row.error_count or 0
        total_visits += visits
        crawlers.append({
            "crawler_type": ct,
            "total_visits": visits,
            "last_seen": row.last_seen.isoformat() if row.last_seen else None,
            "error_count": errors,
            "error_rate": round(errors / visits * 100, 1) if visits else 0,
            "total_bytes": row.total_bytes or 0,
        })

    # Top crawled paths
    path_result = await db.execute(
        select(
            CrawlerLog.request_path,
            func.count(CrawlerLog.id).label("hits"),
        )
        .where(CrawlerLog.brand_id == brand_id, CrawlerLog.timestamp >= since)
        .group_by(CrawlerLog.request_path)
        .order_by(func.count(CrawlerLog.id).desc())
        .limit(20)
    )
    top_paths = [{"path": row.request_path, "hits": row.hits} for row in path_result]

    return {
        "period_days": days,
        "total_visits": total_visits,
        "crawler_count": len(crawlers),
        "crawlers": crawlers,
        "top_paths": top_paths,
    }


@router.post("/{brand_id}/ingest-logs", status_code=status.HTTP_201_CREATED)
async def ingest_server_logs(
    brand_id: uuid.UUID,
    file: UploadFile = File(...),
    log_format: str = Form(default="combined"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Ingest server access logs and extract AI crawler visits.

    Supports:
    - combined: Standard Apache/Nginx combined log format
    - cloudfront: AWS CloudFront access logs (tab-separated)
    """
    # Verify brand access
    from sqlalchemy import select
    result = await db.execute(
        select(Brand).where(Brand.id == brand_id, Brand.organization_id == user.organization_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Brand not found")

    # Read and parse log file
    content = await file.read()
    lines = content.decode("utf-8", errors="replace").splitlines()

    parsed = parse_log_lines(lines, log_format)

    # Insert crawler logs (with dedup — skip if same brand+ip+path+timestamp exists)
    logs_created = 0
    skipped = 0
    for entry in parsed:
        # Check for duplicate
        dup = await db.execute(
            select(CrawlerLog.id).where(
                CrawlerLog.brand_id == brand_id,
                CrawlerLog.ip_address == entry["ip_address"],
                CrawlerLog.request_path == entry["request_path"],
                CrawlerLog.timestamp == entry["timestamp"],
            ).limit(1)
        )
        if dup.scalar_one_or_none():
            skipped += 1
            continue

        log = CrawlerLog(
            brand_id=brand_id,
            crawler_type=entry["crawler_type"],
            ip_address=entry["ip_address"],
            user_agent=entry["user_agent"],
            request_path=entry["request_path"],
            status_code=entry["status_code"],
            response_size_bytes=entry["response_size_bytes"],
            timestamp=entry["timestamp"],
        )
        db.add(log)
        logs_created += 1

    await db.flush()

    return {
        "total_lines_processed": len(lines),
        "ai_crawler_entries_found": len(parsed),
        "logs_created": logs_created,
        "duplicates_skipped": skipped,
    }
