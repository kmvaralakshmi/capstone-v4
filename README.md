# Explainable Multi-Agent ESG Risk Analysis System — Phase 3

Phase 3 extends the V1 seven-agent ESG pipeline from 5 companies to a fixed cohort of **20 Indian technology companies** while preserving the original V1 raw datasets and multi-agent architecture.

## Phase 3 rules

1. **BRSR is the primary company ESG source.**
2. Target reporting period: **FY 2024-25** for April-March reporters.
3. Source priority is defined in `utils/brsr_manifest.py` and may use NSE, BSE, or the company's official website.
4. One company + one target FY = **one canonical active PDF**: `<CODE>_BR_24-25.pdf`.
5. A valid canonical PDF is never overwritten or duplicated.
6. A replacement is activated only after PDF, company, BRSR-content and FY validation all pass.
7. The original V1 raw datasets remain unchanged.
8. Agent 1 creates review placeholders when a company has no validated PDF, so the 20-company cohort remains visible in downstream outputs.

## Cohort

TCS, Infosys, Wipro, HCL Technologies, Tech Mahindra, LTIMindtree, Mphasis, Persistent Systems, Coforge, L&T Technology Services, Tata Elxsi, Oracle Financial Services Software, KPIT Technologies, Cyient, Birlasoft, Zensar Technologies, Tata Technologies, Happiest Minds Technologies, Sonata Software, and Hexaware Technologies.

## Important Hexaware note

Hexaware reports on a calendar-year basis. Its currently discoverable 2025 annual report covers **1 January 2025–31 December 2025**, so it must not be silently treated as FY 2024-25. The Phase 3 downloader therefore leaves Hexaware pending until a document whose reporting period is genuinely comparable to the target period is identified.

## Project structure

```text
capstone-implementation/
├── agents/
│   ├── agent1_brsr_extractor.py
│   ├── agent2_environmental_risk.py
│   ├── agent3_news_sentiment.py
│   ├── agent4_stock_correlation.py
│   ├── agent5_greenwashing_detector.py
│   ├── agent6_master_scorer.py
│   └── agent7_explainable_ai.py
├── helper-scripts/
│   ├── download_brsr_reports.py
│   ├── download_brsr_reports.ps1
│   └── validate_phase3.py
├── utils/
│   ├── config.py
│   ├── brsr_manifest.py
│   ├── pdf_extractor.py
│   ├── data_validator.py
│   └── lineage_tracker.py
├── brsr-pdfs/
├── raw-datasets/              # preserved V1 datasets
├── processed-data/            # generated agent outputs
├── demo-output/               # copied demo outputs
├── documentation/
├── demo.py
├── requirements.txt
├── CHANGELOG.md
└── README.md
```

## Setup

From the project root:

```bat
python -m pip install -r requirements.txt
```

## Phase 3 execution

### 1. Check the 20-company configuration

```bat
python utils/config.py
```

Expected company count:

```text
Companies: 20
```

### 2. Download/validate BRSR reports

```bat
python helper-scripts/download_brsr_reports.py
```

The downloader uses the configured source priority, rejects HTML responses, streams large PDFs safely, validates documents before activation, and never creates `_1`, `_2`, `_3` duplicates.

### 3. Run pre-flight validation

```bat
python helper-scripts/validate_phase3.py
```

### 4. Run the full seven-agent pipeline

```bat
python demo.py
```

The agents execute in this order:

```text
Agent 1 → BRSR extraction
Agent 2 → Environmental/location risk
Agent 3 → ESG news sentiment
Agent 4 → Stock/ESG correlation
Agent 5 → Greenwashing detection
Agent 6 → Master ESG scoring + quality gate
Agent 7 → Explainable AI report
```

## Outputs

Generated files are written to `processed-data/` and copied to `demo-output/` by `demo.py`.

Important outputs include:

- `brsr_extracted_metrics.csv`
- `company_location_environmental_risk.csv`
- `esg_news_sentiment.csv`
- `esg_news_rejected_articles.csv`
- `stock_esg_correlation.csv`
- `greenwashing_detection.csv`
- `cross_validation_report.csv`
- `data_quality_report.csv`
- `external_benchmark_report.csv`
- `esg_master_scores.csv`
- `multi_agent_explanations.csv`
- `run_metadata.json`

## Reproducibility

`utils/lineage_tracker.py` records input signatures, generated-output signatures, runtime information and Git information when available.

See:

- `documentation/PHASE3_IMPLEMENTATION.md`
- `documentation/PHASE3_CHANGE_LOG.md`
- `CHANGELOG.md`


## PHASE 3 WEB APPLICATION

The completed Phase 3 package now includes a frontend and backend.

### Quick start (Windows)
```text
setup_windows.bat
run_phase3.bat
start_backend.bat
```
Then open `http://127.0.0.1:8000`.

### If you only want to use the already-downloaded reports
```text
run_phase3_without_download.bat
```

### API
- `GET /api/health`
- `GET /api/summary`
- `GET /api/companies`
- `GET /api/company/{code}`
- `GET /api/download-status`
- `POST /api/run?download=true`
- `GET /api/run-status`
