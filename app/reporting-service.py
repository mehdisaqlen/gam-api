# reporting_service.py
from datetime import date
from typing import List, Optional

from .reporting_schemas import (
    SummaryMetrics,
    LocationBreakdownItem,
    TimeseriesPoint,
)


async def fetch_summary_metrics(
    start_date: date,
    end_date: date,
    network_code: Optional[str] = None,
) -> SummaryMetrics:
    """
    TODO: Replace with real query (GAM API / DB).
    """
    # Example dummy calculation
    impressions = 100_000
    clicks = 1_200
    revenue = 250.0

    ctr = (clicks / impressions * 100) if impressions else 0.0
    ecpm = (revenue / impressions * 1000) if impressions else 0.0

    return SummaryMetrics(
        impressions=impressions,
        clicks=clicks,
        ctr=round(ctr, 3),
        revenue=round(revenue, 2),
        ecpm=round(ecpm, 3),
    )


async def fetch_location_breakdown(
    start_date: date,
    end_date: date,
    network_code: Optional[str] = None,
) -> List[LocationBreakdownItem]:
    """
    TODO: Replace with real query grouped by country/region.
    """
    return [
        LocationBreakdownItem(
            country="US",
            region=None,
            impressions=40_000,
            clicks=500,
            ctr=round(500 / 40_000 * 100, 3),
            revenue=120.0,
            ecpm=round(120 / 40_000 * 1000, 3),
        ),
        LocationBreakdownItem(
            country="PK",
            region=None,
            impressions=30_000,
            clicks=400,
            ctr=round(400 / 30_000 * 100, 3),
            revenue=60.0,
            ecpm=round(60 / 30_000 * 1000, 3),
        ),
    ]


async def fetch_timeseries(
    start_date: date,
    end_date: date,
    network_code: Optional[str] = None,
) -> List[TimeseriesPoint]:
    """
    TODO: Replace with real daily timeseries query.
    """
    # Example: one point per day
    days = (end_date - start_date).days + 1
    points: list[TimeseriesPoint] = []
    for i in range(days):
        current = start_date + timedelta(days=i)
        impressions = 5_000 + i * 200
        clicks = 50 + i * 3
        revenue = 10 + i * 0.5
        ctr = (clicks / impressions * 100) if impressions else 0.0
        ecpm = (revenue / impressions * 1000) if impressions else 0.0

        points.append(
            TimeseriesPoint(
                date=current,
                impressions=impressions,
                clicks=clicks,
                ctr=round(ctr, 3),
                revenue=round(revenue, 2),
                ecpm=round(ecpm, 3),
            )
        )

    return points
