
from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "processed-data"
DEMO = ROOT / "demo-output"
LEGACY = ROOT / "legacy-v1-outputs" / "processed-data"
FRONTEND = ROOT / "frontend"
LOG = ROOT / "brsr-pdfs" / "brsr_download_log.csv"

app = FastAPI(
    title="Explainable Multi-Agent ESG Risk Analysis System",
    version="3.0.0",
    description="Phase 3 web interface for the multi-agent ESG pipeline."
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

_pipeline_lock = threading.Lock()
_pipeline_state: dict[str, Any] = {
    "status": "idle",
    "message": "Ready",
    "return_code": None,
}


def read_csv(name: str) -> list[dict[str, Any]]:
    path = PROCESSED / name
    if not path.exists():
        path = DEMO / name
    if not path.exists():
        path = LEGACY / name
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def to_number(v: Any, default=None):
    try:
        if v is None or str(v).strip() == "":
            return default
        return float(v)
    except (ValueError, TypeError):
        return default


def company_summary() -> list[dict[str, Any]]:
    scores = read_csv("esg_master_scores.csv")
    quality = {r.get("Company_Code"): r for r in read_csv("data_quality_report.csv")}
    explanations = {r.get("Company_Code"): r for r in read_csv("multi_agent_explanations.csv")}
    out = []
    for row in scores:
        code = row.get("Company_Code")
        q = quality.get(code, {})
        e = explanations.get(code, {})
        out.append({
            "code": code,
            "name": row.get("Company_Name"),
            "environmental": to_number(row.get("Environmental_Score")),
            "social": to_number(row.get("Social_Score")),
            "governance": to_number(row.get("Governance_Score")),
            "score": to_number(row.get("Master_ESG_Score")),
            "risk": row.get("Risk_Level"),
            "quality": to_number(row.get("Quality_Score", q.get("Quality_Score"))),
            "rank": to_number(row.get("Project_Rank")),
            "contradictions": int(to_number(row.get("Contradiction_Count"), 0) or 0),
            "review_flags": int(to_number(row.get("Review_Flag_Count", q.get("Review_Flag_Count")), 0) or 0),
            "strengths": e.get("Strengths", ""),
            "weaknesses": e.get("Weaknesses", ""),
            "recommendations": e.get("Recommendations", ""),
        })
    return sorted(out, key=lambda x: (x["rank"] is None, x["rank"] or 999, -(x["score"] or 0)))


def pipeline_worker(skip_download: bool = False):
    global _pipeline_state
    try:
        _pipeline_state = {"status": "running", "message": "Pipeline started", "return_code": None}
        if not skip_download:
            _pipeline_state["message"] = "Downloading/validating BRSR reports..."
            dl = subprocess.run(
                [sys.executable, str(ROOT / "helper-scripts" / "download_brsr_reports.py")],
                cwd=ROOT, text=True, capture_output=True
            )
            if dl.returncode != 0:
                _pipeline_state = {
                    "status": "failed",
                    "message": "BRSR downloader failed. Check pipeline.log or terminal output.",
                    "return_code": dl.returncode,
                }
                return
        _pipeline_state["message"] = "Running Agents 1-7..."
        run = subprocess.run(
            [sys.executable, str(ROOT / "demo.py")],
            cwd=ROOT, text=True, capture_output=True
        )
        (ROOT / "pipeline.log").write_text(
            "=== STDOUT ===\n" + run.stdout + "\n=== STDERR ===\n" + run.stderr,
            encoding="utf-8"
        )
        _pipeline_state = {
            "status": "completed" if run.returncode == 0 else "failed",
            "message": "Agents 1-7 completed" if run.returncode == 0 else "Pipeline failed; see pipeline.log",
            "return_code": run.returncode,
        }
    except Exception as exc:
        _pipeline_state = {"status": "failed", "message": str(exc), "return_code": -1}


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "phase": "Phase 3",
        "version": "3.0.0",
        "processed_data_exists": PROCESSED.exists(),
        "frontend_exists": FRONTEND.exists(),
    }


@app.get("/api/summary")
def summary():
    companies = company_summary()
    scores = [c["score"] for c in companies if c["score"] is not None]
    return {
        "companies": companies,
        "count": len(companies),
        "average_score": round(sum(scores) / len(scores), 2) if scores else None,
        "best_company": companies[0] if companies else None,
        "risk_distribution": {
            risk: sum(1 for c in companies if c["risk"] == risk)
            for risk in sorted({c["risk"] for c in companies if c["risk"]})
        },
    }


@app.get("/api/companies")
def companies():
    return {"companies": company_summary()}


@app.get("/api/company/{code}")
def company(code: str):
    code = code.upper()
    match = next((c for c in company_summary() if c["code"] == code), None)
    if not match:
        raise HTTPException(status_code=404, detail=f"Company {code} not found in current outputs.")
    return {
        "summary": match,
        "brsr": [r for r in read_csv("brsr_extracted_metrics.csv") if r.get("Company_Code") == code],
        "environment": [r for r in read_csv("company_location_environmental_risk.csv") if r.get("Company_Code") == code],
        "news": [r for r in read_csv("esg_news_sentiment.csv") if r.get("Company_Code") == code],
        "stock": [r for r in read_csv("stock_esg_correlation.csv") if r.get("Company_Code") == code],
        "greenwashing": [r for r in read_csv("greenwashing_detection.csv") if r.get("Company_Code") == code],
        "explanation": [r for r in read_csv("multi_agent_explanations.csv") if r.get("Company_Code") == code],
    }


@app.get("/api/outputs/{filename}")
def output_file(filename: str):
    allowed = {
        "brsr_extracted_metrics.csv", "company_location_environmental_risk.csv",
        "esg_news_sentiment.csv", "esg_news_rejected_articles.csv",
        "stock_esg_correlation.csv", "greenwashing_detection.csv",
        "esg_master_scores.csv", "multi_agent_explanations.csv",
        "cross_validation_report.csv", "data_quality_report.csv",
        "external_benchmark_report.csv", "run_metadata.json",
    }
    if filename not in allowed:
        raise HTTPException(status_code=403, detail="Output not exposed.")
    path = PROCESSED / filename
    if not path.exists():
        path = DEMO / filename
    if not path.exists():
        path = LEGACY / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Output not generated yet.")
    return FileResponse(path, filename=filename)


@app.get("/api/download-status")
def download_status():
    if not LOG.exists():
        return {"total": 0, "valid": 0, "pending": 0, "rows": []}
    with LOG.open("r", encoding="utf-8-sig", newline="") as f:
        raw_rows = list(csv.reader(f))

    rows = []
    for values in raw_rows[1:]:
        if len(values) < 2:
            continue

        # The log predates the current writer, so normalize both layouts.
        if len(values) >= 12:
            status_index = 8
            reason = values[-1]
        else:
            status_index = 6
            reason = values[9] if len(values) > 9 else ""
        rows.append({
            "company_code": values[1],
            "status": values[status_index] if len(values) > status_index else "",
            "reason": reason,
        })

    latest = {}
    for r in rows:
        latest[r.get("company_code")] = r
    def is_valid(r):
        status = str(r.get("status", "")).upper()
        source_url = str(r.get("source_url", "")).upper()
        output_file = str(r.get("output_file", "")).upper()
        return status in {"PASS", "SKIPPED"} or source_url == "PASS" or output_file == "PASS" or "VALID CANONICAL PDF" in status

    def is_pending(r):
        status = str(r.get("status", "")).upper()
        source_url = str(r.get("source_url", "")).upper()
        output_file = str(r.get("output_file", "")).upper()
        return status == "PENDING" or source_url == "PENDING" or output_file == "PENDING"

    return {
        "total": len(latest),
        "valid": sum(1 for r in latest.values() if is_valid(r)),
        "pending": sum(1 for r in latest.values() if is_pending(r)),
        "rows": list(latest.values()),
    }


@app.post("/api/run")
def run_pipeline(
    download: bool = Query(True),
):
    global _pipeline_state
    if _pipeline_state["status"] == "running":
        return _pipeline_state
    thread = threading.Thread(target=pipeline_worker, args=(not download,), daemon=True)
    thread.start()
    return {"status": "started", "message": "Pipeline started in background."}


@app.get("/api/run-status")
def run_status():
    return _pipeline_state


@app.get("/")
def index():
    return FileResponse(FRONTEND / "index.html")


app.mount("/static", StaticFiles(directory=FRONTEND), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
