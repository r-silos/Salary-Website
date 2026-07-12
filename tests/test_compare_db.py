from sqlalchemy.orm import Session

from app.compare import compare_salary
from app.config import settings
from app.schemas import CompareRequest


def test_verdict_under_metro(seeded_db: Session):
    resp = compare_salary(
        seeded_db,
        CompareRequest(
            soc_code="15-1252",
            job_title="Software Developer",
            area_code="42660",
            state="WA",
            current_salary=100000,
        ),
    )
    assert resp.verdict == "under"
    assert resp.geo_level_used == "metro"
    assert resp.oews is not None
    assert resp.oews.pct25 == 120000
    assert resp.lca is not None
    assert resp.lca.n is not None and resp.lca.n >= settings.lca_min_sample


def test_verdict_in_range(seeded_db: Session):
    resp = compare_salary(
        seeded_db,
        CompareRequest(soc_code="15-1252", area_code="42660", state="WA", current_salary=145000),
    )
    assert resp.verdict == "in_range"


def test_verdict_over(seeded_db: Session):
    resp = compare_salary(
        seeded_db,
        CompareRequest(soc_code="15-1252", area_code="42660", state="WA", current_salary=200000),
    )
    assert resp.verdict == "over"


def test_geo_fallback_to_state(seeded_db: Session):
    resp = compare_salary(
        seeded_db,
        CompareRequest(soc_code="15-1252", area_code="99999", state="WA", current_salary=145000),
    )
    assert resp.geo_level_used == "state"
    assert any("fell back" in c.lower() for c in resp.caveats)


def test_geo_fallback_to_national(seeded_db: Session):
    resp = compare_salary(
        seeded_db,
        CompareRequest(soc_code="15-1252", area_code="99999", state="TX", current_salary=145000),
    )
    assert resp.geo_level_used == "national"


def test_lca_threshold_omits_small_sample(seeded_db: Session, monkeypatch):
    monkeypatch.setattr(settings, "lca_min_sample", 30)
    resp = compare_salary(
        seeded_db,
        CompareRequest(
            soc_code="15-1252",
            job_title="Software Developer",
            state="CA",
            current_salary=180000,
        ),
    )
    assert resp.lca is None
    assert any("LCA overlay omitted" in c for c in resp.caveats)
