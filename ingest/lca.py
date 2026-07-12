"""Ingest one DOL OFLC LCA disclosure file (CSV/XLSX).

Keeps Certified rows only, annualizes wages, applies wage caps, normalizes titles.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pandas as pd

from app.compare import annualize_wage, clamp_annual_wage, infer_fiscal_year, normalize_soc, normalize_title
from ingest.common import ensure_tables, read_table, session, upsert_lca

COLUMN_MAP = {
    "case_number": ["case_number", "CASE_NUMBER"],
    "job_title": ["job_title", "JOB_TITLE"],
    "soc_code": ["soc_code", "soc_code_1", "SOC_CODE", "SOC_CODE_1"],
    "employer": ["employer_name", "EMPLOYER_NAME", "employer"],
    "worksite_city": ["worksite_city", "WORKSITE_CITY", "worksite_city_1"],
    "worksite_state": ["worksite_state", "WORKSITE_STATE", "worksite_state_1"],
    "wage_from": ["wage_rate_of_pay_from", "WAGE_RATE_OF_PAY_FROM", "wage_from"],
    "wage_unit": ["wage_unit_of_pay", "WAGE_UNIT_OF_PAY", "wage_unit"],
    "case_status": ["case_status", "CASE_STATUS"],
    "fiscal_year": ["fiscal_year", "FISCAL_YEAR", "fy"],
}


def _pick(df: pd.DataFrame, names: list[str]) -> str | None:
    lower = {c.lower(): c for c in df.columns}
    for name in names:
        if name in df.columns:
            return name
        if name.lower() in lower:
            return lower[name.lower()]
    return None


def _to_float(val) -> float | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    s = str(val).strip().replace(",", "").replace("$", "")
    if s in {"", "*", "**", "#", "NA", "N/A", "-"}:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _fy_from_filename(path: Path | None) -> int | None:
    if path is None:
        return None
    m = re.search(r"FY(\d{4})", path.name, re.IGNORECASE)
    return int(m.group(1)) if m else None


def transform(
    df: pd.DataFrame,
    *,
    default_fiscal_year: int | None = None,
) -> list[dict]:
    cols = {key: _pick(df, aliases) for key, aliases in COLUMN_MAP.items()}
    required = ["case_number", "job_title", "worksite_state", "wage_from", "wage_unit", "case_status"]
    missing = [k for k in required if cols[k] is None]
    if missing:
        raise ValueError(f"Missing required columns for {missing}. Found: {list(df.columns)}")

    rows: list[dict] = []
    for _, r in df.iterrows():
        status = str(r[cols["case_status"]]).strip()
        if status.lower() != "certified":
            continue

        wage_raw = _to_float(r[cols["wage_from"]])
        unit = str(r[cols["wage_unit"]]).strip()
        annual = annualize_wage(wage_raw, unit) if wage_raw is not None else None
        annual = clamp_annual_wage(annual)
        if annual is None:
            continue

        case_number = str(r[cols["case_number"]]).strip()
        job_title = str(r[cols["job_title"]]).strip()
        state = str(r[cols["worksite_state"]]).strip().upper()
        if len(state) != 2:
            continue

        soc = None
        if cols["soc_code"] is not None and not pd.isna(r[cols["soc_code"]]):
            soc = normalize_soc(str(r[cols["soc_code"]]))

        explicit_fy = r[cols["fiscal_year"]] if cols["fiscal_year"] else None
        fiscal_year = infer_fiscal_year(case_number, explicit_fy) or default_fiscal_year

        rows.append(
            {
                "case_number": case_number,
                "wage_line": 1,
                "job_title": job_title,
                "job_title_norm": normalize_title(job_title),
                "soc_code": soc,
                "employer": str(r[cols["employer"]]).strip() if cols["employer"] else None,
                "worksite_city": str(r[cols["worksite_city"]]).strip() if cols["worksite_city"] else None,
                "worksite_state": state,
                "wage_annual": annual,
                "wage_unit": unit,
                "fiscal_year": fiscal_year,
                "case_status": "Certified",
                "source": "lca",
            }
        )
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest one LCA disclosure file")
    parser.add_argument("path", type=Path, help="Path to LCA CSV/XLSX")
    parser.add_argument(
        "--fiscal-year",
        type=int,
        default=None,
        help="Fallback fiscal year (also inferred from FY#### in filename)",
    )
    args = parser.parse_args(argv)

    if not args.path.exists():
        print(f"File not found: {args.path}", file=sys.stderr)
        return 1

    ensure_tables()
    df = read_table(args.path)
    default_fy = args.fiscal_year or _fy_from_filename(args.path)
    rows = transform(df, default_fiscal_year=default_fy)
    with session() as db:
        n = upsert_lca(db, rows)
    print(f"Upserted {n} LCA rows from {args.path}" + (f" (fy fallback={default_fy})" if default_fy else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
