# app/main.py
import os
from datetime import date, timedelta
from enum import Enum
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from googleads import errors as googleads_errors

from .gam import build_client, grant_admin_for_email
from .gam import list_accessible_networks


app = FastAPI(title="GAM Access API", version="1.0.0")

# =========================
# CORS CONFIG
# =========================

# You can override this in Render env as: CORS_ORIGINS="http://localhost:3000,https://your-frontend.com"
_raw_origins = os.getenv("CORS_ORIGINS", "")
if _raw_origins.strip():
    origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]
else:
    # Safe defaults for local dev
    origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# Existing access endpoints
# =========================

class GrantRequest(BaseModel):
    email: EmailStr = Field(..., description="Email to grant Administrator access")
    networks: Optional[List[str]] = Field(
        default=None,
        description="List of network codes (defaults to GAM_NETWORKS env if omitted)",
    )


class GrantResult(BaseModel):
    network: str
    status: str
    userId: Optional[int] = None
    roleId: Optional[int] = None
    error: Optional[str] = None


class GrantResponse(BaseModel):
    email: EmailStr
    results: List[GrantResult]


def _env_networks() -> List[str]:
    raw = os.getenv("GAM_NETWORKS", "")
    return [n.strip() for n in raw.split(",") if n.strip()]


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.post("/grant-access", response_model=GrantResponse)
def grant_access(body: GrantRequest):
    networks = body.networks or _env_networks()
    if not networks:
        raise HTTPException(
            status_code=400,
            detail="No networks provided and GAM_NETWORKS env not set.",
        )

    results: List[GrantResult] = []

    for code in networks:
        try:
            client = build_client(network_code=code)
            out = grant_admin_for_email(client, body.email)
            results.append(GrantResult(network=code, **out))
        except googleads_errors.GoogleAdsServerFault as e:
            results.append(
                GrantResult(network=code, status="error", error=str(e))
            )
        except Exception as e:
            results.append(
                GrantResult(network=code, status="error", error=str(e))
            )

    return GrantResponse(email=body.email, results=results)


@app.get("/networks")
def get_networks():
    try:
        return {"networks": list_accessible_networks()}
    except Exception as e:
        return {"error": str(e)}


# =========================
# Reporting models
# =========================

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
        return today - timedelta(days(29)), today  # <- BUG: fix below

    # custom
    if not start_date or not end_date:
        raise ValueError("start_date and end_date are required for custom range")
    if start_date > end_date:
        raise ValueError("start_date cannot be after end_date")
    return start_date, end_date


class SummaryMetrics(BaseModel):
    impressions: int = 0
    clicks: int = 0
    ctr: float = 0.0        # percent, for example 1.23
    revenue: float = 0.0    # default currency
    ecpm: float = 0.0       # revenue per 1000 impressions


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


# =========================
# Reporting data functions
# =========================

def fetch_summary_metrics(
    start_date: date,
    end_date: date,
    network_code: Optional[str] = None,
) -> SummaryMetrics:
    """
    TODO: Replace with real GAM reporting query.

    You probably want:
    - dimensions: DATE (if you aggregate client side) and maybe COUNTRY_NAME
    - metrics: AD_EXCHANGE_LINE_ITEM_LEVEL_IMPRESSIONS,
               AD_EXCHANGE_LINE_ITEM_LEVEL_CLICKS,
               AD_EXCHANGE_LINE_ITEM_LEVEL_REVENUE
    """
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


def fetch_location_breakdown(
    start_date: date,
    end_date: date,
    network_code: Optional[str] = None,
) -> List[LocationBreakdownItem]:
    """
    TODO: Replace with real GAM query grouped by country / region.
    """
    items: List[LocationBreakdownItem] = []

    # Example data
    us_impressions = 40_000
    us_clicks = 500
    us_revenue = 120.0

    pk_impressions = 30_000
    pk_clicks = 400
    pk_revenue = 60.0

    items.append(
        LocationBreakdownItem(
            country="US",
            region=None,
            impressions=us_impressions,
            clicks=us_clicks,
            ctr=round(us_clicks / us_impressions * 100, 3)
            if us_impressions
            else 0.0,
            revenue=round(us_revenue, 2),
            ecpm=round(us_revenue / us_impressions * 1000, 3)
            if us_impressions
            else 0.0,
        )
    )

    items.append(
        LocationBreakdownItem(
            country="PK",
            region=None,
            impressions=pk_impressions,
            clicks=pk_clicks,
            ctr=round(pk_clicks / pk_impressions * 100, 3)
            if pk_impressions
            else 0.0,
            revenue=round(pk_revenue, 2),
            ecpm=round(pk_revenue / pk_impressions * 1000, 3)
            if pk_impressions
            else 0.0,
        )
    )

    return items


def fetch_timeseries(
    start_date: date,
    end_date: date,
    network_code: Optional[str] = None,
) -> List[TimeseriesPoint]:
    """
    TODO: Replace with real GAM daily timeseries query.
    """
    days = (end_date - start_date).days + 1
    points: List[TimeseriesPoint] = []

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


def _resolve_dates_or_400(
    range_: DateRange,
    start_date: Optional[date],
    end_date: Optional[date],
) -> tuple[date, date]:
    try:
        return resolve_date_range(range_, start_date, end_date)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =========================
# Reporting endpoints
# =========================

@app.get("/reports/summary", response_model=SummaryResponse)
def get_summary_report(
    range: DateRange = Query(default=DateRange.today),
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None),
    network_code: Optional[str] = Query(default=None),
):
    """
    Aggregate metrics: impressions, clicks, ctr, revenue, ecpm
    for the given date range and optional network.
    """
    start, end = _resolve_dates_or_400(range, start_date, end_date)
    metrics = fetch_summary_metrics(start, end, network_code)

    return SummaryResponse(
        range=range,
        start_date=start,
        end_date=end,
        network_code=network_code,
        metrics=metrics,
    )


@app.get("/reports/locations", response_model=LocationResponse)
def get_location_report(
    range: DateRange = Query(default=DateRange.today),
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None),
    network_code: Optional[str] = Query(default=None),
):
    """
    Breakdown by country / region with revenue, ecpm, ctr.
    """
    start, end = _resolve_dates_or_400(range, start_date, end_date)
    locations = fetch_location_breakdown(start, end, network_code)

    return LocationResponse(
        range=range,
        start_date=start,
        end_date=end,
        network_code=network_code,
        locations=locations,
    )


@app.get("/reports/timeseries", response_model=TimeseriesResponse)
def get_timeseries_report(
    range: DateRange = Query(default=DateRange.last_7_days),
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None),
    network_code: Optional[str] = Query(default=None),
):
    """
    Daily timeseries for charts: revenue, ecpm, ctr, etc.
    """
    start, end = _resolve_dates_or_400(range, start_date, end_date)
    points = fetch_timeseries(start, end, network_code)

    return TimeseriesResponse(
        range=range,
        start_date=start,
        end_date=end,
        network_code=network_code,
        points=points,
    )
