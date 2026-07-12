"""Shared ingest helpers."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.compare import annualize_wage, normalize_soc, normalize_title
from app.db import SessionLocal, engine
from app.models import Base, LcaFiling, OewsEstimate


def ensure_tables() -> None:
    Base.metadata.create_all(bind=engine)


def read_table(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    if suffix == ".csv":
        return pd.read_csv(path)
    raise ValueError(f"Unsupported file type: {path}")


def upsert_oews(db: Session, rows: list[dict]) -> int:
    if not rows:
        return 0
    stmt = insert(OewsEstimate).values(rows)
    stmt = stmt.on_conflict_do_update(
        constraint="uq_oews_soc_area_year",
        set_={
            "occupation_title": stmt.excluded.occupation_title,
            "area_name": stmt.excluded.area_name,
            "area_type": stmt.excluded.area_type,
            "mean_wage": stmt.excluded.mean_wage,
            "pct10": stmt.excluded.pct10,
            "pct25": stmt.excluded.pct25,
            "pct50": stmt.excluded.pct50,
            "pct75": stmt.excluded.pct75,
            "pct90": stmt.excluded.pct90,
            "employment": stmt.excluded.employment,
            "source": stmt.excluded.source,
        },
    )
    db.execute(stmt)
    db.commit()
    return len(rows)


def upsert_lca(db: Session, rows: list[dict]) -> int:
    if not rows:
        return 0
    stmt = insert(LcaFiling).values(rows)
    stmt = stmt.on_conflict_do_update(
        constraint="uq_lca_case_wage_line",
        set_={
            "job_title": stmt.excluded.job_title,
            "job_title_norm": stmt.excluded.job_title_norm,
            "soc_code": stmt.excluded.soc_code,
            "employer": stmt.excluded.employer,
            "worksite_city": stmt.excluded.worksite_city,
            "worksite_state": stmt.excluded.worksite_state,
            "wage_annual": stmt.excluded.wage_annual,
            "wage_unit": stmt.excluded.wage_unit,
            "fiscal_year": stmt.excluded.fiscal_year,
            "case_status": stmt.excluded.case_status,
            "source": stmt.excluded.source,
        },
    )
    db.execute(stmt)
    db.commit()
    return len(rows)


def session() -> Session:
    return SessionLocal()


__all__ = [
    "annualize_wage",
    "ensure_tables",
    "normalize_soc",
    "normalize_title",
    "read_table",
    "session",
    "upsert_lca",
    "upsert_oews",
]
