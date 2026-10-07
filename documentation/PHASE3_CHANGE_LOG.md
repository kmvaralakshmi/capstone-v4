# 📋 Phase 3 Change Log

## Entry #034 — BRSR canonical-file rule
- One company + one FY = one active PDF.
- Existing valid canonical PDFs are reused.
- Duplicate `_1`, `_2`, `_3` files are not created.

## Entry #035 — Multi-source BRSR acquisition
- Added source-priority support through `utils/brsr_manifest.py`.
- Supported priority: NSE → BSE → official company source.
- Added validation before a source can become the active PDF.

## Entry #036 — Helper-script review
- Reviewed the BRSR downloader and PowerShell fallback.
- Confirmed streaming download, retries, HTML rejection, canonical activation and audit logging.

## Entry #037 — Pipeline preparation
- Confirmed the seven-agent execution path through `demo.py`.
- Confirmed the Phase 3 cohort is configuration-driven rather than hard-coded to five companies.

## Entry #038 — V1 ZIP integrated as Phase 3 master project
- Original V1 raw datasets preserved.
- Existing seven-agent architecture preserved.
- Existing V1.1 quality/lineage work preserved.
- Phase 3 configuration expanded to 20 companies.

## Entry #039 — Configuration repair
- Restored V1 headquarters/major-office fields required by Agent 2.
- Added representative headquarters locations for Phase 3 additions.
- Kept additional-company office lists empty unless explicitly documented in the project evidence.

## Entry #040 — Downloader hardening
- Generalized NSE `AUTO` discovery so it is not hard-coded to LTIMindtree.
- Added stricter target-period validation.
- Kept temporary-file activation and canonical replacement safety.
- Added legacy-log preservation when an old audit-log schema is encountered.

## Entry #041 — Phase 3 pre-flight
- Added `helper-scripts/validate_phase3.py`.
- It reports canonical PDF presence for all 20 companies before agent execution.

## Entry #042 — Reporting-period integrity
- Hexaware is not silently filled with a calendar-year report just to reach 20 PDFs.
- The project documents Hexaware as pending until a genuinely comparable target-period document is identified.

## Current status

- Target companies: 20
- Canonical FY 2024-25 PDFs present in supplied ZIP: 19
- Pending: Hexaware Technologies
- Agent architecture: 7 agents retained
- V1 raw datasets: retained


## Phase 3 web application completion (2026-09-01)
- Added FastAPI backend and REST API.
- Added responsive frontend dashboard.
- Added company detail/explainability view.
- Added BRSR download audit status UI.
- Added Windows batch launchers to avoid PowerShell policy issues.
- Added 50-company target configuration without falsely claiming unverified PDFs.
