from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import get_db
from app.main import app


def test_compare_endpoint(seeded_db: Session):
    def override_get_db():
        try:
            yield seeded_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    try:
        r = client.post(
            "/v1/compare",
            json={
                "soc_code": "15-1252",
                "job_title": "Software Developer",
                "area_code": "42660",
                "state": "WA",
                "current_salary": 100000,
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert body["verdict"] == "under"
        assert body["geo_level_used"] == "metro"
        assert body["oews"]["pct50"] == 140000
        assert body["lca"]["n"] >= 30

        meta = client.get("/v1/meta")
        assert meta.status_code == 200
        assert meta.json()["oews_rows"] >= 3
    finally:
        app.dependency_overrides.clear()
