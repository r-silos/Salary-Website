import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.models import LcaFiling, OewsEstimate


@pytest.fixture()
def db() -> Session:
    """In-memory SQLite session with tables for compare unit tests."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def seeded_db(db: Session) -> Session:
    db.add_all(
        [
            OewsEstimate(
                soc_code="15-1252",
                occupation_title="Software Developers",
                area_code="42660",
                area_name="Seattle-Tacoma-Bellevue, WA",
                area_type="metro",
                year=2024,
                mean_wage=145000,
                pct25=120000,
                pct50=140000,
                pct75=170000,
                employment=80000,
                source="oews",
            ),
            OewsEstimate(
                soc_code="15-1252",
                occupation_title="Software Developers",
                area_code="ST-WA",
                area_name="Washington",
                area_type="state",
                year=2024,
                mean_wage=135000,
                pct25=110000,
                pct50=130000,
                pct75=160000,
                employment=120000,
                source="oews",
            ),
            OewsEstimate(
                soc_code="15-1252",
                occupation_title="Software Developers",
                area_code="99",
                area_name="United States",
                area_type="national",
                year=2024,
                mean_wage=130000,
                pct25=105000,
                pct50=127000,
                pct75=155000,
                employment=1600000,
                source="oews",
            ),
        ]
    )
    for i in range(35):
        db.add(
            LcaFiling(
                case_number=f"I-2024-{i}",
                wage_line=1,
                job_title="Software Developer",
                job_title_norm="software developer",
                soc_code="15-1252",
                employer=f"Co {i}",
                worksite_city="Seattle",
                worksite_state="WA",
                wage_annual=100000 + i * 2000,
                wage_unit="Year",
                fiscal_year=2024,
                case_status="Certified",
                source="lca",
            )
        )
    # Too few for CA overlay
    for i in range(5):
        db.add(
            LcaFiling(
                case_number=f"I-2024-CA-{i}",
                wage_line=1,
                job_title="Software Developer",
                job_title_norm="software developer",
                soc_code="15-1252",
                employer=f"CA Co {i}",
                worksite_city="San Jose",
                worksite_state="CA",
                wage_annual=180000,
                wage_unit="Year",
                fiscal_year=2024,
                case_status="Certified",
                source="lca",
            )
        )
    db.commit()
    return db


# Ensure pysqlite is available via SQLAlchemy default
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://salary:salary@localhost:5432/salary")
