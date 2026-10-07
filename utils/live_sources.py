"""Live external-source adapters used by the dynamic ESG pipeline.

The legacy agents continue to use their local benchmark datasets. These
adapters provide JSON-safe payloads for the Phase 5 dynamic orchestrator and
keep external failures explicit so the orchestrator can select a fallback.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

import pandas as pd
import requests

from utils.config import COMPANIES
from utils.orchestrator import StageSpec


HTTP_TIMEOUT_SECONDS = 15
YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
GDELT_DOC_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _company(context: Dict[str, Any]) -> Dict[str, Any]:
    code = str(context.get("company_code", "")).upper()
    if code not in COMPANIES:
        raise ValueError(f"Unknown configured company code: {code}")
    return COMPANIES[code]


def _json_response(response: requests.Response, source: str) -> Any:
    response.raise_for_status()
    try:
        return response.json()
    except ValueError as exc:
        raise RuntimeError(f"{source} returned invalid JSON") from exc


def fetch_market_data(context: Dict[str, Any]) -> Dict[str, Any]:
    """Fetch daily Yahoo Finance chart data for the requested company."""
    company = _company(context)
    ticker = str(context.get("ticker") or company["ticker"])
    response = requests.get(
        YAHOO_CHART_URL.format(ticker=ticker),
        params={"range": "1y", "interval": "1d", "events": "history"},
        timeout=HTTP_TIMEOUT_SECONDS,
        headers={"User-Agent": "capstone-esg-research/1.0"},
    )
    payload = _json_response(response, "Yahoo Finance")
    result = payload.get("chart", {}).get("result")
    if not result:
        raise RuntimeError(f"Yahoo Finance returned no chart data for {ticker}")

    chart = result[0]
    timestamps = chart.get("timestamp", [])
    quote = chart.get("indicators", {}).get("quote", [{}])[0]
    closes = quote.get("close", [])
    records = [
        {"timestamp": timestamp, "close": close}
        for timestamp, close in zip(timestamps, closes)
        if close is not None
    ]
    if not records:
        raise RuntimeError(f"Yahoo Finance returned no closing prices for {ticker}")

    first = records[0]["close"]
    last = records[-1]["close"]
    return {
        "source": "Yahoo Finance",
        "source_url": YAHOO_CHART_URL.format(ticker=ticker),
        "retrieved_at": _utc_now(),
        "ticker": ticker,
        "records": records,
        "current_price": last,
        "period_return_pct": ((last - first) / first) * 100 if first else None,
    }


def fetch_esg_news(context: Dict[str, Any]) -> Dict[str, Any]:
    """Fetch recent ESG-related articles from GDELT DOC 2.0."""
    company = _company(context)
    query = f'"{company["full_name"]}" (ESG OR sustainability OR climate OR governance)'
    response = requests.get(
        GDELT_DOC_URL,
        params={
            "query": query,
            "mode": "artlist",
            "format": "json",
            "maxrecords": 50,
            "sort": "HybridRel",
            "timespan": "365d",
        },
        timeout=HTTP_TIMEOUT_SECONDS,
        headers={"User-Agent": "capstone-esg-research/1.0"},
    )
    payload = _json_response(response, "GDELT")
    articles = payload.get("articles", [])
    records = [
        {
            "title": article.get("title"),
            "url": article.get("url"),
            "domain": article.get("domain"),
            "language": article.get("language"),
            "published_at": article.get("seendate"),
        }
        for article in articles
        if article.get("url") and article.get("title")
    ]
    return {
        "source": "GDELT DOC 2.0",
        "source_url": GDELT_DOC_URL,
        "retrieved_at": _utc_now(),
        "query": query,
        "articles": records,
        "article_count": len(records),
    }


def _locations(context: Dict[str, Any]) -> List[str]:
    explicit = context.get("locations")
    if explicit:
        return [str(location) for location in explicit]
    company = _company(context)
    locations = [company["headquarters"]["city"]]
    locations.extend(office["city"] for office in company.get("major_offices", []))
    return list(dict.fromkeys(locations))


def fetch_environmental_context(context: Dict[str, Any]) -> Dict[str, Any]:
    """Geocode company locations and fetch current Open-Meteo AQI context."""
    locations = _locations(context)
    results = []
    for location in locations:
        geo_response = requests.get(
            GEOCODING_URL,
            params={"name": location, "count": 1, "language": "en", "format": "json"},
            timeout=HTTP_TIMEOUT_SECONDS,
            headers={"User-Agent": "capstone-esg-research/1.0"},
        )
        geo_payload = _json_response(geo_response, "Open-Meteo geocoding")
        matches = geo_payload.get("results", [])
        if not matches:
            raise RuntimeError(f"Could not geocode environmental location: {location}")
        match = matches[0]

        air_response = requests.get(
            AIR_QUALITY_URL,
            params={
                "latitude": match["latitude"],
                "longitude": match["longitude"],
                "current": "us_aqi,pm2_5,pm10",
                "timezone": "UTC",
            },
            timeout=HTTP_TIMEOUT_SECONDS,
            headers={"User-Agent": "capstone-esg-research/1.0"},
        )
        air_payload = _json_response(air_response, "Open-Meteo air quality")
        current = air_payload.get("current", {})
        results.append(
            {
                "requested_location": location,
                "resolved_location": match.get("name"),
                "latitude": match["latitude"],
                "longitude": match["longitude"],
                "observed_at": current.get("time"),
                "us_aqi": current.get("us_aqi"),
                "pm2_5": current.get("pm2_5"),
                "pm10": current.get("pm10"),
            }
        )

    return {
        "source": "Open-Meteo Air Quality",
        "source_url": AIR_QUALITY_URL,
        "retrieved_at": _utc_now(),
        "locations": results,
        "context_only": True,
        "score_impact": "none",
    }


def _records(frame: pd.DataFrame) -> List[Dict[str, Any]]:
    return frame.where(pd.notna(frame), None).to_dict(orient="records")


def fallback_market_data(context: Dict[str, Any]) -> Dict[str, Any]:
    """Return the existing local stock benchmark in a JSON-safe form."""
    from agents.agent4_stock_correlation import StockCorrelationAnalyzer

    frame = StockCorrelationAnalyzer().load_stock_data()
    if frame.empty:
        raise RuntimeError("Local stock benchmark is unavailable")
    ticker = _company(context)["ticker"]
    filtered = frame[frame["Ticker"] == ticker]
    if filtered.empty:
        raise RuntimeError(f"Local stock benchmark has no data for {ticker}")
    return {
        "source": "Local stock benchmark",
        "retrieved_at": _utc_now(),
        "ticker": ticker,
        "records": _records(filtered),
    }


def fallback_news_data(context: Dict[str, Any]) -> Dict[str, Any]:
    """Return matching local ESG news articles in a JSON-safe payload."""
    from agents.agent3_news_sentiment import NewsSentimentAnalyzer

    frame = NewsSentimentAnalyzer().load_news_data()
    if frame.empty:
        raise RuntimeError("Local ESG news benchmark is unavailable")
    code = str(context["company_code"]).upper()
    company = _company(context)
    filtered = NewsSentimentAnalyzer().filter_company_news(
        frame,
        code,
        company["full_name"],
    )
    return {
        "source": "Local ESG news benchmark",
        "retrieved_at": _utc_now(),
        "articles": _records(filtered),
        "article_count": len(filtered),
    }


def fallback_environmental_context(context: Dict[str, Any]) -> Dict[str, Any]:
    """Return local AQI observations as context without changing ESG scores."""
    from agents.agent2_environmental_risk import EnvironmentalRiskValidator

    historical, realtime = EnvironmentalRiskValidator().load_air_quality_data()
    if historical.empty and realtime.empty:
        raise RuntimeError("Local air-quality benchmark is unavailable")
    observations = []
    for location in _locations(context):
        result = EnvironmentalRiskValidator().calculate_city_aqi_score(
            historical,
            realtime,
            location,
        )
        observations.append(result)
    return {
        "source": "Local air-quality benchmark",
        "retrieved_at": _utc_now(),
        "locations": observations,
        "context_only": True,
        "score_impact": "none",
    }


def phase5_source_adapters() -> Dict[str, Any]:
    """Return primary and fallback callables for StageSpec construction."""
    return {
        "market": (fetch_market_data, fallback_market_data),
        "news": (fetch_esg_news, fallback_news_data),
        "environment": (
            fetch_environmental_context,
            fallback_environmental_context,
        ),
    }


def phase5_stage_specs() -> Dict[str, StageSpec]:
    """Build StageSpec objects ready for DynamicOrchestrator.run()."""
    adapters = phase5_source_adapters()
    return {
        "market": StageSpec(
            name="market",
            source="Yahoo Finance",
            fetch=adapters["market"][0],
            fallback=adapters["market"][1],
        ),
        "news": StageSpec(
            name="news",
            source="GDELT DOC 2.0",
            fetch=adapters["news"][0],
            fallback=adapters["news"][1],
        ),
        "environment": StageSpec(
            name="environment",
            source="Open-Meteo Air Quality",
            fetch=adapters["environment"][0],
            fallback=adapters["environment"][1],
            depends_on_filing=True,
        ),
    }
