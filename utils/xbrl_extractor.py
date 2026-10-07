"""Small, format-tolerant reader for locally downloaded BRSR XBRL data."""

from __future__ import annotations

import csv
import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Optional


@dataclass(frozen=True)
class XBRLMetric:
    value: float
    unit: str
    concept: str
    section: str = ""


def _normalize(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value).lower()).strip()


def _number(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    text = str(value).replace(",", "").strip()
    match = re.search(r"[-+]?\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _aliases(metric_name: str) -> set[str]:
    normalized = _normalize(metric_name)
    aliases = {normalized}
    aliases.update(
        {
            normalized.replace(" percentage", ""),
            normalized.replace(" per employee", ""),
            normalized.replace(" total ", " "),
        }
    )
    return {alias for alias in aliases if alias}


def _matches(concept: str, metric_name: str) -> bool:
    concept_text = _normalize(concept)
    compact_concept = concept_text.replace(" ", "")
    return any(
        alias in concept_text
        or concept_text in alias
        or alias.replace(" ", "") in compact_concept
        or compact_concept in alias.replace(" ", "")
        for alias in _aliases(metric_name)
    )


def _record_from_mapping(record: Dict[str, Any], metric_name: str) -> Optional[XBRLMetric]:
    concept = record.get("concept") or record.get("metric") or record.get("name") or ""
    if not _matches(str(concept), metric_name):
        return None
    value = _number(record.get("value"))
    if value is None:
        return None
    return XBRLMetric(
        value=value,
        unit=str(record.get("unit") or ""),
        concept=str(concept),
        section=str(record.get("section") or ""),
    )


def _walk_json(value: Any) -> Iterable[Dict[str, Any]]:
    if isinstance(value, dict):
        if any(key in value for key in ("concept", "metric", "name")) and "value" in value:
            yield value
        for child in value.values():
            yield from _walk_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_json(child)


def _read_csv(path: Path) -> list[Dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def _read_excel(path: Path) -> list[Dict[str, Any]]:
    try:
        import pandas as pd
    except ImportError as exc:
        raise RuntimeError(
            "Reading XBRL Excel files requires pandas."
        ) from exc

    frame = pd.read_excel(path)
    return frame.where(frame.notna(), None).to_dict("records")


def _read_xml(path: Path) -> list[Dict[str, Any]]:
    root = ET.parse(path).getroot()
    records = []
    for element in root.iter():
        if not list(element) and element.text and element.text.strip():
            records.append(
                {
                    "concept": element.tag.rsplit("}", 1)[-1],
                    "value": element.text.strip(),
                    "unit": element.attrib.get("unit", ""),
                    "section": element.attrib.get("section", ""),
                }
            )
    return records


def load_xbrl_metrics(path: Path, metric_names: Iterable[str]) -> Dict[str, XBRLMetric]:
    """Load recognized metric values from JSON, CSV, XML, or XBRL files."""
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in {".json"}:
        records = list(_walk_json(json.loads(path.read_text(encoding="utf-8"))))
    elif suffix in {".csv"}:
        records = _read_csv(path)
    elif suffix in {".xlsx", ".xls"}:
        records = _read_excel(path)
    elif suffix in {".xml", ".xbrl", ".html", ".htm"}:
        records = _read_xml(path)
    else:
        raise ValueError(f"Unsupported XBRL file format: {path.suffix}")

    result: Dict[str, XBRLMetric] = {}
    for metric_name in metric_names:
        for record in records:
            metric = _record_from_mapping(record, metric_name)
            if metric is not None:
                result[metric_name] = metric
                break
    return result


def find_xbrl_file(directory: Path, company_code: str) -> Optional[Path]:
    """Find one deterministic XBRL file for a company, if downloaded."""
    candidates = []
    for path in Path(directory).iterdir() if Path(directory).exists() else []:
        if path.is_file() and company_code.lower() in path.stem.lower():
            if path.suffix.lower() in {
                ".json", ".csv", ".xlsx", ".xls", ".xml", ".xbrl", ".html", ".htm"
            }:
                candidates.append(path)
    return sorted(candidates)[0] if candidates else None
