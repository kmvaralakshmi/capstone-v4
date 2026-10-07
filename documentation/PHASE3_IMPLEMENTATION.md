# Phase 3 Implementation Record

## Scope

Phase 3 is the production-style expansion of the V1 explainable multi-agent ESG system from five companies to twenty technology companies.

## Preserved V1 inputs

The existing raw datasets were retained:

- Air Quality Data in India (2015-2024)
- Real-Time Air Quality Index (AQI) India 2023-2025
- Stock Market Sensex & Nifty All-time Dataset
- Zenodo Indian ESG/news dataset

No replacement `indian_companies_esg_scores.csv` dataset was introduced as an input.

## Company-level ESG source

BRSR/annual-report documents containing BRSR disclosures are stored in `brsr-pdfs/`. The downloader uses a manifest so the source URL, source priority and target company are auditable.

### Canonical naming

```text
<CODE>_BR_24-25.pdf
```

### Activation rule

A downloaded document becomes canonical only after:

- PDF signature validation
- PDF readability/page validation
- company identity validation
- BRSR content validation
- FY 2024-25 reporting-period validation

An invalid existing canonical document is not deleted until a replacement has passed all validation gates.

## Multi-source fallback

The manifest supports source priority. A source can be a direct URL or `AUTO` for NSE discovery. The intended order is:

1. NSE
2. BSE
3. Company official website

Company-specific source definitions may add a more precise NSE annual-report or official BRSR fallback where the exchange BRSR listing does not expose a usable attachment.

## Phase 3 company coverage

The configuration contains 20 companies. At the time this package was prepared, 19 canonical FY 2024-25 PDFs were already present and validated in the supplied project ZIP. Hexaware remains pending because its current 2025 report is for the calendar year 2025 rather than the April 2024–March 2025 target period.

This is intentional: the system must not mix reporting periods merely to reach a 20/20 file count.

## Environmental-location input

The original V1 headquarters/major-office locations for the five V1 companies are retained. For the fifteen Phase 3 additions, the configuration uses a representative headquarters city and no invented multi-city footprint. This keeps AQI scoring conservative when a documented office list has not been added to the project evidence base.

## Downstream quality controls

The existing V1.1 quality controls remain part of Phase 3:

- extraction confidence and manual-review flags
- ESG news relevance filtering
- cross-validation/contradiction reporting
- pre-scoring data-quality gate
- external benchmark comparison
- lineage/run metadata
- explainable final outputs

## Execution order

```text
BRSR downloader
      ↓
Phase 3 pre-flight
      ↓
Agent 1
      ↓
Agent 2
      ↓
Agent 3
      ↓
Agent 4
      ↓
Agent 5
      ↓
Agent 6
      ↓
Agent 7
```
