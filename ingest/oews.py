"""Ingest BLS OEWS wage estimates from CSV/XLSX.

Expected columns (case-insensitive; aliases supported):
  soc_code / OCC_CODE
  occupation_title / OCC_TITLE
  area_code / AREA
  area_name / AREA_TITLE
  area_type / AREA_TYPE  (metro|state|national) — inferred if missing
  year / YEAR
  mean_wage / A_MEAN
  pct10 / A_PCT10, pct25 / A_PCT25, pct50 / A_MEDIAN, pct75 / A_PCT75, pct90 / A_PCT90
  employment / TOT_EMP
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from ingest.common import ensure_tables, normalize_soc, read_table, session, upsert_oews

COLUMN_MAP = {
    "soc_code": ["soc_code", "occ_code", "OCC_CODE"],
    "occupation_title": ["occupation_title", "occ_title", "OCC_TITLE"],
    "area_code": ["area_code", "area", "AREA"],
    "area_name": ["area_name", "area_title", "AREA_TITLE"],
    "area_type": ["area_type", "AREA_TYPE"],
    "year": ["year", "YEAR"],
    "mean_wage": ["mean_wage", "a_mean", "A_MEAN"],
    "pct10": ["pct10", "a_pct10", "A_PCT10"],
    "pct25": ["pct25", "a_pct25", "A_PCT25"],
    "pct50": ["pct50", "a_median", "A_MEDIAN", "a_pct50", "A_PCT50"],
    "pct75": ["pct75", "a_pct75", "A_PCT75"],
    "pct90": ["pct90", "a_pct90", "A_PCT90"],
    "employment": ["employment", "tot_emp", "TOT_EMP"],
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


def _infer_area_type(area_code: str, area_name: str, explicit: str | None) -> str:
    """Map BLS AREA_TYPE codes / labels to metro|state|national."""
    if explicit:
        e = str(explicit).strip().lower()
        # Excel often yields "4.0"
        if e.endswith(".0"):
            e = e[:-2]
        bls_code_map = {
            "1": "national",
            "2": "state",
            "3": "metro",
            "4": "metro",  # MSA / nonmetro area files
            "metro": "metro",
            "metropolitan": "metro",
            "msa": "metro",
            "state": "state",
            "national": "national",
            "nation": "national",
            "us": "national",
        }
        if e in bls_code_map:
            return bls_code_map[e]
    code = (area_code or "").strip().upper()
    name = (area_name or "").strip().lower()
    if code in {"99", "00000", "NATIONAL"} or name in {"united states", "national", "u.s."}:
        return "national"
    if code.startswith("ST-") or (len(code) == 2 and code.isalpha()):
        return "state"
    return "metro"


def transform(df: pd.DataFrame, default_year: int | None = None) -> list[dict]:
    cols = {key: _pick(df, aliases) for key, aliases in COLUMN_MAP.items()}
    required = ["soc_code", "occupation_title", "area_code", "area_name"]
    missing = [k for k in required if cols[k] is None]
    if missing:
        raise ValueError(f"Missing required columns for {missing}. Found: {list(df.columns)}")

    rows: list[dict] = []
    for _, r in df.iterrows():
        soc = normalize_soc(str(r[cols["soc_code"]]))
        if not soc or soc.lower() in {"nan", "none"}:
            continue
        area_code = str(r[cols["area_code"]]).strip()
        area_name = str(r[cols["area_name"]]).strip()
        explicit_type = str(r[cols["area_type"]]) if cols["area_type"] else None
        year_val = r[cols["year"]] if cols["year"] else default_year
        if year_val is None or (isinstance(year_val, float) and pd.isna(year_val)):
            raise ValueError("year column missing and --year not provided")
        year = int(float(year_val))

        rows.append(
            {
                "soc_code": soc,
                "occupation_title": str(r[cols["occupation_title"]]).strip(),
                "area_code": area_code,
                "area_name": area_name,
                "area_type": _infer_area_type(area_code, area_name, explicit_type),
                "year": year,
                "mean_wage": _to_float(r[cols["mean_wage"]]) if cols["mean_wage"] else None,
                "pct10": _to_float(r[cols["pct10"]]) if cols["pct10"] else None,
                "pct25": _to_float(r[cols["pct25"]]) if cols["pct25"] else None,
                "pct50": _to_float(r[cols["pct50"]]) if cols["pct50"] else None,
                "pct75": _to_float(r[cols["pct75"]]) if cols["pct75"] else None,
                "pct90": _to_float(r[cols["pct90"]]) if cols["pct90"] else None,
                "employment": _to_float(r[cols["employment"]]) if cols["employment"] else None,
                "source": "oews",
            }
        )
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest OEWS wage estimates")
    parser.add_argument("path", type=Path, help="Path to OEWS CSV/XLSX")
    parser.add_argument("--year", type=int, default=None, help="Default year if file has no YEAR column")
    args = parser.parse_args(argv)

    if not args.path.exists():
        print(f"File not found: {args.path}", file=sys.stderr)
        return 1

    ensure_tables()
    df = read_table(args.path)
    rows = transform(df, default_year=args.year)
    with session() as db:
        n = upsert_oews(db, rows)
    print(f"Upserted {n} OEWS rows from {args.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
