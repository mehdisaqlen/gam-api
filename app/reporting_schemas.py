# reporting_schemas.py
from datetime import date, timedelta
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class DateRange(str, Enum):
    today = "today"
    yesterday = "yesterday"
    last_7_days = "last_7_days"
    last_30_days = "last_30_days"
    custom = "custom"


def resolve_date_range(
    range_: DateRange,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> tuple[date, date]:
    today = date.today()

    if range_ == DateRange.today:
        return today, today
    if range_ == DateRange.yesterday:
        y = today - timedelta(days=1)
        return y, y
    if range_ == DateRange.last_7_days:
        return today - timedelta(days=6), today
    if range_ == DateRange.last_30_days:
        return today - timedelta(days=29), today

    # custom
    if not start_date or not end_date:
        raise ValueError("start_date and end_date are required for custom range")
    if start_date > end_date:
        raise ValueError("start_date cannot be after end_date")
    return start_date, end_date


class SummaryMetrics(BaseModel):
    impressions: int = 0
    clicks: int = 0
    ctr: float = 0.0         # percent, e.g. 1.23
    revenue: float = 0.0     # in your default currency
    ecpm: float = 0.0        # revenue per 1000 impressions


class LocationBreakdownItem(BaseModel):
    country: str
    region: Optional[str] = None
    impressions: int
    clicks: int
    ctr: float
    revenue: float
    ecpm: float


class TimeseriesPoint(BaseModel):
    date: date
    impressions: int
    clicks: int
    ctr: float
    revenue: float
    ecpm: float


class SummaryResponse(BaseModel):
    range: DateRange
    start_date: date
    end_date: date
    network_code: Optional[str] = None
    metrics: SummaryMetrics


class LocationResponse(BaseModel):
    range: DateRange
    start_date: date
    end_date: date
    network_code: Optional[str] = None
    locations: List[LocationBreakdownItem]


class TimeseriesResponse(BaseModel):
    range: DateRange
    start_date: date
    end_date: date
    network_code: Optional[str] = None
    points: List[TimeseriesPoint]
