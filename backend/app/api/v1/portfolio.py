"""
Portfolio API — read-only, company-scoped aggregation across a company's
active Missions. See app.services.portfolio_service for the aggregation
logic itself; this router only handles auth/DB wiring, matching every
other route module's thin-router convention.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import User
from app.schemas.portfolio import PortfolioResponse
from app.services import portfolio_service

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("", response_model=PortfolioResponse)
def get_portfolio(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PortfolioResponse:
    return portfolio_service.get_portfolio(db, current_user.company_id)
