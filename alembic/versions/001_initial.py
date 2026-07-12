"""create oews_estimates and lca_filings

Revision ID: 001_initial
Revises:
Create Date: 2026-07-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "oews_estimates",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("soc_code", sa.String(length=16), nullable=False),
        sa.Column("occupation_title", sa.String(length=255), nullable=False),
        sa.Column("area_code", sa.String(length=16), nullable=False),
        sa.Column("area_name", sa.String(length=255), nullable=False),
        sa.Column("area_type", sa.String(length=32), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("mean_wage", sa.Float(), nullable=True),
        sa.Column("pct10", sa.Float(), nullable=True),
        sa.Column("pct25", sa.Float(), nullable=True),
        sa.Column("pct50", sa.Float(), nullable=True),
        sa.Column("pct75", sa.Float(), nullable=True),
        sa.Column("pct90", sa.Float(), nullable=True),
        sa.Column("employment", sa.Float(), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("soc_code", "area_code", "year", name="uq_oews_soc_area_year"),
    )
    op.create_index("ix_oews_soc_area", "oews_estimates", ["soc_code", "area_code"])

    op.create_table(
        "lca_filings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("case_number", sa.String(length=64), nullable=False),
        sa.Column("wage_line", sa.Integer(), nullable=False),
        sa.Column("job_title", sa.String(length=255), nullable=False),
        sa.Column("job_title_norm", sa.String(length=255), nullable=False),
        sa.Column("soc_code", sa.String(length=16), nullable=True),
        sa.Column("employer", sa.String(length=255), nullable=True),
        sa.Column("worksite_city", sa.String(length=128), nullable=True),
        sa.Column("worksite_state", sa.String(length=8), nullable=False),
        sa.Column("wage_annual", sa.Float(), nullable=False),
        sa.Column("wage_unit", sa.String(length=32), nullable=False),
        sa.Column("fiscal_year", sa.Integer(), nullable=True),
        sa.Column("case_status", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("case_number", "wage_line", name="uq_lca_case_wage_line"),
    )
    op.create_index("ix_lca_state_title", "lca_filings", ["worksite_state", "job_title_norm"])
    op.create_index("ix_lca_soc_state", "lca_filings", ["soc_code", "worksite_state"])


def downgrade() -> None:
    op.drop_index("ix_lca_soc_state", table_name="lca_filings")
    op.drop_index("ix_lca_state_title", table_name="lca_filings")
    op.drop_table("lca_filings")
    op.drop_index("ix_oews_soc_area", table_name="oews_estimates")
    op.drop_table("oews_estimates")
