from datetime import datetime

from sqlalchemy import DateTime, Float, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class OewsEstimate(Base):
    __tablename__ = "oews_estimates"
    __table_args__ = (
        UniqueConstraint("soc_code", "area_code", "year", name="uq_oews_soc_area_year"),
        Index("ix_oews_soc_area", "soc_code", "area_code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    soc_code: Mapped[str] = mapped_column(String(16), nullable=False)
    occupation_title: Mapped[str] = mapped_column(String(255), nullable=False)
    area_code: Mapped[str] = mapped_column(String(16), nullable=False)
    area_name: Mapped[str] = mapped_column(String(255), nullable=False)
    area_type: Mapped[str] = mapped_column(String(32), nullable=False)  # metro | state | national
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    mean_wage: Mapped[float | None] = mapped_column(Float, nullable=True)
    pct10: Mapped[float | None] = mapped_column(Float, nullable=True)
    pct25: Mapped[float | None] = mapped_column(Float, nullable=True)
    pct50: Mapped[float | None] = mapped_column(Float, nullable=True)
    pct75: Mapped[float | None] = mapped_column(Float, nullable=True)
    pct90: Mapped[float | None] = mapped_column(Float, nullable=True)
    employment: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="oews")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LcaFiling(Base):
    __tablename__ = "lca_filings"
    __table_args__ = (
        UniqueConstraint("case_number", "wage_line", name="uq_lca_case_wage_line"),
        Index("ix_lca_state_title", "worksite_state", "job_title_norm"),
        Index("ix_lca_soc_state", "soc_code", "worksite_state"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_number: Mapped[str] = mapped_column(String(64), nullable=False)
    wage_line: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    job_title: Mapped[str] = mapped_column(String(255), nullable=False)
    job_title_norm: Mapped[str] = mapped_column(String(255), nullable=False)
    soc_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    employer: Mapped[str | None] = mapped_column(String(255), nullable=True)
    worksite_city: Mapped[str | None] = mapped_column(String(128), nullable=True)
    worksite_state: Mapped[str] = mapped_column(String(8), nullable=False)
    wage_annual: Mapped[float] = mapped_column(Float, nullable=False)
    wage_unit: Mapped[str] = mapped_column(String(32), nullable=False)
    fiscal_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    case_status: Mapped[str] = mapped_column(String(64), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="lca")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
