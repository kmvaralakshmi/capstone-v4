# Phase 3 Complete Implementation Package

## What was added
- FastAPI backend under `backend/`
- Responsive vanilla-JS frontend under `frontend/`
- Dashboard for ranking, E/S/G scores, quality, risk and explainability
- Company detail view
- BRSR download-status view
- API endpoints for current processed outputs
- Background execution of the BRSR downloader and Agents 1–7
- Windows `.bat` launchers that do not require PowerShell execution policy changes
- 50-company target configuration (`config/target_companies_50.csv`)
- Pipeline launcher under `scripts/run_pipeline.py`

## Architecture
Frontend -> FastAPI -> pipeline runner -> downloader -> Agent 1 -> Agents 2–4 -> Agent 5 -> Agent 6 -> Agent 7 -> `processed-data/`

The dashboard can also read the preserved `legacy-v1-outputs/` when current outputs have not yet been generated.

## Important scope boundary
The package contains the existing validated 20-company Phase 3/early implementation PDFs and a 50-company target configuration. It does **not** falsely mark all 50 reports as downloaded. The downloader audit log remains authoritative. This is intentional: a final 50-company research result should only include reports that pass PDF/company/FY/BRSR validation.

## Run on Windows
1. Run `setup_windows.bat`.
2. Run `run_phase3.bat` to download/validate and run Agents 1–7.
3. Run `start_backend.bat`.
4. Open `http://127.0.0.1:8000`.

If NSE blocks direct requests, use the existing downloader's source fallbacks or browser-assisted retrieval and then rerun the pipeline.
