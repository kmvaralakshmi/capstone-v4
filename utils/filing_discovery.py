"""Dynamic NSE BRSR/XBRL filing discovery and download helpers."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Optional
from urllib.parse import urljoin

import requests

from utils.company_resolver import ResolvedCompany


NSE_ANNOUNCEMENTS_URL = "https://www.nseindia.com/api/corporate-announcements"
NSE_BASE_URL = "https://www.nseindia.com"
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/151.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, application/octet-stream, text/html;q=0.9",
    "Accept-Language": "en-US,en;q=0.9",
}


@dataclass(frozen=True)
class FilingCandidate:
    company_code: str
    source: str
    url: str
    title: str
    filing_type: str
    financial_year: str


def _text(item: dict[str, Any]) -> str:
    return " ".join(
        str(item.get(key) or "")
        for key in ("attchmntText", "subject", "desc", "announcement", "fileName")
    )


def _filing_type(item: dict[str, Any], url: str) -> str:
    text = f"{_text(item)} {url}".lower()
    if "xbrl" in text or "excel" in text or "xlsx" in text or "xls" in text:
        return "xbrl"
    return "pdf"


def _attachment_url(value: Any) -> str:
    if not value:
        return ""
    return urljoin(NSE_BASE_URL, str(value).strip())


def discover_nse_filings(
    company: ResolvedCompany,
    *,
    from_date: str = "01-04-2025",
    to_date: str = "31-10-2025",
    session: Optional[requests.Session] = None,
) -> list[FilingCandidate]:
    """Discover BRSR-related NSE attachments for a resolved company."""
    client = session or requests.Session()
    symbol = company.ticker.removesuffix(".NS") or company.code
    response = client.get(
        NSE_ANNOUNCEMENTS_URL,
        params={
            "index": "equities",
            "from_date": from_date,
            "to_date": to_date,
            "symbol": symbol,
        },
        headers=DEFAULT_HEADERS,
        timeout=(20, 60),
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list):
        raise ValueError("NSE returned an unexpected announcements payload")

    candidates: list[FilingCandidate] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        url = _attachment_url(item.get("attchmntFile"))
        text = _text(item)
        if not url or not re.search(
            r"\bBRSR\b|business responsibility|sustainability|xbrl|annual report",
            text,
            re.IGNORECASE,
        ):
            continue
        candidates.append(
            FilingCandidate(
                company_code=company.code,
                source="NSE",
                url=url,
                title=text[:300],
                filing_type=_filing_type(item, url),
                financial_year="2024-25",
            )
        )

    return candidates


def download_filing(
    candidate: FilingCandidate,
    output_dir: Path,
    *,
    session: Optional[requests.Session] = None,
    max_bytes: int = 100 * 1024 * 1024,
) -> Path:
    """Download one discovered filing atomically and return its final path."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    extension = ".xlsx" if candidate.filing_type == "xbrl" else ".pdf"
    digest = hashlib.sha256(candidate.url.encode("utf-8")).hexdigest()[:12]
    destination = output_dir / f"{candidate.company_code}_BRSR_24-25_{digest}{extension}"
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    client = session or requests.Session()

    with client.get(
        candidate.url,
        headers=DEFAULT_HEADERS,
        stream=True,
        timeout=(20, 60),
    ) as response:
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "").lower()
        if "text/html" in content_type and candidate.filing_type != "pdf":
            raise ValueError("NSE returned HTML instead of an XBRL file")
        total = 0
        with temporary.open("wb") as file:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if not chunk:
                    continue
                total += len(chunk)
                if total > max_bytes:
                    raise ValueError("filing exceeds maximum allowed size")
                file.write(chunk)

    if total == 0:
        temporary.unlink(missing_ok=True)
        raise ValueError("NSE returned an empty filing")
    temporary.replace(destination)
    return destination
