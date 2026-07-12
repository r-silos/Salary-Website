from fastapi import APIRouter, Depends
from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from app.compare import compare_salary
from app.config import settings
from app.db import get_db
from app.models import LcaFiling, OewsEstimate
from app.schemas import CompareRequest, CompareResponse, MetaResponse

router = APIRouter()


@router.post("/v1/compare", response_model=CompareResponse)
def compare(req: CompareRequest, db: Session = Depends(get_db)) -> CompareResponse:
    return compare_salary(db, req)


@router.get("/v1/meta", response_model=MetaResponse)
def meta(db: Session = Depends(get_db)) -> MetaResponse:
    oews_rows = db.scalar(select(func.count()).select_from(OewsEstimate)) or 0
    lca_rows = db.scalar(select(func.count()).select_from(LcaFiling)) or 0
    oews_years = sorted(db.scalars(select(distinct(OewsEstimate.year))).all())
    lca_years = sorted(
        y for y in db.scalars(select(distinct(LcaFiling.fiscal_year))).all() if y is not None
    )
    return MetaResponse(
        oews_rows=oews_rows,
        lca_rows=lca_rows,
        oews_years=oews_years,
        lca_fiscal_years=lca_years,
        lca_min_sample=settings.lca_min_sample,
    )
