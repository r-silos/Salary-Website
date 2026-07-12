from __future__ import annotations

import re

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import LcaFiling, OewsEstimate
from app.schemas import CompareRequest, CompareResponse, WageRange


def normalize_title(title: str) -> str:
    return re.sub(r"\s+", " ", title.strip().lower())


def normalize_soc(soc: str) -> str:
    """Normalize SOC codes like 151252 / 15-1252.00 -> 15-1252."""
    digits = re.sub(r"[^0-9]", "", soc)
    if len(digits) >= 6:
        return f"{digits[:2]}-{digits[2:6]}"
    cleaned = soc.strip()
    if re.fullmatch(r"\d{2}-\d{4}(\.\d+)?", cleaned):
        return cleaned[:7]
    return cleaned


def annualize_wage(amount: float, unit: str) -> float | None:
    if amount is None or amount <= 0:
        return None
    u = (unit or "").strip().lower()
    if u in {"year", "yr", "annual", "annually"}:
        # Year rates below $1k are almost certainly mislabeled hourly/other.
        if amount < 1000:
            return None
        return float(amount)
    if u in {"hour", "hr", "hourly"}:
        # Hourly rates above $1k are almost certainly mislabeled annual.
        if amount > 1000:
            return None
        return float(amount) * 2080
    if u in {"week", "wk", "weekly"}:
        return float(amount) * 52
    if u in {"bi-weekly", "biweekly", "bi_weekly"}:
        return float(amount) * 26
    if u in {"month", "mo", "monthly"}:
        return float(amount) * 12
    return None


def clamp_annual_wage(annual: float | None, *, lo: float | None = None, hi: float | None = None) -> float | None:
    if annual is None:
        return None
    min_w = settings.lca_wage_min if lo is None else lo
    max_w = settings.lca_wage_max if hi is None else hi
    if annual < min_w or annual > max_w:
        return None
    return annual


def infer_fiscal_year(case_number: str, explicit=None) -> int | None:
    """Infer FY from explicit value or DOL case number patterns."""
    if explicit is not None:
        try:
            year = int(float(explicit))
            if 1990 <= year <= 2100:
                return year
        except (TypeError, ValueError):
            pass

    cn = str(case_number).strip()
    # Modern DOL: I-200-25... or I-200-25101-... (YY or YY+julian after form code)
    m = re.match(r"^I-\d{3}-(\d{2})", cn)
    if m:
        yy = int(m.group(1))
        return 2000 + yy if yy < 100 else yy
    # Legacy / fixture style: I-2024-...
    m = re.search(r"I-(\d{4})-", cn)
    if m:
        return int(m.group(1))
    return None


def winsorize(values: list[float], low_pct: float = 1.0, high_pct: float = 99.0) -> list[float]:
    if len(values) < 20:
        return values
    lo = _percentile(values, low_pct)
    hi = _percentile(values, high_pct)
    return [min(max(v, lo), hi) for v in values]


def verdict_from_band(salary: float, pct25: float | None, pct75: float | None) -> str:
    if pct25 is None or pct75 is None:
        return "unknown"
    if salary < pct25:
        return "under"
    if salary > pct75:
        return "over"
    return "in_range"


def _percentile(values: list[float], p: float) -> float:
    if not values:
        raise ValueError("empty")
    if len(values) == 1:
        return values[0]
    # statistics.quantiles with n=100 gives cut points; simpler linear rank
    ordered = sorted(values)
    k = (len(ordered) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(ordered) - 1)
    if f == c:
        return ordered[f]
    return ordered[f] + (ordered[c] - ordered[f]) * (k - f)


def resolve_oews(db: Session, soc_code: str, area_code: str | None, state: str | None) -> OewsEstimate | None:
    soc = normalize_soc(soc_code)
    latest_year = db.scalar(select(func.max(OewsEstimate.year)).where(OewsEstimate.soc_code == soc))
    if latest_year is None:
        return None

    base = select(OewsEstimate).where(OewsEstimate.soc_code == soc, OewsEstimate.year == latest_year)

    if area_code:
        row = db.scalar(base.where(OewsEstimate.area_code == area_code, OewsEstimate.area_type == "metro"))
        if row:
            return row

    if state:
        # State area codes in fixtures use ST-{STATE}; also match area_name containing state abbrev
        row = db.scalar(
            base.where(
                OewsEstimate.area_type == "state",
                (OewsEstimate.area_code == f"ST-{state.upper()}") | (OewsEstimate.area_code == state.upper()),
            )
        )
        if row:
            return row

    return db.scalar(base.where(OewsEstimate.area_type == "national"))


def _lca_base_filters():
    return (
        LcaFiling.case_status == "Certified",
        LcaFiling.wage_annual.is_not(None),
        LcaFiling.wage_annual >= settings.lca_wage_min,
        LcaFiling.wage_annual <= settings.lca_wage_max,
    )


def resolve_lca(
    db: Session,
    *,
    soc_code: str,
    job_title: str | None,
    state: str | None,
    min_sample: int,
) -> WageRange | None:
    """Prefer SOC match; fall back to title only if SOC cohort is too small."""
    soc = normalize_soc(soc_code)

    def _fetch(extra_clauses) -> list[float]:
        stmt = select(LcaFiling.wage_annual).where(*_lca_base_filters(), *extra_clauses)
        if state:
            stmt = stmt.where(LcaFiling.worksite_state == state.upper())
        return list(db.scalars(stmt))

    wages = _fetch([LcaFiling.soc_code == soc])
    matched_on = "soc"

    if len(wages) < min_sample and job_title:
        title_norm = normalize_title(job_title)
        # Require SOC null-or-same to avoid pulling unrelated occupations by title alone.
        title_wages = _fetch(
            [
                LcaFiling.job_title_norm.contains(title_norm),
                (LcaFiling.soc_code.is_(None)) | (LcaFiling.soc_code == soc),
            ]
        )
        if len(title_wages) > len(wages):
            wages = title_wages
            matched_on = "title"

    if len(wages) < min_sample:
        return None

    trimmed = winsorize(wages)
    return WageRange(
        pct25=_percentile(trimmed, 25),
        pct50=_percentile(trimmed, 50),
        pct75=_percentile(trimmed, 75),
        mean=sum(trimmed) / len(trimmed),
        n=len(wages),
        source=f"lca:{matched_on}",
    )


def compare_salary(db: Session, req: CompareRequest) -> CompareResponse:
    caveats: list[str] = []
    oews_row = resolve_oews(db, req.soc_code, req.area_code, req.state)

    oews_range: WageRange | None = None
    geo_level: str | None = None
    if oews_row is None:
        caveats.append("No OEWS estimate found for the given SOC/geography; verdict unknown.")
    else:
        geo_level = oews_row.area_type
        oews_range = WageRange(
            pct25=oews_row.pct25,
            pct50=oews_row.pct50,
            pct75=oews_row.pct75,
            mean=oews_row.mean_wage,
            n=int(oews_row.employment) if oews_row.employment is not None else None,
            source="oews",
            occupation_title=oews_row.occupation_title,
            area_name=oews_row.area_name,
            area_type=oews_row.area_type,
            year=oews_row.year,
        )
        if oews_row.pct25 is None or oews_row.pct75 is None:
            caveats.append("OEWS percentiles missing; verdict unknown (mean shown if available).")
        if req.area_code and oews_row.area_type != "metro":
            caveats.append(f"Metro area {req.area_code} not found; fell back to {oews_row.area_type}.")
        elif req.state and oews_row.area_type == "national":
            caveats.append("State estimate not found; fell back to national OEWS.")

    verdict = (
        verdict_from_band(req.current_salary, oews_range.pct25, oews_range.pct75)
        if oews_range
        else "unknown"
    )

    lca_range = resolve_lca(
        db,
        soc_code=req.soc_code,
        job_title=req.job_title,
        state=req.state,
        min_sample=settings.lca_min_sample,
    )
    if lca_range is None and (req.job_title or req.soc_code):
        caveats.append(
            f"LCA overlay omitted (fewer than {settings.lca_min_sample} matching certified filings)."
        )
    else:
        caveats.append("LCA range is informational only; verdict uses OEWS p25–p75.")

    return CompareResponse(
        verdict=verdict,  # type: ignore[arg-type]
        current_salary=req.current_salary,
        geo_level_used=geo_level,
        oews=oews_range,
        lca=lca_range,
        caveats=caveats,
    )
