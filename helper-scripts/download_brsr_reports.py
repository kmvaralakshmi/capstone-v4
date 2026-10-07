"""
PHASE 3 - MULTI-SOURCE FY2024-25 BRSR DOWNLOADER
================================================

Rules
-----
1. One company + one FY = one canonical PDF.
2. Existing valid PDFs are skipped.
3. Source priority:
       NSE -> BSE -> Official Website
4. Downloads are made to temporary files first.
5. HTML responses are rejected.
6. Only validated PDFs become canonical PDFs.
7. No duplicate _1/_2/_3 files.
8. First 10 pages are used for FAST validation.
9. BRSR does NOT have to appear in the first 10 pages
   when the source is an integrated annual report.
10. Standalone BRSR PDFs must contain BRSR content.
11. Mphasis has an official standalone BRSR fallback.
12. All important actions are written to the audit log.
"""

from __future__ import annotations

import csv
import hashlib
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import requests
from pypdf import PdfReader


# ============================================================
# PROJECT PATH
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================
# IMPORT MANIFEST
# ============================================================

from utils.brsr_manifest import BRSR_MANIFEST


# ============================================================
# CONFIGURATION
# ============================================================

TARGET_FY = "2024-25"

OUTPUT_DIR = PROJECT_ROOT / "brsr-pdfs"

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

AUDIT_LOG = OUTPUT_DIR / "brsr_download_log.csv"

MAX_ATTEMPTS = 3

VALIDATION_PAGES = 10

CONNECT_TIMEOUT = 20

READ_TIMEOUT = 60

CHUNK_SIZE = 1024 * 1024

MAX_FILE_SIZE = 100 * 1024 * 1024

DOWNLOAD_RETRY_WAIT = 2

NSE_ANNOUNCEMENTS_URL = "https://www.nseindia.com/api/corporate-announcements"
NSE_DISCOVERY_FROM = "01-04-2025"
NSE_DISCOVERY_TO = "31-10-2025"


# ============================================================
# HTTP HEADERS
# ============================================================

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 "
    "(KHTML, like Gecko) "
    "Chrome/151.0.0.0 Safari/537.36"
)

HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": (
        "application/pdf,"
        "application/octet-stream,"
        "text/html;q=0.9,"
        "*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
}


def discover_nse_brsr_url(company_code: str, company: dict) -> str:
    """Find a FY 2024-25 BRSR attachment from NSE announcements."""
    symbol = str(company.get("ticker", company_code)).removesuffix(".NS")
    symbol = {
        "MINDTREE": "LTIM",
        "ZOMATO": "ZOMATO",
        "HCL-INFO": "HCLINSYS",
    }.get(company_code, symbol)
    params = {
        "index": "equities",
        "from_date": NSE_DISCOVERY_FROM,
        "to_date": NSE_DISCOVERY_TO,
        "symbol": symbol,
    }
    response = requests.get(
        NSE_ANNOUNCEMENTS_URL,
        params=params,
        headers=HEADERS,
        timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
    )
    response.raise_for_status()
    announcements = response.json()
    if not isinstance(announcements, list):
        raise ValueError("NSE returned an unexpected announcements payload")

    candidates = []
    for item in announcements:
        if not isinstance(item, dict):
            continue
        attachment = item.get("attchmntFile")
        text = str(item.get("attchmntText") or "")
        if not attachment or not re.search(
            r"\bBRSR\b|business responsibility\s*(?:and|&)\s*sustainability|annual report",
            text,
            re.IGNORECASE,
        ):
            continue
        candidates.append((text, attachment))

    if not candidates:
        raise LookupError(f"No FY 2024-25 BRSR announcement found for {symbol}")
    return candidates[0][1]


# ============================================================
# LOGGING
# ============================================================

LOG_FIELDS = [
    "timestamp",
    "company_code",
    "company_name",
    "financial_year",
    "source",
    "action",
    "status",
    "file",
    "sha256",
    "reason",
]


def ensure_audit_log():

    if AUDIT_LOG.exists():
        return

    with AUDIT_LOG.open(
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=LOG_FIELDS
        )

        writer.writeheader()


def sha256_file(path: Path) -> str:

    digest = hashlib.sha256()

    with path.open("rb") as f:

        while True:

            chunk = f.read(1024 * 1024)

            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest()


def write_log(
    company: dict,
    company_code: str,
    source: str,
    action: str,
    status: str,
    file_path: Optional[Path],
    reason: str
):

    ensure_audit_log()

    digest = ""

    if (
        file_path
        and file_path.exists()
    ):

        try:
            digest = sha256_file(file_path)
        except Exception:
            digest = ""

    with AUDIT_LOG.open(
        "a",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=LOG_FIELDS
        )

        writer.writerow({
            "timestamp": datetime.now().isoformat(
                timespec="seconds"
            ),
            "company_code": company_code,
            "company_name": company["company_name"],
            "financial_year": TARGET_FY,
            "source": source,
            "action": action,
            "status": status,
            "file": str(file_path)
            if file_path else "",
            "sha256": digest,
            "reason": reason,
        })


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def normalize_text(text: str) -> str:

    if not text:
        return ""

    text = text.replace(
        "\x00",
        " "
    )

    text = text.lower()

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# ============================================================
# COMPANY VALIDATION
# ============================================================

def validate_company(
    text: str,
    company: dict
) -> tuple[bool, str]:

    normalized = normalize_text(text)

    aliases = company.get(
        "aliases",
        []
    )

    for alias in aliases:

        alias_normalized = normalize_text(
            alias
        )

        if alias_normalized in normalized:

            return (
                True,
                f"company matched: {alias}"
            )

    return (
        False,
        f"company identity could not be confirmed for "
        f"{company['company_name']}"
    )


# ============================================================
# BRSR VALIDATION
# ============================================================

def validate_brsr_content(
    text: str
) -> tuple[bool, str]:

    normalized = normalize_text(text)

    patterns = [

        "business responsibility and sustainability report",

        "business responsibility & sustainability report",

        "business responsibility and sustainability",

        "business responsibility sustainability report",

        "brsr",

        "business responsibility report",

        "sustainability report",

    ]

    for pattern in patterns:

        if pattern in normalized:

            return (
                True,
                f"BRSR pattern matched: {pattern}"
            )

    return (
        False,
        "BRSR content could not be confirmed"
    )


# ============================================================
# FY VALIDATION
# ============================================================

def validate_financial_year(
    text: str,
    company: dict
) -> tuple[bool, str]:

    normalized = normalize_text(text)

    patterns = [

        "fy 2024-25",

        "fy2024-25",

        "financial year 2024-25",

        "financial year 2024 25",

        "financial year 2024-2025",

        "financial year 2024 2025",

        "april 1 2024 to march 31 2025",

        "1 april 2024 to 31 march 2025",

        "1 april 2024 to 31st march 2025",

        "april 2024 to march 2025",

        "2024-25",

        "2024 2025",

        "year ended march 31 2025",

        "year ended march 31st 2025",

        "march 31 2025",

        "march 31st 2025",

    ]

    for pattern in patterns:

        if normalize_text(pattern) in normalized:

            return (
                True,
                f"FY 2024-25 matched: {pattern}"
            )

    return (
        False,
        "FY 2024-25 could not be confirmed"
    )


# ============================================================
# PDF SIGNATURE
# ============================================================

def is_pdf_signature(
    path: Path
) -> bool:

    try:

        with path.open("rb") as f:

            return (
                f.read(5)
                == b"%PDF-"
            )

    except Exception:

        return False


# ============================================================
# PDF PAGE COUNT
# ============================================================

def get_page_count(
    path: Path
) -> int:

    reader = PdfReader(
        str(path)
    )

    return len(
        reader.pages
    )


# ============================================================
# FIRST 10 PAGES
# ============================================================

def extract_first_pages(
    path: Path
) -> tuple[str, int]:

    reader = PdfReader(
        str(path)
    )

    total_pages = len(
        reader.pages
    )

    pages_to_read = min(
        VALIDATION_PAGES,
        total_pages
    )

    text_parts = []

    for index in range(
        pages_to_read
    ):

        try:

            text = (
                reader.pages[index]
                .extract_text()
                or ""
            )

            text_parts.append(text)

        except Exception:

            continue

    return (
        "\n".join(text_parts),
        total_pages
    )


# ============================================================
# DETERMINE IF SOURCE IS STANDALONE BRSR
# ============================================================

def source_is_standalone_brsr(
    source_name: str,
    url: str
) -> bool:

    combined = (
        source_name
        + " "
        + url
    ).lower()

    keywords = [

        "brsr",

        "business-responsibility",

        "business_responsibility",

        "sustainability-report",

        "sustainability_report",

    ]

    return any(
        keyword in combined
        for keyword in keywords
    )


# ============================================================
# FULL DOCUMENT BRSR SEARCH
# ============================================================

def search_document_for_brsr(
    path: Path
) -> bool:

    """
    Search the PDF for BRSR text.

    This is only used when the first 10 pages
    do not contain BRSR.

    We stop immediately once BRSR is found.
    """

    try:

        reader = PdfReader(
            str(path)
        )

        total_pages = len(
            reader.pages
        )

        for index in range(
            VALIDATION_PAGES,
            total_pages
        ):

            try:

                text = (
                    reader.pages[index]
                    .extract_text()
                    or ""
                )

            except Exception:

                continue

            normalized = normalize_text(
                text
            )

            found, _ = (
                validate_brsr_content(
                    normalized
                )
            )

            if found:

                print(
                    f"BRSR found on page "
                    f"{index + 1}/{total_pages}"
                )

                return True

            # Progress every 25 pages.
            if (
                (index + 1)
                % 25
                == 0
            ):

                print(
                    f"BRSR search through page "
                    f"{index + 1}/{total_pages}"
                )

    except Exception as exc:

        print(
            f"Warning: full BRSR search failed: {exc}"
        )

    return False


# ============================================================
# DOCUMENT VALIDATION
# ============================================================

def validate_pdf(
    path: Path,
    company: dict,
    source_name: str,
    source_url: str
) -> tuple[bool, str]:

    if not path.exists():

        return (
            False,
            "file does not exist"
        )

    size = path.stat().st_size

    if size < 1024:

        return (
            False,
            "file too small"
        )

    if size > MAX_FILE_SIZE:

        return (
            False,
            "file exceeds maximum allowed size"
        )

    if not is_pdf_signature(path):

        return (
            False,
            "invalid PDF signature"
        )

    try:

        first_text, total_pages = (
            extract_first_pages(
                path
            )
        )

    except Exception as exc:

        return (
            False,
            f"PDF could not be opened: {exc}"
        )

    if total_pages == 0:

        return (
            False,
            "PDF contains zero pages"
        )

    print(
        f"PDF pages: {total_pages}"
    )

    print(
        f"Validating first "
        f"{min(VALIDATION_PAGES, total_pages)} "
        f"pages..."
    )

    normalized = normalize_text(
        first_text
    )

    # --------------------------------------------------------
    # Company
    # --------------------------------------------------------

    company_ok, company_reason = (
        validate_company(
            normalized,
            company
        )
    )

    print(
        "Company validation:",
        "PASS" if company_ok else "FAIL"
    )

    if not company_ok:

        return (
            False,
            company_reason
        )

    # --------------------------------------------------------
    # FY
    # --------------------------------------------------------

    fy_ok, fy_reason = (
        validate_financial_year(
            normalized,
            company
        )
    )

    print(
        "Financial-year validation:",
        "PASS" if fy_ok else "FAIL"
    )

    if not fy_ok:

        return (
            False,
            fy_reason
        )

    # --------------------------------------------------------
    # BRSR
    # --------------------------------------------------------

    brsr_ok, brsr_reason = (
        validate_brsr_content(
            normalized
        )
    )

    print(
        "BRSR validation:",
        "PASS" if brsr_ok else "NOT IN FIRST 10 PAGES"
    )

    # --------------------------------------------------------
    # Standalone BRSR
    # --------------------------------------------------------

    standalone = source_is_standalone_brsr(
        source_name,
        source_url
    )

    if standalone:

        if not brsr_ok:

            return (
                False,
                "standalone BRSR document does not contain BRSR content"
            )

        return (
            True,
            "standalone BRSR validated"
        )

    # --------------------------------------------------------
    # Integrated annual report
    # --------------------------------------------------------

    if brsr_ok:

        return (
            True,
            "company + FY2024-25 + BRSR validated"
        )

    print(
        "BRSR not found in first 10 pages."
    )

    print(
        "Searching document for BRSR section..."
    )

    full_brsr_found = (
        search_document_for_brsr(
            path
        )
    )

    if not full_brsr_found:

        return (
            False,
            "BRSR content could not be confirmed"
        )

    return (
        True,
        "company + FY2024-25 + BRSR validated"
    )


# ============================================================
# DOWNLOAD
# ============================================================

def download_to_temp(
    url: str,
    destination: Path,
    source_name: str
) -> tuple[Optional[Path], str]:

    temp_path = destination.with_name(
        destination.name
        + ".download.tmp"
    )

    temp_path.unlink(
        missing_ok=True
    )

    last_error = ""

    for attempt in range(
        1,
        MAX_ATTEMPTS + 1
    ):

        print(
            f"[{source_name}] "
            f"Download attempt "
            f"{attempt}/{MAX_ATTEMPTS}"
        )

        try:

            with requests.get(
                url,
                headers=HEADERS,
                stream=True,
                timeout=(
                    CONNECT_TIMEOUT,
                    READ_TIMEOUT
                ),
                allow_redirects=True,
            ) as response:

                print(
                    f"[{source_name}] "
                    f"HTTP Status: "
                    f"{response.status_code}"
                )

                response.raise_for_status()

                content_type = (
                    response.headers
                    .get(
                        "Content-Type",
                        ""
                    )
                    .lower()
                )

                print(
                    f"[{source_name}] "
                    f"Content-Type: "
                    f"{content_type}"
                )

                # ------------------------------------------------
                # Reject HTML
                # ------------------------------------------------

                if (
                    "text/html"
                    in content_type
                ):

                    raise ValueError(
                        "server returned HTML instead of PDF"
                    )

                # ------------------------------------------------
                # Download
                # ------------------------------------------------

                total = 0
                last_mb = 0

                with temp_path.open(
                    "wb"
                ) as f:

                    for chunk in response.iter_content(
                        chunk_size=CHUNK_SIZE
                    ):

                        if not chunk:
                            continue

                        f.write(chunk)

                        total += len(
                            chunk
                        )

                        if total > MAX_FILE_SIZE:

                            raise ValueError(
                                "download exceeds maximum file size"
                            )

                        current_mb = (
                            total
                            // (
                                1024 * 1024
                            )
                        )

                        if (
                            current_mb
                            > last_mb
                        ):

                            print(
                                f"[{source_name}] "
                                f"Downloaded: "
                                f"{current_mb:.2f} MB"
                            )

                            last_mb = current_mb

                print(
                    f"[{source_name}] "
                    f"Download completed: "
                    f"{total / 1024 / 1024:.2f} MB"
                )

                # ------------------------------------------------
                # PDF signature
                # ------------------------------------------------

                if not is_pdf_signature(
                    temp_path
                ):

                    raise ValueError(
                        "invalid PDF signature"
                    )

                return (
                    temp_path,
                    "download successful"
                )

        except Exception as exc:

            last_error = str(
                exc
            )

            print(
                f"[{source_name}] "
                f"Attempt {attempt} failed: "
                f"{last_error}"
            )

            temp_path.unlink(
                missing_ok=True
            )

            if (
                attempt
                < MAX_ATTEMPTS
            ):

                wait_seconds = (
                    DOWNLOAD_RETRY_WAIT
                    * attempt
                )

                print(
                    f"Retrying in "
                    f"{wait_seconds} seconds..."
                )

                time.sleep(
                    wait_seconds
                )

    return (
        None,
        (
            f"download failed after "
            f"{MAX_ATTEMPTS} attempts: "
            f"{last_error}"
        )
    )


# ============================================================
# CANONICAL FILENAME
# ============================================================

def canonical_path(
    company_code: str
) -> Path:

    return (
        OUTPUT_DIR
        / f"{company_code}_BR_24-25.pdf"
    )


# ============================================================
# PROCESS COMPANY
# ============================================================

def process_company(
    company_code: str,
    company: dict
) -> str:

    name = company[
        "company_name"
    ]

    destination = canonical_path(
        company_code
    )

    print()
    print("-" * 60)
    print(
        f"{company_code}: {name}"
    )
    print("-" * 60)

    # ========================================================
    # EXISTING CANONICAL
    # ========================================================

    if destination.exists():

        print(
            "Canonical PDF already exists."
        )

        valid, reason = (
            validate_pdf(
                destination,
                company,
                "Existing Canonical",
                ""
            )
        )

        if valid:

            print(
                "Existing PDF validation: PASS"
            )

            print(
                "ACTION: SKIP"
            )

            write_log(
                company,
                company_code,
                "Existing Canonical",
                "SKIP",
                "PASS",
                destination,
                reason
            )

            return "skipped"

        print(
            "Existing PDF validation: FAILED"
        )

        print(
            f"Reason: {reason}"
        )

        # ----------------------------------------------------
        # IMPORTANT:
        # Do NOT delete the invalid canonical immediately.
        # Rename it so the original is preserved.
        # ----------------------------------------------------

        invalid_path = (
            destination.with_suffix(
                ".invalid.pdf"
            )
        )

        try:

            if invalid_path.exists():

                invalid_path.unlink()

            destination.replace(
                invalid_path
            )

            print(
                "Invalid canonical PDF moved to:"
            )

            print(
                invalid_path
            )

            write_log(
                company,
                company_code,
                "Existing Canonical",
                "MOVE_INVALID",
                "PASS",
                invalid_path,
                reason
            )

        except Exception as exc:

            print(
                "Warning: could not move "
                f"invalid canonical: {exc}"
            )

    # ========================================================
    # SOURCES
    # ========================================================

    sources = sorted(
        company.get(
            "sources",
            []
        ),
        key=lambda item:
            item.get(
                "priority",
                999
            )
    )

    configured_sources = 0

    for source in sources:

        source_name = source.get(
            "name",
            "Unknown"
        )

        url = source.get("url")

        if url == "AUTO":
            try:
                url = discover_nse_brsr_url(company_code, company)
                source["url"] = url
                print(f"Discovered NSE BRSR URL: {url}")
            except (LookupError, requests.RequestException, ValueError) as exc:
                print(f"{source_name}: AUTO discovery failed: {exc}")
                write_log(
                    company,
                    company_code,
                    source_name,
                    "DISCOVER",
                    "FAILED",
                    None,
                    str(exc),
                )
                continue

        if not url:

            print()
            print(
                f"{source_name}: "
                "URL not configured."
            )

            continue

        configured_sources += 1

        print()
        print(
            f"Trying source priority "
            f"{source.get('priority', '?')}: "
            f"{source_name}"
        )

        print()
        print(
            f"Source: {source_name}"
        )

        print(
            f"URL: {url}"
        )

        parsed = urlparse(
            url
        )

        if parsed.scheme not in (
            "http",
            "https"
        ):

            print(
                f"{source_name}: "
                "invalid URL"
            )

            continue

        write_log(
            company,
            company_code,
            source_name,
            "DOWNLOAD",
            "STARTED",
            None,
            "source attempt started"
        )

        temp_path = None

        try:

            temp_path, reason = (
                download_to_temp(
                    url,
                    destination,
                    source_name
                )
            )

            if temp_path is None:

                print(
                    f"{source_name}: "
                    "DOWNLOAD FAILED"
                )

                print(
                    f"Reason: {reason}"
                )

                write_log(
                    company,
                    company_code,
                    source_name,
                    "DOWNLOAD",
                    "FAILED",
                    None,
                    reason
                )

                continue

            print(
                f"{source_name}: "
                "running document validation..."
            )

            valid, validation_reason = (
                validate_pdf(
                    temp_path,
                    company,
                    source_name,
                    url
                )
            )

            if not valid:

                print(
                    f"{source_name}: "
                    "VALIDATION FAILED"
                )

                print(
                    f"Reason: "
                    f"{validation_reason}"
                )

                write_log(
                    company,
                    company_code,
                    source_name,
                    "VALIDATION",
                    "FAILED",
                    temp_path,
                    validation_reason
                )

                temp_path.unlink(
                    missing_ok=True
                )

                print(
                    f"{source_name}: "
                    "trying next fallback source..."
                )

                continue

            # ------------------------------------------------
            # ACCEPT ONLY VALIDATED PDF
            # ------------------------------------------------

            temp_path.replace(
                destination
            )

            print()
            print(
                f"{source_name}: "
                "VALIDATION PASS"
            )

            print(
                f"{source_name}: "
                "SOURCE ACCEPTED"
            )

            write_log(
                company,
                company_code,
                source_name,
                "DOWNLOAD",
                "PASS",
                destination,
                validation_reason
            )

            print()
            print("=" * 60)
            print(
                "SOURCE ACCEPTED"
            )
            print(
                f"Company: {name}"
            )
            print(
                f"Source: {source_name}"
            )
            print(
                f"File: {destination}"
            )
            print("=" * 60)

            return "downloaded"

        except Exception as exc:

            if temp_path:

                temp_path.unlink(
                    missing_ok=True
                )

            print(
                f"{source_name}: "
                f"ERROR - {exc}"
            )

            write_log(
                company,
                company_code,
                source_name,
                "ERROR",
                "FAILED",
                None,
                str(exc)
            )

            continue

    # ========================================================
    # NO SOURCE
    # ========================================================

    if configured_sources == 0:

        print()
        print(
            "No configured source URLs available."
        )

        print(
            "STATUS: PENDING"
        )

        write_log(
            company,
            company_code,
            "none",
            "PENDING",
            "PENDING",
            None,
            "no configured source URLs"
        )

        return "pending"

    print()
    print(
        "All configured sources exhausted."
    )

    write_log(
        company,
        company_code,
        "all sources",
        "PENDING",
        "PENDING",
        None,
        "all configured sources failed validation/download"
    )

    return "pending"


# ============================================================
# MAIN
# ============================================================

def main():

    ensure_audit_log()

    print("=" * 70)

    print(
        "PHASE 3 - FINAL MULTI-SOURCE "
        "FY2024-25 BRSR DOWNLOADER"
    )

    print("=" * 70)

    print(
        "Rule: One company + one FY = one active PDF"
    )

    print(
        "Source priority:"
    )

    print(
        "1. NSE"
    )

    print(
        "2. BSE"
    )

    print(
        "3. Company Official Website"
    )

    print()

    print(
        "Target FY:",
        TARGET_FY
    )

    print(
        "Output:",
        OUTPUT_DIR
    )

    print(
        "Maximum attempts per source:",
        MAX_ATTEMPTS
    )

    print(
        "Fast validation pages:",
        VALIDATION_PAGES
    )

    print("=" * 70)

    downloaded = 0
    skipped = 0
    pending = 0
    failed = 0

    for company_code, company in (
        BRSR_MANIFEST.items()
    ):

        try:

            result = process_company(
                company_code,
                company
            )

            if result == "downloaded":

                downloaded += 1

            elif result == "skipped":

                skipped += 1

            elif result == "pending":

                pending += 1

            elif result == "failed":

                failed += 1

        except KeyboardInterrupt:

            print()
            print(
                "Process interrupted by user."
            )

            break

        except Exception as exc:

            failed += 1

            print()
            print(
                f"UNEXPECTED ERROR for "
                f"{company['company_name']}: "
                f"{exc}"
            )

            write_log(
                company,
                company_code,
                "system",
                "ERROR",
                "FAILED",
                None,
                str(exc)
            )

    # ========================================================
    # SUMMARY
    # ========================================================

    print()
    print("=" * 70)

    print(
        "BRSR DOWNLOAD SUMMARY"
    )

    print("=" * 70)

    print(
        f"Total companies : "
        f"{len(BRSR_MANIFEST)}"
    )

    print(
        f"Downloaded      : "
        f"{downloaded}"
    )

    print(
        f"Skipped         : "
        f"{skipped}"
    )

    print(
        f"Pending         : "
        f"{pending}"
    )

    print(
        f"Failed          : "
        f"{failed}"
    )

    print()

    print(
        "Audit log:"
    )

    print(
        AUDIT_LOG
    )

    print("=" * 70)

    if failed > 0:

        print(
            "STATUS: COMPLETED WITH FAILURES"
        )

    elif pending > 0:

        print(
            "STATUS: COMPLETED WITH PENDING SOURCES"
        )

    else:

        print(
            "STATUS: COMPLETED SUCCESSFULLY"
        )


if __name__ == "__main__":
    main()