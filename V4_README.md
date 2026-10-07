# Capstone V4

This version improves the project in four areas:

1. **Autonomous coordination:** an LLM supervisor can dynamically route work to specialist agents.
2. **ESG scoring:** transparent direction-aware normalization, pillar aggregation, missing-data handling, completeness and confidence reporting.
3. **Explainability:** mathematical metric contributions and BRSR evidence pages are used as the source of explanations; an LLM is not allowed to invent the score.
4. **Greenwashing analysis:** reports potential disclosure-performance inconsistency signals rather than making unsupported accusations.

## Quick run

```powershell
.venv\Scripts\activate
python run_v4_pipeline.py
```

For the LLM supervisor:

```powershell
python run_v4_pipeline.py --supervisor
```

Set `OPENAI_API_KEY` in `.env` before using `--supervisor`.

## Outputs

- `processed-data/esg_scores_v4.csv`
- `processed-data/esg_metric_contributions_v4.csv`
- `processed-data/esg_explanations_v4.csv`
- `processed-data/greenwashing_signals_v4.csv`
- `processed-data/esg_scoring_methodology_v4.json`
- `processed-data/supervisor_trace_v4.json` (when supervisor is run)
