from typing import Literal

from pydantic import BaseModel, Field


class CompareRequest(BaseModel):
    soc_code: str = Field(..., examples=["15-1252"])
    job_title: str | None = Field(None, examples=["Software Developer"])
    area_code: str | None = Field(None, examples=["42660"])
    state: str | None = Field(None, min_length=2, max_length=2, examples=["WA"])
    current_salary: float = Field(..., gt=0, examples=[145000])


class WageRange(BaseModel):
    pct25: float | None = None
    pct50: float | None = None
    pct75: float | None = None
    mean: float | None = None
    n: int | None = None
    source: str
    occupation_title: str | None = None
    area_name: str | None = None
    area_type: str | None = None
    year: int | None = None


class CompareResponse(BaseModel):
    verdict: Literal["under", "in_range", "over", "unknown"]
    current_salary: float
    geo_level_used: str | None
    oews: WageRange | None
    lca: WageRange | None
    caveats: list[str]


class MetaResponse(BaseModel):
    oews_rows: int
    lca_rows: int
    oews_years: list[int]
    lca_fiscal_years: list[int]
    lca_min_sample: int
