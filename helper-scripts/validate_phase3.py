"""Validate Phase 3 project inputs before running Agents 1-7."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.brsr_manifest import BRSR_MANIFEST
from utils.config import BRSR_PDF_DIR, COMPANIES, TARGET_FINANCIAL_YEAR


def main() -> int:
    print("=" * 70)
    print("PHASE 3 PRE-FLIGHT VALIDATION")
    print("=" * 70)
    print(f"Target financial year: {TARGET_FINANCIAL_YEAR}")
    print(f"Configured companies : {len(COMPANIES)}")
    print(f"Manifest companies   : {len(BRSR_MANIFEST)}")
    print(f"BRSR directory       : {BRSR_PDF_DIR}")
    print("=" * 70)

    missing = []
    present = []
    for code, details in COMPANIES.items():
        path = BRSR_PDF_DIR / details["brsr_file"]
        if path.exists() and path.stat().st_size > 0:
            present.append(code)
            print(f"PASS  {code:<12} {details['brsr_file']:<30} {path.stat().st_size/1024:.1f} KB")
        else:
            missing.append(code)
            print(f"MISS  {code:<12} {details['brsr_file']}")

    print("\n" + "=" * 70)
    print(f"Valid file presence: {len(present)}/{len(COMPANIES)}")
    print(f"Missing files     : {len(missing)}")
    if missing:
        print("Missing company codes:", ", ".join(missing))
        print("\nRun the downloader first. Agent 1 will create review placeholders for")
        print("companies that still have no validated BRSR PDF.")
    else:
        print("All 20 canonical PDF inputs are present.")
    print("=" * 70)

    # This pre-flight only checks file presence. Full PDF content validation is
    # performed by download_brsr_reports.py before a file becomes canonical.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
