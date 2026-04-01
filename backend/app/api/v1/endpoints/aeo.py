from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.models import User
from app.schemas.schemas import AEOAuditRequest, AEOAuditResult
from app.services.recommendations.aeo_engine import aeo_engine

router = APIRouter(prefix="/aeo", tags=["aeo"])


@router.post("/audit", response_model=AEOAuditResult)
async def audit_page(
    req: AEOAuditRequest,
    user: User = Depends(get_current_user),
):
    """Run an AEO readiness audit on a web page.

    Analyzes content structure, schema markup, technical SEO, and trust signals.
    Returns a score (0-100) with actionable recommendations.
    """
    return await aeo_engine.audit_page(req.url)
