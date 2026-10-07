"""Discover and download NSE BRSR/XBRL filings for one or more companies."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.company_resolver import CompanyResolver
from utils.config import BRSR_PDF_DIR, COMPANIES, XBRL_DIR
from utils.filing_discovery import discover_nse_filings, download_filing


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("companies", nargs="+", help="Company name, code, or NSE symbol")
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()

    resolver = CompanyResolver(COMPANIES)
    output = []
    for query in args.companies:
        company = resolver.resolve(query)
        candidates = discover_nse_filings(company)
        downloaded = []
        if args.download:
            for candidate in candidates:
                destination_dir = (
                    XBRL_DIR if candidate.filing_type == "xbrl" else BRSR_PDF_DIR
                )
                downloaded.append(str(download_filing(candidate, destination_dir)))
        output.append(
            {
                "query": query,
                "company_code": company.code,
                "company_name": company.name,
                "candidates": [candidate.__dict__ for candidate in candidates],
                "downloaded": downloaded,
            }
        )
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
