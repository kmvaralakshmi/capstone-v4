"""Resolve user company names and NSE symbols to configured company records."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterable


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


@dataclass(frozen=True)
class ResolvedCompany:
    code: str
    name: str
    ticker: str
    record: Dict


class CompanyResolver:
    """Resolve exact codes, tickers, names, and configured aliases."""

    def __init__(self, companies: Dict[str, Dict]):
        self.companies = companies

    def resolve(self, query: str) -> ResolvedCompany:
        normalized_query = _normalize(query)
        compact_query = normalized_query.replace(" ", "")

        for code, record in self.companies.items():
            candidates = {
                code,
                record.get("full_name", ""),
                record.get("company_name", ""),
                record.get("ticker", ""),
                *record.get("aliases", []),
            }
            for candidate in candidates:
                normalized_candidate = _normalize(str(candidate))
                if normalized_query == normalized_candidate:
                    return ResolvedCompany(
                        code=code,
                        name=record.get("full_name")
                        or record.get("company_name")
                        or code,
                        ticker=record.get("ticker", ""),
                        record=record,
                    )
                if compact_query and compact_query == normalized_candidate.replace(" ", ""):
                    return ResolvedCompany(
                        code=code,
                        name=record.get("full_name")
                        or record.get("company_name")
                        or code,
                        ticker=record.get("ticker", ""),
                        record=record,
                    )

        raise LookupError(f"Company not found in configuration: {query}")

    def resolve_many(self, queries: Iterable[str]) -> list[ResolvedCompany]:
        return [self.resolve(query) for query in queries]
