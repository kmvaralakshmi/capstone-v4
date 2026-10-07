"""Evidence-gap greenwashing signal detector.

This module reports potential disclosure-performance inconsistencies. It does NOT label
companies as greenwashing; human review is required.
"""
from pathlib import Path
import pandas as pd
import numpy as np

def run(brsr_csv, sentiment_csv, output_csv):
    b=pd.read_csv(brsr_csv); s=pd.read_csv(sentiment_csv) if Path(sentiment_csv).exists() else pd.DataFrame()
    rows=[]
    for code,g in b.groupby("Company_Code"):
        name=g.Company_Name.iloc[0]
        signals=[]
        # A quantitative trend requires multiple observations; if only one FY exists, do not invent a trend.
        for metric in ["Renewable Energy Percentage","Water Recycled Percentage","Waste Recycled Percentage"]:
            x=g[g.Metric_Name==metric]["Metric_Value"].dropna()
            if len(x)>=2 and x.iloc[-1] < x.iloc[0]:
                signals.append(f"{metric} decreased between available observations")
        if "Confidence_Score" in g:
            low=(pd.to_numeric(g.Confidence_Score,errors="coerce")<0.7).sum()
            if low: signals.append(f"{low} extracted metric(s) have confidence below 0.70")
        if not s.empty and "Company_Code" in s:
            sg=s[s.Company_Code==code]
            if not sg.empty and "Sentiment_Class" in sg:
                neg=(sg.Sentiment_Class.astype(str).str.lower()=="negative").mean()
                if neg>0.30: signals.append(f"{neg:.0%} of analyzed ESG-relevant news is negative")
        rows.append({"Company_Code":code,"Company_Name":name,"Potential_Inconsistency_Count":len(signals),
                     "Potential_Signals":" | ".join(signals) if signals else "No automated inconsistency signal from available data",
                     "Interpretation":"Potential greenwashing signal requiring evidence review" if signals else "No automated signal",
                     "Caution":"Not a finding that the company is greenwashing; longitudinal and external evidence are required."})
    pd.DataFrame(rows).to_csv(output_csv,index=False)

if __name__ == "__main__":
    root=Path(__file__).resolve().parents[1]; out=root/"processed-data"
    run(out/"brsr_extracted_metrics.csv",out/"esg_news_sentiment.csv",out/"greenwashing_signals_v4.csv")
