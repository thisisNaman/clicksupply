import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.models import Brand, CrawlerLog, User
from app.schemas.schemas import CrawlerLogOut
from app.services.analytics.crawler_parser import parse_log_lines

router = APIRouter(prefix="/agent-analytics", tags=["agent-analytics"])


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

    # Insert crawler logs
    logs_created = 0
    for entry in parsed:
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
    }
