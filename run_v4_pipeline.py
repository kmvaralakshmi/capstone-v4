"""Run deterministic V4 scoring/XAI/greenwashing modules.

Use --supervisor to additionally start the LLM supervisor after OPENAI_API_KEY is set.
"""
import argparse
from pathlib import Path
from v4_core.esg_scoring import run as run_scoring
from v4_core.explainability_v4 import build_explanations
from v4_core.greenwashing_v4 import run as run_greenwashing

def main():
    root=Path(__file__).resolve().parent; out=root/"processed-data"
    source=out/"brsr_extracted_metrics.csv"
    if not source.exists():
        source=out/"brsr_metrics.csv"
    run_scoring(str(source),str(out))
    build_explanations(out/"esg_scores_v4.csv",out/"esg_metric_contributions_v4.csv",source,out/"esg_explanations_v4.csv")
    sentiment=out/"esg_news_sentiment.csv"
    run_greenwashing(str(source),str(sentiment),out/"greenwashing_signals_v4.csv")
    print("V4 deterministic analysis complete.")
    print(f"Scores: {out/'esg_scores_v4.csv'}")
    print(f"Contributions: {out/'esg_metric_contributions_v4.csv'}")
    print(f"Explanations: {out/'esg_explanations_v4.csv'}")
    print(f"Greenwashing signals: {out/'greenwashing_signals_v4.csv'}")
    if args.supervisor:
        from v4_core.supervisor import Supervisor
        import os
        if not os.getenv("OPENAI_API_KEY"):
            raise SystemExit("OPENAI_API_KEY is required for --supervisor")
        s=Supervisor(); trace=s.run("Coordinate the ESG analysis and decide the next specialist actions.", "V4 deterministic scoring outputs are ready; validation and explanation artifacts exist.")
        import json
        (out/"supervisor_trace_v4.json").write_text(json.dumps(trace,indent=2),encoding="utf-8")

if __name__=="__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--supervisor",action="store_true"); args=parser.parse_args(); main()
