"""Evidence-grounded XAI for the V4 ESG score.

Uses exact mathematical metric contributions from the scoring engine. Optional SHAP is
supported for a separate predictive model; it is not used to fabricate explanations of
the deterministic ESG score.
"""
from pathlib import Path
import pandas as pd

def build_explanations(scores_csv, contributions_csv, brsr_csv, output_csv):
    scores = pd.read_csv(scores_csv)
    contrib = pd.read_csv(contributions_csv)
    brsr = pd.read_csv(brsr_csv) if Path(brsr_csv).exists() else pd.DataFrame()
    rows=[]
    for _, s in scores.iterrows():
        code=s["Company_Code"]
        c=contrib[contrib.Company_Code==code].sort_values("Contribution_To_Overall", ascending=False)
        top_pos=c.head(3); top_neg=c.tail(3).sort_values("Contribution_To_Overall")
        evidence=brsr[brsr.Company_Code==code] if not brsr.empty else pd.DataFrame()
        pos=[]
        for _,r in top_pos.iterrows():
            src=evidence[evidence.Metric_Name==r.Metric_Name] if not evidence.empty else pd.DataFrame()
            page=src.Page_Number.iloc[0] if not src.empty and "Page_Number" in src else "N/A"
            pos.append(f"{r.Metric_Name}: contribution {r.Contribution_To_Overall:.2f}; source page {page}")
        neg=[]
        for _,r in top_neg.iterrows():
            src=evidence[evidence.Metric_Name==r.Metric_Name] if not evidence.empty else pd.DataFrame()
            page=src.Page_Number.iloc[0] if not src.empty and "Page_Number" in src else "N/A"
            neg.append(f"{r.Metric_Name}: contribution {r.Contribution_To_Overall:.2f}; source page {page}")
        rows.append({"Company_Code":code,"Company_Name":s["Company_Name"],
                     "Overall_ESG_Score_0_100":s["Overall_ESG_Score_0_100"],
                     "Data_Completeness_Pct":s["Data_Completeness_Pct"],
                     "Mean_Extraction_Confidence":s["Mean_Extraction_Confidence"],
                     "Top_Positive_Contributors":" | ".join(pos),
                     "Top_Low_Contributors":" | ".join(neg),
                     "Explanation":"Score is explained by the mathematically calculated contributions of validated, normalized BRSR metrics; evidence pages are retained where available."})
    pd.DataFrame(rows).to_csv(output_csv,index=False)

if __name__ == "__main__":
    root=Path(__file__).resolve().parents[1]; out=root/"processed-data"
    build_explanations(out/"esg_scores_v4.csv",out/"esg_metric_contributions_v4.csv",out/"brsr_extracted_metrics.csv",out/"esg_explanations_v4.csv")
