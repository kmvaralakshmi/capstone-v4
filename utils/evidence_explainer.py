"""Evidence-grounded ESG explanations.

The deterministic summary is always produced from supplied pipeline evidence.
An optional OpenAI pass can improve wording, but it may only cite evidence
identifiers present in that summary and never calculates the ESG score.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


@dataclass(frozen=True)
class EvidenceItem:
    """A claim-supporting item that can be cited by an explanation."""

    evidence_id: str
    claim: str
    source: str
    source_url: Optional[str] = None
    section: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "claim": self.claim,
            "source": self.source,
            "source_url": self.source_url,
            "section": self.section,
        }


def _number(value: Any) -> Optional[float]:
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None


def build_evidence_items(
    score: Dict[str, Any],
    contributions: List[Dict[str, Any]],
    source_rows: Optional[List[Dict[str, Any]]] = None,
) -> List[EvidenceItem]:
    """Normalize score, contribution, and source rows into citation records."""
    items: List[EvidenceItem] = []
    for index, row in enumerate(contributions, start=1):
        metric = row.get("Metric_Name", row.get("metric_name", "metric"))
        contribution = _number(
            row.get("Contribution_To_Overall", row.get("contribution"))
        )
        if contribution is None:
            continue
        source = str(row.get("Source") or row.get("Evidence_Source") or "scoring output")
        items.append(
            EvidenceItem(
                evidence_id=f"contribution-{index}",
                claim=f"{metric} contributes {contribution:.2f} to the deterministic score",
                source=source,
                source_url=row.get("Source_URL"),
                section=row.get("Section"),
            )
        )

    for index, row in enumerate(source_rows or [], start=1):
        claim = row.get("Claim") or row.get("Metric_Name") or row.get("claim")
        if not claim:
            continue
        items.append(
            EvidenceItem(
                evidence_id=f"source-{index}",
                claim=str(claim),
                source=str(row.get("Source") or row.get("Evidence_Source") or "pipeline source"),
                source_url=row.get("Source_URL"),
                section=row.get("Section"),
            )
        )
    return items


def deterministic_explanation(
    score: Dict[str, Any],
    evidence: List[EvidenceItem],
) -> Dict[str, Any]:
    """Create a grounded explanation without an external model."""
    score_value = _number(
        score.get("Master_ESG_Score", score.get("Overall_ESG_Score_0_100"))
    )
    company = score.get("Company_Name", score.get("Company_Code", "Company"))
    ordered = sorted(
        evidence,
        key=lambda item: abs(
            _number(
                item.claim.rsplit(" ", 1)[-1]
                if "contributes" in item.claim
                else None
            )
            or 0
        ),
        reverse=True,
    )
    citations = [item.evidence_id for item in ordered[:5]]
    claims = [item.claim for item in ordered[:3]]
    score_text = f"{score_value:.2f}" if score_value is not None else "not available"
    explanation = (
        f"{company} has a deterministic ESG score of {score_text}. "
        "The explanation is limited to the recorded scoring contributions and "
        "source evidence; it does not infer unsupported causes."
    )
    if claims:
        explanation += " Key recorded evidence: " + "; ".join(claims) + "."
    return {
        "status": "deterministic",
        "explanation": explanation,
        "citations": citations,
        "evidence": [item.as_dict() for item in evidence],
    }


def _model_output(response: Any) -> Dict[str, Any]:
    text = getattr(response, "output_text", "")
    if not text:
        raise RuntimeError("OpenAI returned an empty explanation")
    try:
        result = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError("OpenAI returned non-JSON explanation output") from exc
    if not isinstance(result, dict):
        raise RuntimeError("OpenAI explanation output must be a JSON object")
    return result


def generate_explanation(
    score: Dict[str, Any],
    contributions: List[Dict[str, Any]],
    source_rows: Optional[List[Dict[str, Any]]] = None,
    *,
    client: Optional[Any] = None,
    model: Optional[str] = None,
    allow_deterministic_fallback: bool = True,
) -> Dict[str, Any]:
    """Generate an explanation while enforcing evidence-only citations."""
    evidence = build_evidence_items(score, contributions, source_rows)
    deterministic = deterministic_explanation(score, evidence)
    selected_model = model or os.getenv("OPENAI_MODEL")
    if client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or not selected_model:
            if allow_deterministic_fallback:
                return deterministic
            raise RuntimeError("OPENAI_API_KEY and OPENAI_MODEL are required")
        client = OpenAI(api_key=api_key)

    prompt = json.dumps(
        {
            "score": score,
            "evidence": deterministic["evidence"],
            "required_output": {
                "explanation": "string",
                "citations": ["evidence_id"],
                "limitations": "string",
            },
        },
        ensure_ascii=False,
        default=str,
    )
    try:
        response = client.responses.create(
            model=selected_model,
            instructions=(
                "Write a concise ESG explanation grounded only in the supplied evidence. "
                "Do not calculate or change scores. Do not make claims absent from evidence. "
                "Return valid JSON with explanation, citations, and limitations."
            ),
            input=prompt,
        )
    except Exception as exc:
        if allow_deterministic_fallback:
            deterministic["fallback_reason"] = (
                f"{type(exc).__name__}: {exc}"
            )
            return deterministic
        raise RuntimeError(
            f"OpenAI explanation request failed: {type(exc).__name__}: {exc}"
        ) from exc
    result = _model_output(response)
    valid_ids = {item.evidence_id for item in evidence}
    citations = result.get("citations", [])
    if not isinstance(citations, list) or any(item not in valid_ids for item in citations):
        if allow_deterministic_fallback:
            return deterministic
        raise RuntimeError("OpenAI explanation cited evidence not present in input")
    result["status"] = "openai"
    result["evidence"] = deterministic["evidence"]
    return result
