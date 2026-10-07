# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, with sections:
- Added
- Changed
- Fixed
- Known Limitations

## [Phase 3] - 2026-08-27

### Added
- Expanded the configured technology-company cohort from 5 to 20.
- Added Phase 3 BRSR source manifest and canonical FY 2024-25 naming.
- Added multi-source downloader with validation and fallback handling.
- Added `helper-scripts/validate_phase3.py` pre-flight validation.
- Added `documentation/PHASE3_IMPLEMENTATION.md` and `documentation/PHASE3_CHANGE_LOG.md`.

### Changed
- Restored headquarters/major-office configuration required by Agent 2.
- Generalized NSE AUTO discovery rather than hard-coding a single company.
- Strengthened FY 2024-25 validation so a document cannot pass merely because it contains both years as comparative figures.
- Preserved the original V1 raw datasets.

### Fixed
- Phase 3 configuration no longer leaves Agent 2 without location fields.
- Downloader no longer activates a file before complete document validation.
- Old downloader audit-log schemas are preserved as a legacy log before a new schema is started.

### Known Limitations
- Hexaware remains pending because its currently discoverable 2025 annual report covers calendar year 2025 rather than the target April 2024-March 2025 reporting period.
- Agent 1 remains an automated extraction system with manual-review flags; it is not a substitute for human verification of every extracted BRSR metric.

## [Unreleased]

### Added
- None yet in this unreleased section.

### Changed
- None yet in this unreleased section.

### Fixed
- None yet in this unreleased section.

### Known Limitations
- CRITICAL-002: BRSR extraction quality still has missing/incorrect values.

## [v1.1] - 2026-03-15

### Added
- ESG news relevance filtering outputs:
  - `processed-data/esg_news_sentiment.csv` (ESG-relevant rows)
  - `processed-data/esg_news_rejected_articles.csv` (rejected non-ESG rows)
- Cross-validation contradiction report:
  - `processed-data/cross_validation_report.csv`
- Data quality gate report:
  - `processed-data/data_quality_report.csv`
- External benchmark comparison report:
  - `processed-data/external_benchmark_report.csv`
- Reproducibility and lineage artifacts:
  - `documentation/DATA_SOURCE_REGISTRY.md`
  - `processed-data/run_metadata.json`
  - `utils/lineage_tracker.py`

### Changed
- `agents/agent1_brsr_extractor.py` upgraded to hybrid extraction with confidence/validation/review flags.
- `agents/agent3_news_sentiment.py` upgraded with ESG relevance filtering logic.
- `agents/agent6_master_scorer.py` upgraded with:
  - contradiction engine and consistency scoring
  - centralized quality gate
  - external benchmark rank comparison
  - run metadata and dataset signature generation
- `agents/agent7_explainable_ai.py` upgraded with contradiction, quality, and benchmark-aware explanations.
- Session tracking and limitation documentation updated across daily logs.

### Fixed
- CRITICAL-001: ESG news validity issue addressed with relevance filtering.
- CRITICAL-003: Cross-source contradiction checks implemented.
- CRITICAL-004: Pre-scoring quality validation pipeline implemented.
- Limitation-5: External benchmarking comparison implemented.
- Limitation-6: Reproducibility and data lineage capture implemented.

### Known Limitations
- CRITICAL-002: BRSR extraction quality improved but still partially unresolved for some metrics.

## [v1.0] - 2026-03-13

### Added
- End-to-end 7-agent ESG pipeline:
  - Agent 1: BRSR extraction
  - Agent 2: Environmental risk mapping
  - Agent 3: News sentiment
  - Agent 4: Stock correlation
  - Agent 5: Greenwashing detection
  - Agent 6: Master ESG scoring
  - Agent 7: Explainable AI outputs
- Structured repository setup with `.gitignore`.
- Documentation and daily log framework.

### Changed
- Project organized into clear folders: `agents/`, `utils/`, `helper-scripts/`, `documentation/`, `processed-data/`, `raw-datasets/`, `brsr-pdfs/`.

### Fixed
- Session log synchronization and cleanup in `documentation/daily_log/`.

### Known Limitations
- CRITICAL-001: ESG news dataset includes non-ESG market articles.
- CRITICAL-002: BRSR extraction has reliability gaps for some metrics.
- CRITICAL-003: No robust cross-source contradiction engine.
- CRITICAL-004: Incomplete pre-scoring quality validation pipeline.

## V4 - research-grounded ESG analysis upgrade (2026-09-23)
- Added `v4_core/` with direction-aware, cohort-normalized ESG scoring.
- Added explicit data completeness, validation coverage and extraction-confidence reporting.
- Added mathematical metric contribution explanations tied to BRSR source pages.
- Added potential disclosure-performance inconsistency signals with cautious wording.
- Added optional LLM Supervisor routing layer for dynamic specialist selection.
- Added V4 methodology/research documentation.
