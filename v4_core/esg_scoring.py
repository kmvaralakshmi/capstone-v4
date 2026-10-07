"""Version 4 ESG scoring engine.

Design goals:
- BRSR/BRSR-Core-aligned metric catalogue is the input, not an invented rating.
- Normalize metrics within the selected company cohort using direction-aware min-max.
- Calculate Environmental/Social/Governance pillar scores and an overall research score.
- Report completeness, extraction confidence and validation coverage separately.
- Never silently convert missing data to zero.

This is a transparent research score, not an official SEBI rating.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd

DEFAULT_PILLAR_WEIGHTS = {"Environmental": 1/3, "Social": 1/3, "Governance": 1/3}

# Direction is explicit so the score does not assume that "higher is always better".
# Metrics not in this catalogue are retained but excluded from scoring until direction is defined.
METRIC_RULES = {
    "Total Energy Consumption": ("Environmental", "lower"),
    "Renewable Energy Percentage": ("Environmental", "higher"),
    "Total Water Consumption": ("Environmental", "lower"),
    "Water Recycled Percentage": ("Environmental", "higher"),
    "Total Waste Generated": ("Environmental", "lower"),
    "Waste Recycled Percentage": ("Environmental", "higher"),
    "Total Employees": ("Social", "context"),
    "Female Employees Percentage": ("Social", "higher"),
    "Female Employee Percentage": ("Social", "higher"),
    "Employee Turnover Rate": ("Social", "lower"),
    "Training Hours Per Employee": ("Social", "higher"),
    "Independent Directors Percentage": ("Governance", "higher"),
    "Board Independence Percentage": ("Governance", "higher"),
    "CSR Amount Spent": ("Governance", "higher"),
}

class ESGScoringV4:
    def __init__(self, pillar_weights=None):
        self.pillar_weights = pillar_weights or DEFAULT_PILLAR_WEIGHTS.copy()
        total = sum(self.pillar_weights.values())
        self.pillar_weights = {k: v/total for k, v in self.pillar_weights.items()}

    @staticmethod
    def _num(s):
        return pd.to_numeric(s, errors="coerce")

    def normalize_cohort(self, df: pd.DataFrame) -> pd.DataFrame:
        d = df.copy()
        d["Metric_Value"] = self._num(d["Metric_Value"])
        d["Normalized_Score"] = np.nan
        d["Scoring_Status"] = "Excluded"
        d["Direction"] = "undefined"
        for metric, g in d.groupby("Metric_Name", dropna=False):
            rule = METRIC_RULES.get(metric)
            if not rule:
                continue
            pillar, direction = rule
            idx = g.index
            d.loc[idx, "Direction"] = direction
            if direction == "context":
                continue
            vals = g["Metric_Value"]
            valid = vals.notna()
            if valid.sum() == 0:
                continue
            lo, hi = vals[valid].min(), vals[valid].max()
            if hi == lo:
                d.loc[idx[valid], "Normalized_Score"] = 50.0
            elif direction == "higher":
                d.loc[idx[valid], "Normalized_Score"] = 100 * (vals[valid]-lo)/(hi-lo)
            else:
                d.loc[idx[valid], "Normalized_Score"] = 100 * (hi-vals[valid])/(hi-lo)
            d.loc[idx, "Scoring_Status"] = "Scored"
        return d

    def score(self, df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        d = self.normalize_cohort(df)
        rows = []
        contrib_rows = []
        for company_code, g in d.groupby("Company_Code"):
            company_name = g["Company_Name"].iloc[0]
            pillar_scores = {}
            for pillar in self.pillar_weights:
                pg = g[(g["Metric_Category"] == pillar) & g["Normalized_Score"].notna()]
                if pg.empty:
                    pillar_scores[pillar] = np.nan
                    continue
                # Equal metric weight within a pillar unless a documented metric-specific scheme is added.
                pillar_scores[pillar] = float(pg["Normalized_Score"].mean())
                for _, r in pg.iterrows():
                    contribution = self.pillar_weights[pillar] * (r["Normalized_Score"] / len(pg))
                    contrib_rows.append({
                        "Company_Code": company_code,
                        "Company_Name": company_name,
                        "Pillar": pillar,
                        "Metric_Name": r["Metric_Name"],
                        "Metric_Value": r["Metric_Value"],
                        "Normalized_Score": r["Normalized_Score"],
                        "Pillar_Weight": self.pillar_weights[pillar],
                        "Contribution_To_Overall": contribution,
                        "Direction": r["Direction"],
                    })
            available = [p for p, v in pillar_scores.items() if pd.notna(v)]
            overall = (sum(self.pillar_weights[p]*pillar_scores[p] for p in available) /
                       sum(self.pillar_weights[p] for p in available)) if available else np.nan
            expected = len(g)
            valid = int(g["Metric_Value"].notna().sum())
            validated = int((g.get("Validation_Status", pd.Series(index=g.index)).astype(str).str.lower() == "valid").sum()) if "Validation_Status" in g else 0
            confidence = pd.to_numeric(g.get("Confidence_Score", pd.Series(dtype=float)), errors="coerce").mean()
            completeness = 100 * valid / expected if expected else 0
            validation_coverage = 100 * validated / valid if valid else 0
            rows.append({
                "Company_Code": company_code,
                "Company_Name": company_name,
                "Environmental_Score": pillar_scores.get("Environmental", np.nan),
                "Social_Score": pillar_scores.get("Social", np.nan),
                "Governance_Score": pillar_scores.get("Governance", np.nan),
                "Overall_ESG_Score_0_100": overall,
                "Data_Completeness_Pct": completeness,
                "Validation_Coverage_Pct": validation_coverage,
                "Mean_Extraction_Confidence": confidence,
                "Scored_Metric_Count": int(g["Normalized_Score"].notna().sum()),
                "Available_Pillar_Count": len(available),
                "Scoring_Note": "Research score from normalized, direction-aware BRSR metrics; not an official SEBI rating."
            })
        return pd.DataFrame(rows), pd.DataFrame(contrib_rows)

def run(input_csv: str, output_dir: str) -> None:
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(input_csv)
    scorer = ESGScoringV4()
    scores, contributions = scorer.score(df)
    scores.to_csv(out / "esg_scores_v4.csv", index=False)
    contributions.to_csv(out / "esg_metric_contributions_v4.csv", index=False)
    with open(out / "esg_scoring_methodology_v4.json", "w", encoding="utf-8") as f:
        json.dump({"pillar_weights": scorer.pillar_weights, "metric_rules": METRIC_RULES,
                   "note": "Research score; not an official SEBI rating."}, f, indent=2)

if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    source = root / "processed-data" / "brsr_extracted_metrics.csv"
    run(str(source), str(root / "processed-data"))
