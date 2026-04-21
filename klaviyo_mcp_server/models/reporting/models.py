from typing import Literal

from pydantic import BaseModel


class ReportPresetTimeframe(BaseModel):
    key: Literal[
        "last_12_months",
        "last_30_days",
        "last_365_days",
        "last_3_months",
        "last_7_days",
        "last_90_days",
        "last_month",
        "last_week",
        "last_year",
        "this_month",
        "this_week",
        "this_year",
        "today",
        "yesterday",
    ]


class ReportCustomTimeframe(BaseModel):
    start: str
    """e.g. 2022-11-08T00:00:00+00:00"""

    end: str
    """e.g. 2022-11-08T00:00:00+00:00"""


ReportTimeframe = ReportPresetTimeframe | ReportCustomTimeframe
