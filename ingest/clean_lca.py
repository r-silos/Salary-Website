"""Clean LCA rows already loaded into Postgres.

- Drop synthetic fixture employers / short I-2024 fixture case numbers
- Drop Certified-Withdrawn (keep Certified only)
- Drop wages outside configured caps
- Backfill fiscal_year from case number
"""

from __future__ import annotations

import argparse
import sys

from sqlalchemy import delete, func, or_, select, update

from app.compare import infer_fiscal_year
from app.config import settings
from app.models import LcaFiling
from ingest.common import session


FIXTURE_EMPLOYER_PREFIXES = (
    "Employer ",
    "Hourly Co ",
    "Data Co ",
    "CA Co ",
    "Denied Co",
)


def clean_lca(*, default_fiscal_year: int | None = None, dry_run: bool = False) -> dict[str, int]:
    from sqlalchemy import text

    stats = {
        "before": 0,
        "deleted_fixtures": 0,
        "deleted_withdrawn": 0,
        "deleted_wage_outliers": 0,
        "fy_backfilled": 0,
        "after": 0,
    }
    with session() as db:
        stats["before"] = db.scalar(select(func.count()).select_from(LcaFiling)) or 0

        fixture_clause = or_(
            *[LcaFiling.employer.startswith(p) for p in FIXTURE_EMPLOYER_PREFIXES],
            text("case_number ~ '^I-2024-[0-9]{1,6}$'"),
        )
        fixture_count = db.scalar(select(func.count()).select_from(LcaFiling).where(fixture_clause)) or 0
        stats["deleted_fixtures"] = fixture_count

        withdrawn_clause = LcaFiling.case_status.ilike("%withdrawn%")
        withdrawn_count = db.scalar(select(func.count()).select_from(LcaFiling).where(withdrawn_clause)) or 0
        stats["deleted_withdrawn"] = withdrawn_count

        outlier_clause = or_(
            LcaFiling.wage_annual < settings.lca_wage_min,
            LcaFiling.wage_annual > settings.lca_wage_max,
        )
        outlier_count = db.scalar(select(func.count()).select_from(LcaFiling).where(outlier_clause)) or 0
        stats["deleted_wage_outliers"] = outlier_count

        if dry_run:
            null_fy = db.scalar(
                select(func.count()).select_from(LcaFiling).where(LcaFiling.fiscal_year.is_(None))
            ) or 0
            # Approximate: most null FY rows will backfill from case number
            stats["fy_backfilled"] = null_fy
            stats["after"] = (
                stats["before"]
                - stats["deleted_fixtures"]
                - stats["deleted_withdrawn"]
                - stats["deleted_wage_outliers"]
            )
            db.rollback()
            return stats

        if fixture_count:
            db.execute(delete(LcaFiling).where(fixture_clause))
        if withdrawn_count:
            db.execute(delete(LcaFiling).where(withdrawn_clause))
        if outlier_count:
            db.execute(delete(LcaFiling).where(outlier_clause))

        rows = db.scalars(select(LcaFiling).where(LcaFiling.fiscal_year.is_(None))).all()
        backfilled = 0
        for row in rows:
            fy = infer_fiscal_year(row.case_number) or default_fiscal_year
            if fy is not None:
                row.fiscal_year = fy
                backfilled += 1
        stats["fy_backfilled"] = backfilled

        db.execute(
            update(LcaFiling)
            .where(LcaFiling.case_status.ilike("certified"))
            .values(case_status="Certified")
        )
        db.commit()
        stats["after"] = db.scalar(select(func.count()).select_from(LcaFiling)) or 0
    return stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Clean LCA filings in the database")
    parser.add_argument("--dry-run", action="store_true", help="Report counts without writing")
    parser.add_argument(
        "--fiscal-year",
        type=int,
        default=None,
        help="Fallback FY when case number cannot be parsed",
    )
    args = parser.parse_args(argv)
    stats = clean_lca(default_fiscal_year=args.fiscal_year, dry_run=args.dry_run)
    label = "DRY-RUN " if args.dry_run else ""
    print(f"{label}LCA clean:")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
