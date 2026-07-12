from app.compare import (
    annualize_wage,
    clamp_annual_wage,
    infer_fiscal_year,
    normalize_soc,
    normalize_title,
    verdict_from_band,
)


def test_annualize_year():
    assert annualize_wage(150000, "Year") == 150000


def test_annualize_hour():
    assert annualize_wage(100, "Hour") == 208000


def test_annualize_rejects_mislabeled_year():
    assert annualize_wage(80, "Year") is None


def test_annualize_rejects_mislabeled_hour():
    assert annualize_wage(150000, "Hour") is None


def test_annualize_week():
    assert annualize_wage(2000, "Week") == 104000


def test_annualize_month():
    assert annualize_wage(10000, "Month") == 120000


def test_annualize_invalid():
    assert annualize_wage(0, "Year") is None
    assert annualize_wage(100, "decade") is None


def test_clamp_annual_wage():
    assert clamp_annual_wage(150000) == 150000
    assert clamp_annual_wage(5000) is None
    assert clamp_annual_wage(2_000_000) is None


def test_infer_fiscal_year_modern_and_legacy():
    assert infer_fiscal_year("I-200-25123-456789") == 2025
    assert infer_fiscal_year("I-200-26-001") == 2026
    assert infer_fiscal_year("I-2024-100000") == 2024
    assert infer_fiscal_year("I-200-25-001", explicit=2025) == 2025


def test_verdict_under():
    assert verdict_from_band(100000, 120000, 170000) == "under"


def test_verdict_in_range():
    assert verdict_from_band(145000, 120000, 170000) == "in_range"


def test_verdict_over():
    assert verdict_from_band(200000, 120000, 170000) == "over"


def test_verdict_unknown_missing_band():
    assert verdict_from_band(145000, None, 170000) == "unknown"


def test_normalize_soc():
    assert normalize_soc("15-1252.00") == "15-1252"
    assert normalize_soc("151252") == "15-1252"


def test_normalize_title():
    assert normalize_title("  Software   Developer ") == "software developer"
