# Capstone V4: methodology update

## Architecture
V4 uses a hybrid autonomous multi-agent design. An LLM supervisor dynamically selects specialist work. Deterministic tools perform PDF extraction, validation, normalization, scoring and evidence calculations. This is intentionally auditable.

## ESG scoring
- BRSR/BRSR-Core-aligned metrics are inputs; the project score is explicitly a research score, not an official SEBI rating.
- Metric direction is explicit (`higher`, `lower`, or `context`).
- Cohort min-max normalization is used only for comparable numeric metrics.
- Equal metric weighting within each pillar is transparent; pillar weights default to one-third each and are stored in the methodology JSON.
- Missing values are not treated as zero.
- Data completeness, validation coverage and extraction confidence are reported separately.

## Explainability
V4 explains the deterministic score through exact metric contributions, pillar contributions and BRSR source-page metadata. An LLM may verbalize these facts, but it is not allowed to invent the underlying score.

## Greenwashing
V4 reports potential disclosure/performance inconsistency signals. It does not label a company as greenwashing without longitudinal and external evidence.

## Research basis
The redesign was informed by the uploaded reference collection and external research including ESGAgent (2026), SHAP-based ESG explainability research, recent ESG rating prediction work using XGBoost/SHAP, trustworthy LLM sustainability-report analysis, BRSR-focused Indian ESG research, and greenwashing detection research.

## Important limitation
A single FY of BRSR data is insufficient for a genuine performance trend. V4 therefore avoids inventing year-over-year trends when only one observation exists.
