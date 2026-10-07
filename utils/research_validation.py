"""Deterministic Section C validation and research analyses.

These analyses describe associations and disclosure inconsistencies. They do
not establish causality and do not change the deterministic ESG score.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from utils.config import OUTPUT_FILES, PROCESSED_DATA_DIR


def _numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    return pd.to_numeric(frame.get(column, pd.Series(dtype=float)), errors="coerce")


def _correlation(
    frame: pd.DataFrame,
    left: str,
    right: str,
    *,
    method: str = "spearman",
) -> Optional[float]:
    values = frame[[left, right]].dropna()
    if len(values) < 3 or values[left].nunique() < 2 or values[right].nunique() < 2:
        return None
    result = values[left].corr(values[right], method=method)
    return round(float(result), 4) if pd.notna(result) else None


def validate_nse_top_200(
    project_scores: pd.DataFrame,
    nse_top_200: pd.DataFrame,
    *,
    project_code_column: str = "Company_Code",
    benchmark_code_column: str = "Company_Code",
    benchmark_rank_column: str = "NSE_Rank",
) -> pd.DataFrame:
    """Compare project rankings with an externally supplied NSE Top 200 table."""
    if project_code_column not in project_scores.columns or "Master_ESG_Score" not in project_scores.columns:
        raise ValueError("Project scores require Company_Code and Master_ESG_Score")
    if (
        benchmark_code_column not in nse_top_200.columns
        or benchmark_rank_column not in nse_top_200.columns
    ):
        raise ValueError(
            f"NSE table requires {benchmark_code_column} and {benchmark_rank_column}"
        )
    project = project_scores[[project_code_column, "Master_ESG_Score"]].copy()
    project["Master_ESG_Score"] = _numeric(project, "Master_ESG_Score")
    project = project.dropna(subset=["Master_ESG_Score"]).sort_values(
        "Master_ESG_Score", ascending=False
    )
    project["Project_Rank"] = range(1, len(project) + 1)

    benchmark = nse_top_200[
        [benchmark_code_column, benchmark_rank_column]
    ].copy()
    benchmark[benchmark_rank_column] = _numeric(benchmark, benchmark_rank_column)
    merged = project.merge(
        benchmark,
        left_on=project_code_column,
        right_on=benchmark_code_column,
        how="inner",
    )
    merged["Rank_Deviation"] = (
        merged["Project_Rank"] - merged[benchmark_rank_column]
    ).abs()
    merged["Validation_Status"] = np.where(
        merged["Rank_Deviation"] <= 10,
        "Within-10-Ranks",
        "Review-Required",
    )
    merged["Validation_Method"] = "NSE Top 200 rank comparison"
    return merged


def analyze_esg_vs_stock(
    scores: pd.DataFrame,
    stock: pd.DataFrame,
) -> Dict[str, Any]:
    """Measure observed ESG-score versus stock-return association."""
    required = {"Company_Code", "Master_ESG_Score"}
    if not required.issubset(scores.columns):
        raise ValueError("Scores require Company_Code and Master_ESG_Score")
    observations = stock.copy()
    observations["Monthly_Return_Pct"] = _numeric(
        observations, "Monthly_Return_Pct"
    )
    observations = observations.groupby("Company_Code", as_index=False).agg(
        Observed_Return_Pct=("Monthly_Return_Pct", "mean"),
        Observation_Count=("Monthly_Return_Pct", "count"),
    )
    merged = scores[["Company_Code", "Master_ESG_Score"]].copy()
    merged["Master_ESG_Score"] = _numeric(merged, "Master_ESG_Score")
    merged = merged.merge(observations, on="Company_Code", how="inner")
    correlation = _correlation(
        merged,
        "Master_ESG_Score",
        "Observed_Return_Pct",
    )
    return {
        "analysis": "esg_vs_stock",
        "method": "Spearman correlation of ESG score and observed monthly returns",
        "observation_count": len(merged),
        "correlation": correlation,
        "causal_claim": False,
        "status": "available" if correlation is not None else "insufficient_data",
        "observations": merged.to_dict(orient="records"),
    }


def analyze_esg_vs_news(
    scores: pd.DataFrame,
    news: pd.DataFrame,
) -> Dict[str, Any]:
    """Measure observed ESG-score versus ESG-news sentiment association."""
    sentiment = news.copy()
    sentiment["Sentiment_Score"] = _numeric(sentiment, "Sentiment_Score")
    sentiment = sentiment.groupby("Company_Code", as_index=False).agg(
        Mean_News_Sentiment=("Sentiment_Score", "mean"),
        Article_Count=("Sentiment_Score", "count"),
    )
    merged = scores[["Company_Code", "Master_ESG_Score"]].copy()
    merged["Master_ESG_Score"] = _numeric(merged, "Master_ESG_Score")
    merged = merged.merge(sentiment, on="Company_Code", how="inner")
    correlation = _correlation(
        merged,
        "Master_ESG_Score",
        "Mean_News_Sentiment",
    )
    return {
        "analysis": "esg_vs_news",
        "method": "Spearman correlation of ESG score and observed ESG-news sentiment",
        "observation_count": len(merged),
        "correlation": correlation,
        "causal_claim": False,
        "status": "available" if correlation is not None else "insufficient_data",
        "observations": merged.to_dict(orient="records"),
    }


def detect_cross_source_signals(
    scores: pd.DataFrame,
    *,
    news: Optional[pd.DataFrame] = None,
    environmental: Optional[pd.DataFrame] = None,
    greenwashing: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """Create review signals from independent sources, not greenwashing verdicts."""
    rows = []
    for _, score in scores.iterrows():
        code = score.get("Company_Code")
        signals = []
        company_news = (
            news[news["Company_Code"] == code]
            if news is not None and "Company_Code" in news.columns
            else pd.DataFrame()
        )
        if not company_news.empty and "Sentiment_Class" in company_news.columns:
            negative_ratio = float(
                (company_news["Sentiment_Class"] == "Negative").mean()
            )
            if negative_ratio >= 0.30:
                signals.append("negative_news_signal")
        else:
            negative_ratio = None

        company_env = (
            environmental[environmental["Company_Code"] == code]
            if environmental is not None and "Company_Code" in environmental.columns
            else pd.DataFrame()
        )
        env_score = (
            _numeric(company_env, "Environmental_Risk_Score").mean()
            if not company_env.empty
            else np.nan
        )
        reported_env = _numeric(
            pd.DataFrame([score]), "Environmental_Score"
        ).iloc[0]
        if pd.notna(reported_env) and pd.notna(env_score) and reported_env >= 7 and env_score < 5:
            signals.append("reported_vs_location_environment_gap")

        company_green = (
            greenwashing[greenwashing["Company_Code"] == code]
            if greenwashing is not None and "Company_Code" in greenwashing.columns
            else pd.DataFrame()
        )
        contradiction_count = int(
            _numeric(pd.DataFrame([score]), "Contradiction_Count").fillna(0).iloc[0]
        )
        if contradiction_count > 0 or (
            not company_green.empty
            and "Discrepancy_Detected" in company_green.columns
            and company_green["Discrepancy_Detected"].fillna(False).astype(bool).any()
        ):
            signals.append("disclosure_consistency_signal")

        rows.append(
            {
                "Company_Code": code,
                "Company_Name": score.get("Company_Name"),
                "Signal_Count": len(signals),
                "Signals": "|".join(signals) or "none",
                "Negative_News_Ratio": negative_ratio,
                "Location_Environmental_Score": env_score if pd.notna(env_score) else None,
                "Review_Status": "Review-Required" if signals else "No-Cross-Source-Signal",
                "Conclusion": (
                    "Potential inconsistency signal; not a greenwashing finding."
                    if signals
                    else "No cross-source inconsistency signal in supplied data."
                ),
            }
        )
    return pd.DataFrame(rows)


def save_research_reports(
    *,
    nse_validation: Optional[pd.DataFrame] = None,
    cross_source_signals: Optional[pd.DataFrame] = None,
    output_dir: Path = PROCESSED_DATA_DIR,
) -> Dict[str, Path]:
    """Persist tabular Section C reports and return their paths."""
    output_dir.mkdir(parents=True, exist_ok=True)
    reports: Dict[str, Path] = {}
    if nse_validation is not None:
        path = output_dir / OUTPUT_FILES["nse_validation"]
        nse_validation.to_csv(path, index=False)
        reports["nse_validation"] = path
    if cross_source_signals is not None:
        path = output_dir / OUTPUT_FILES["cross_source_signals"]
        cross_source_signals.to_csv(path, index=False)
        reports["cross_source_signals"] = path
    return reports
