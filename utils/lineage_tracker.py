"""
Lineage and reproducibility utilities for ESG pipeline.
Creates dataset signatures and run metadata snapshots.
"""

import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

import pandas as pd


def _sha256_file(file_path: Path) -> str:
    """Return SHA256 hash for a file."""
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            sha.update(chunk)
    return sha.hexdigest()


def _safe_git_commit(repo_root: Path) -> str:
    """Return current git commit hash if available."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"


def build_file_signature(file_path: Path) -> Dict[str, Any]:
    """Build traceable signature for a file."""
    signature: Dict[str, Any] = {
        "path": str(file_path),
        "exists": file_path.exists(),
    }

    if not file_path.exists():
        return signature

    signature["size_bytes"] = file_path.stat().st_size
    signature["modified_utc"] = datetime.utcfromtimestamp(file_path.stat().st_mtime).isoformat() + "Z"

    try:
        signature["sha256"] = _sha256_file(file_path)
    except Exception:
        signature["sha256"] = "hash_error"

    if file_path.suffix.lower() == ".csv":
        try:
            df = pd.read_csv(file_path)
            signature["row_count"] = int(len(df))
            signature["column_count"] = int(len(df.columns))
            signature["columns"] = list(df.columns)
        except Exception:
            signature["row_count"] = None
            signature["column_count"] = None
            signature["columns"] = []

    return signature


def build_directory_signature(dir_path: Path, pattern: str = "*.pdf") -> Dict[str, Any]:
    """Build signatures for files in a directory matching a pattern."""
    info: Dict[str, Any] = {
        "path": str(dir_path),
        "exists": dir_path.exists(),
        "pattern": pattern,
        "file_count": 0,
        "files": [],
    }

    if not dir_path.exists():
        return info

    matched_files = sorted(dir_path.glob(pattern))
    info["file_count"] = len(matched_files)
    info["files"] = [build_file_signature(path) for path in matched_files]
    return info


def save_run_metadata(
    metadata_path: Path,
    repo_root: Path,
    input_files: Dict[str, Path],
    output_files: Dict[str, Path],
    source_directory: Path,
) -> Dict[str, Any]:
    """Save append-only run metadata with input/output signatures for reproducibility."""
    run_record: Dict[str, Any] = {
        "run_id": datetime.utcnow().strftime("run-%Y%m%d-%H%M%S"),
        "run_timestamp_utc": datetime.utcnow().isoformat() + "Z",
        "python_version": sys.version,
        "platform": platform.platform(),
        "git_commit": _safe_git_commit(repo_root),
        "inputs": {},
        "input_directories": {
            "brsr_pdfs": build_directory_signature(source_directory, "*.pdf")
        },
        "outputs": {},
    }

    for key, path in input_files.items():
        run_record["inputs"][key] = build_file_signature(path)

    for key, path in output_files.items():
        run_record["outputs"][key] = build_file_signature(path)

    metadata_payload: Dict[str, Any] = {
        "project": "Multi-Agent ESG Risk Analysis System",
        "description": "Run lineage metadata for reproducibility and audit",
        "latest_run": run_record,
        "runs": [run_record],
    }

    if metadata_path.exists():
        try:
            existing = json.loads(metadata_path.read_text(encoding="utf-8"))
            runs = existing.get("runs", [])
            if isinstance(runs, list):
                runs.append(run_record)
                metadata_payload["runs"] = runs[-30:]
                metadata_payload["latest_run"] = run_record
        except Exception:
            # If existing JSON is corrupted, overwrite with fresh payload.
            pass

    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(json.dumps(metadata_payload, indent=2), encoding="utf-8")

    return run_record
