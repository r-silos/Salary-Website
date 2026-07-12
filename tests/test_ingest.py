from pathlib import Path

from ingest.lca import transform as transform_lca
from ingest.oews import transform as transform_oews
from ingest.common import read_table


FIXTURES = Path(__file__).resolve().parents[1] / "data" / "fixtures"


def test_oews_fixture_transform():
    df = read_table(FIXTURES / "oews_sample.csv")
    rows = transform_oews(df)
    assert len(rows) >= 20
    seattle = next(r for r in rows if r["area_code"] == "42660" and r["soc_code"] == "15-1252")
    assert seattle["area_type"] == "metro"
    assert seattle["pct50"] == 140000


def test_lca_fixture_transform_filters_denied_and_annualizes():
    df = read_table(FIXTURES / "lca_sample.csv")
    rows = transform_lca(df)
    assert all(r["case_status"] == "Certified" for r in rows)
    assert not any(r["case_number"] == "I-2024-999999" for r in rows)
    hourly = next(r for r in rows if r["case_number"] == "I-2024-200000")
    assert hourly["wage_annual"] == 70 * 2080
    assert hourly["fiscal_year"] == 2024
    wa_sw = [r for r in rows if r["worksite_state"] == "WA" and r["soc_code"] == "15-1252"]
    assert len(wa_sw) >= 30
