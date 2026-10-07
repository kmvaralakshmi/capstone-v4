"""
Agent 1: BRSR Extraction Agent
This agent handles extracting ESG metrics from BRSR PDF reports.
"""

import sys
from pathlib import Path
import pandas as pd
from datetime import datetime
import time
from typing import Dict, List, Optional, Tuple

# Need to add parent directory so we can import from utils folder
sys.path.append(str(Path(__file__).parent.parent))

from utils.config import COMPANIES, ESG_METRICS, BRSR_PDF_DIR, PROCESSED_DATA_DIR, OUTPUT_FILES
from utils.pdf_extractor import (
    extract_text_from_pdf,
    extract_tables_from_pdf,
    search_text_in_pdf,
    extract_numbers_from_text,
    extract_percentage_from_text,
    get_pdf_metadata
)
from utils.data_validator import validate_numeric_value, validate_percentage


class BRSRExtractionAgent:
    """
    Main agent class for handling BRSR reports.
    Right now it just creates a template for manual data entry.
    """
    
    def __init__(self):
        # Load configuration from config file
        self.companies = COMPANIES
        self.metrics = ESG_METRICS
        self.brsr_dir = BRSR_PDF_DIR
        self.output_dir = PROCESSED_DATA_DIR
        # Will store all extracted data rows here
        self.extracted_data = []
        self.timing_data = []

    def _extract_value_from_text(self, text: str, metric_info: Dict, keyword: Optional[str] = None) -> Optional[float]:
        """Extract a candidate value from text using keyword-aware regex first, then generic parsing."""
        if not text:
            return None

        clean_text = str(text).replace("\n", " ")

        # Prefer numbers that appear near the matched keyword.
        if keyword:
            escaped_keyword = keyword.replace("(", "\\(").replace(")", "\\)")
            if metric_info['unit'] == '%':
                pattern = rf"{escaped_keyword}[^0-9%]{{0,80}}([0-9,]+\.?[0-9]*)\s*%"
            else:
                pattern = rf"{escaped_keyword}[^0-9]{{0,80}}([0-9,]+\.?[0-9]*)"
            match = pd.Series([clean_text]).str.extract(pattern, flags=0).iloc[0, 0]
            if pd.notna(match):
                try:
                    return float(str(match).replace(",", ""))
                except ValueError:
                    pass

        # Fallback: generic extraction from snippet.
        if metric_info['unit'] == '%':
            return extract_percentage_from_text(clean_text)

        numbers = extract_numbers_from_text(clean_text)
        return numbers[0] if numbers else None

    def _extract_from_tables(
        self,
        pdf_path: Path,
        search_keywords: List[str],
        metric_info: Dict,
        page_numbers: Optional[List[int]] = None,
        tables_by_page: Optional[Dict[int, List]] = None,
    ) -> Tuple[Optional[float], Optional[int], Optional[str]]:
        """Search already-extracted tables, avoiding repeated PDF parsing."""
        try:
            if tables_by_page is None:
                tables_by_page = extract_tables_from_pdf(
                    pdf_path, page_numbers=page_numbers
                )
        except BaseException:
            return None, None, None

        for page_num, tables in tables_by_page.items():
            for table in tables:
                for row in table:
                    row_text = " ".join(
                        [str(cell) for cell in row if cell is not None]
                    )
                    row_text_lower = row_text.lower()
                    for keyword in search_keywords:
                        if keyword.lower() in row_text_lower:
                            value = self._extract_value_from_text(
                                row_text, metric_info, keyword
                            )
                            if value is not None:
                                return value, page_num, keyword
        return None, None, None

    def _extract_from_context_search(self, search_results: Dict[str, List[Tuple[int, str]]], metric_info: Dict) -> Tuple[Optional[float], Optional[int], Optional[str]]:
        """Try keyword-context search extraction and return (value, page, matched_keyword)."""
        for keyword, occurrences in search_results.items():
            for page_num, context in occurrences:
                value = self._extract_value_from_text(context, metric_info, keyword)
                if value is not None:
                    return value, page_num, keyword

        return None, None, None

    def _extract_from_text_window(self, text_by_page: Dict[int, str], search_keywords: List[str], metric_info: Dict) -> Tuple[Optional[float], Optional[int], Optional[str]]:
        """Fallback extraction by scanning lines around matched keyword in full page text."""
        for page_num, page_text in text_by_page.items():
            if not page_text:
                continue

            lines = [line.strip() for line in str(page_text).split("\n") if line.strip()]
            for idx, line in enumerate(lines):
                line_lower = line.lower()
                for keyword in search_keywords:
                    if keyword.lower() in line_lower:
                        # Search current line + next line for value.
                        snippet = line
                        if idx + 1 < len(lines):
                            snippet += " " + lines[idx + 1]
                        value = self._extract_value_from_text(snippet, metric_info, keyword)
                        if value is not None:
                            return value, page_num, keyword

        return None, None, None

    def _search_terms_in_cached_text(self, text_by_page: Dict[int, str], search_terms: List[str]) -> Dict[str, List[Tuple[int, str]]]:
        """Search terms in cached page text to avoid repeated PDF parsing."""
        results = {term: [] for term in search_terms}

        for page_num, text in text_by_page.items():
            if not text:
                continue

            text_str = str(text)
            text_lower = text_str.lower()

            for term in search_terms:
                term_lower = term.lower()
                idx = text_lower.find(term_lower)
                if idx >= 0:
                    start = max(0, idx - 50)
                    end = min(len(text_str), idx + len(term) + 50)
                    context = text_str[start:end].replace('\n', ' ')
                    results[term].append((page_num, context))

        return results

    def _validate_metric_value(self, metric_name: str, metric_info: Dict, value: Optional[float]) -> Tuple[str, bool, str]:
        """Validate extracted value and return (validation_status, needs_review, note)."""
        if value is None:
            return "Not Found", True, "No value extracted"

        if metric_info['unit'] == '%':
            is_valid, clean_val = validate_percentage(value)
            if not is_valid:
                return "Invalid Range", True, "Percentage outside 0-100"

        # Metric-specific basic sanity checks.
        bounds_map = {
            'Board Size': (1, 100),
            'Total Employees': (100, 10000000),
            'Health and Safety Incidents': (0, 100000),
            'Audit Committee Size': (1, 50),
            'Board Meeting Frequency': (1, 40),
            'Ethics Policy Violations': (0, 100000),
            'Training Hours per Employee': (0, 1000),
        }

        if metric_name in bounds_map:
            min_val, max_val = bounds_map[metric_name]
            is_valid, _ = validate_numeric_value(value, min_val=min_val, max_val=max_val)
            if not is_valid:
                return "Outlier/Suspect", True, f"Outside expected bounds {min_val}-{max_val}"

        # Special guardrail for known sensitive percentage metric.
        if metric_name == 'Female Employee Percentage' and value < 5:
            return "Outlier/Suspect", True, "Very low value, verify manually"

        return "Valid", False, "Within expected range"

    def _confidence_from_method(self, method: str, needs_review: bool) -> float:
        """Estimate confidence score from extraction method and validation result."""
        base = {
            'table': 0.90,
            'keyword_context': 0.75,
            'text_window': 0.60,
            'not_found': 0.0,
        }.get(method, 0.50)

        if needs_review:
            base = max(0.20, base - 0.35)

        return round(base, 2)
        
    def check_pdf_availability(self) -> Dict[str, bool]:
        """
        Just checking if we have all the PDF files we need.
        Returns a dictionary showing which companies have PDFs available.
        """
        availability = {}
        
        for company_code, company_info in self.companies.items():
            pdf_path = self.brsr_dir / company_info['brsr_file']
            availability[company_code] = pdf_path.exists()
            
        return availability
        
    def extract_metric_from_pdf(self, pdf_path: Path, company_code: str,
                               metric_name: str, metric_info: Dict,
                               text_by_page: Dict[int, str]) -> Dict:
        """
        Automatically extract a metric value from the PDF by searching for keywords.
        Uses pattern matching to find numbers, percentages, and values.
        """
        
        metric_value = None
        page_number = None
        matched_keyword = None
        extraction_method = 'not_found'
        notes = f"Searched in: {metric_info['typical_section']}"
        
        # Define search keywords based on metric name
        search_keywords = self._get_search_keywords(metric_name)
        
        # Build search results once and reuse for targeted extraction fallbacks.
        search_results = self._search_terms_in_cached_text(text_by_page, search_keywords)

        candidate_pages: List[int] = []
        for occurrences in search_results.values():
            for page_num, _ in occurrences:
                if page_num not in candidate_pages:
                    candidate_pages.append(page_num)
                if len(candidate_pages) >= 10:
                    break
            if len(candidate_pages) >= 10:
                break

        # 1) Table-first extraction (targeted pages only)
        value, page_num, keyword = self._extract_from_tables(
            pdf_path,
            search_keywords,
            metric_info,
            page_numbers=candidate_pages if candidate_pages else None,
        )
        if value is not None:
            metric_value = value
            page_number = page_num
            matched_keyword = keyword
            extraction_method = 'table'

        # 2) Keyword-context fallback
        if metric_value is None:
            value, page_num, keyword = self._extract_from_context_search(search_results, metric_info)
            if value is not None:
                metric_value = value
                page_number = page_num
                matched_keyword = keyword
                extraction_method = 'keyword_context'

        # 3) Text-window fallback
        if metric_value is None:
            value, page_num, keyword = self._extract_from_text_window(text_by_page, search_keywords, metric_info)
            if value is not None:
                metric_value = value
                page_number = page_num
                matched_keyword = keyword
                extraction_method = 'text_window'

        validation_status, needs_review, validation_note = self._validate_metric_value(metric_name, metric_info, metric_value)
        confidence_score = self._confidence_from_method(extraction_method, needs_review)
        
        if metric_value is None:
            status = 'Not found'
            notes = "Not found in PDF. Check manually."
        elif needs_review:
            status = 'Auto-extracted (Needs Review)'
            notes = f"{validation_note}; Method: {extraction_method}; Keyword: {matched_keyword}"
        else:
            status = 'Auto-extracted'
            notes = f"Method: {extraction_method}; Keyword: {matched_keyword}; {validation_note}"
        
        return {
            'Company_Code': company_code,
            'Company_Name': self.companies[company_code]['full_name'],
            'Metric_Category': self._get_metric_category(metric_name),
            'Metric_Name': metric_name,
            'Metric_Value': metric_value,
            'Unit': metric_info['unit'],
            'Page_Number': page_number,
            'Verified': status,
            'Extraction_Method': extraction_method,
            'Confidence_Score': confidence_score,
            'Validation_Status': validation_status,
            'Needs_Manual_Review': needs_review,
            'Extraction_Date': datetime.now().strftime('%Y-%m-%d'),
            'Notes': notes
        }
    
    def _get_search_keywords(self, metric_name: str) -> List[str]:
        """
        Generate search keywords for each metric.
        Returns a list of terms to search for in the PDF.
        """
        keyword_map = {
            'Total Energy Consumption': ['total energy', 'energy consumption', 'electricity'],
            'Renewable Energy Percentage': ['renewable energy', 'renewable source', 'solar', 'wind energy'],
            'Total Water Consumption': ['total water', 'water consumption', 'water withdrawn'],
            'Water Recycled Percentage': ['water recycled', 'water reused', 'recycling of water'],
            'Total Waste Generated': ['total waste', 'waste generated', 'hazardous waste'],
            'Waste Recycled Percentage': ['waste recycled', 'waste diverted', 'recycling'],
            'Total Employees': ['total employees', 'permanent employees', 'workforce'],
            'Female Employee Percentage': ['women employees', 'female employees', 'gender diversity'],
            'Employee Turnover Rate': ['attrition', 'turnover', 'employee retention'],
            'Training Hours per Employee': ['training hours', 'average training', 'skill development'],
            'Health and Safety Incidents': ['safety incidents', 'lost time injury', 'accidents'],
            'CSR Expenditure': ['csr spent', 'csr expenditure', 'corporate social responsibility'],
            'Board Size': ['board of directors', 'board members', 'board composition'],
            'Independent Directors Percentage': ['independent directors', 'non-executive'],
            'Female Directors Percentage': ['women directors', 'female board members'],
            'Board Meeting Frequency': ['board meetings held', 'meetings conducted'],
            'Audit Committee Size': ['audit committee', 'audit members'],
            'Ethics Policy Violations': ['complaints', 'ethics violations', 'grievances']
        }
        
        return keyword_map.get(metric_name, [metric_name.lower()])
        
    def _get_metric_category(self, metric_name: str) -> str:
        """Get category (E/S/G) for a metric"""
        for category, metrics in self.metrics.items():
            for metric in metrics:
                if metric['name'] == metric_name:
                    return category
        return "Unknown"
        
    def process_all_companies(self, mode: str = 'auto') -> pd.DataFrame:
        """Process all companies with cached PDF text/tables and timing."""
        overall_start = time.perf_counter()
        availability = self.check_pdf_availability()
        total_companies = len(self.companies)

        for index, (company_code, company_info) in enumerate(
            self.companies.items(), start=1
        ):
            company_start = time.perf_counter()

            print("\n" + "=" * 70)
            print(
                f"[{index}/{total_companies}] "
                f"{company_code}: {company_info['full_name']}"
            )
            print("=" * 70)

            if not availability[company_code]:
                print("NO PDF - creating placeholder rows")
                placeholder_count = 0

                for category, metrics in self.metrics.items():
                    for metric_info in metrics:
                        self.extracted_data.append({
                            'Company_Code': company_code,
                            'Company_Name': company_info.get(
                                'full_name', company_code
                            ),
                            'Metric_Category': self._get_metric_category(
                                metric_info['name']
                            ),
                            'Metric_Name': metric_info['name'],
                            'Metric_Value': None,
                            'Unit': metric_info['unit'],
                            'Page_Number': None,
                            'Verified': 'No PDF - Placeholder',
                            'Extraction_Method': 'not_found',
                            'Confidence_Score': 0.0,
                            'Validation_Status': 'Not Found',
                            'Needs_Manual_Review': True,
                            'Extraction_Date': datetime.now().strftime(
                                '%Y-%m-%d'
                            ),
                            'Notes': (
                                'BRSR PDF not available; populate from '
                                'alternate source or upload PDF'
                            )
                        })
                        placeholder_count += 1

                elapsed = time.perf_counter() - company_start
                self.timing_data.append({
                    "Company_Code": company_code,
                    "Company_Name": company_info.get(
                        "full_name", company_code
                    ),
                    "PDF_Pages": 0,
                    "PDF_Size_MB": 0,
                    "Text_Extraction_Seconds": 0,
                    "Keyword_Indexing_Seconds": 0,
                    "Candidate_Page_Seconds": 0,
                    "Table_Extraction_Seconds": 0,
                    "Metric_Extraction_Seconds": 0,
                    "Validation_Seconds": 0,
                    "Company_Total_Seconds": round(elapsed, 3),
                    "Metrics_Total": placeholder_count,
                    "Metrics_Extracted": 0,
                    "Metrics_Not_Found": placeholder_count,
                    "Status": "NO PDF - PLACEHOLDERS",
                })
                print(f"Company total: {elapsed:.2f} sec")
                continue

            pdf_path = self.brsr_dir / company_info['brsr_file']

            try:
                pdf_size_mb = pdf_path.stat().st_size / (1024 * 1024)
            except OSError:
                pdf_size_mb = 0

            pdf_pages = 0
            try:
                metadata = get_pdf_metadata(pdf_path)
                if isinstance(metadata, dict):
                    pdf_pages = (
                        metadata.get("pages")
                        or metadata.get("page_count")
                        or metadata.get("num_pages")
                        or 0
                    )
            except BaseException:
                pass

            # 1. Extract text ONCE.
            # For larger annual reports, we do an early-page scan first to avoid
            # the full-document parsing bottleneck. Most BRSR metrics appear in the
            # initial sections and can often be found well before the end of the PDF.
            stage = time.perf_counter()
            initial_scan_limit = min(pdf_pages, 30) if pdf_pages else None
            if initial_scan_limit and pdf_pages > initial_scan_limit:
                print(
                    f"Large PDF detected ({pdf_pages} pages): using first "
                    f"{initial_scan_limit} pages for initial text scan"
                )
                text_by_page = extract_text_from_pdf(
                    pdf_path,
                    page_numbers=list(range(1, initial_scan_limit + 1))
                )
            else:
                text_by_page = extract_text_from_pdf(pdf_path)
            text_seconds = time.perf_counter() - stage

            if not pdf_pages:
                pdf_pages = len(text_by_page)

            print(
                f"Text extraction: {text_seconds:.2f} sec "
                f"({len(text_by_page)} pages)"
            )

            # 2. Build one keyword index for every metric.
            stage = time.perf_counter()
            metric_keyword_map = {}
            all_terms = []

            for category, metrics in self.metrics.items():
                for metric_info in metrics:
                    name = metric_info['name']
                    keywords = self._get_search_keywords(name)
                    metric_keyword_map[name] = keywords
                    for keyword in keywords:
                        if keyword not in all_terms:
                            all_terms.append(keyword)

            all_search_results = self._search_terms_in_cached_text(
                text_by_page, all_terms
            )
            keyword_seconds = time.perf_counter() - stage

            print(
                f"Keyword indexing: {keyword_seconds:.2f} sec "
                f"({len(all_terms)} terms)"
            )

            # 3. Find candidate pages for ALL metrics before table parsing.
            stage = time.perf_counter()
            metric_search_results = {}
            all_candidate_pages = set()

            for metric_name, keywords in metric_keyword_map.items():
                results = {
                    keyword: all_search_results.get(keyword, [])
                    for keyword in keywords
                }
                metric_search_results[metric_name] = results

                count = 0
                for occurrences in results.values():
                    for page_num, _context in occurrences:
                        all_candidate_pages.add(page_num)
                        count += 1
                        if count >= 10:
                            break
                    if count >= 10:
                        break

            candidate_seconds = time.perf_counter() - stage

            print(
                f"Candidate page search: {candidate_seconds:.2f} sec "
                f"({len(all_candidate_pages)} unique pages)"
            )

            # 4. Extract tables ONCE for the union of candidate pages.
            stage = time.perf_counter()
            tables_by_page = {}

            if all_candidate_pages:
                try:
                    tables_by_page = extract_tables_from_pdf(
                        pdf_path,
                        page_numbers=sorted(all_candidate_pages)
                    )
                except BaseException as exc:
                    print(
                        f"Table extraction warning: "
                        f"{type(exc).__name__}: {exc}"
                    )

            table_seconds = time.perf_counter() - stage

            print(
                f"Table extraction: {table_seconds:.2f} sec "
                f"({len(tables_by_page)} pages)"
            )

            # 5. Extract all metrics from cached text/tables.
            metric_stage = time.perf_counter()
            company_extracted = 0
            company_not_found = 0
            validation_total = 0.0

            metrics_total = sum(
                len(metrics) for metrics in self.metrics.values()
            )

            for category, metrics in self.metrics.items():
                for metric_info in metrics:
                    metric_name = metric_info['name']
                    keywords = metric_keyword_map[metric_name]
                    search_results = metric_search_results[metric_name]

                    metric_value = None
                    page_number = None
                    matched_keyword = None
                    extraction_method = 'not_found'

                    # Table extraction uses the cached tables.
                    value, page_num, keyword = self._extract_from_tables(
                        pdf_path,
                        keywords,
                        metric_info,
                        tables_by_page=tables_by_page
                    )

                    if value is not None:
                        metric_value = value
                        page_number = page_num
                        matched_keyword = keyword
                        extraction_method = 'table'

                    if metric_value is None:
                        value, page_num, keyword = (
                            self._extract_from_context_search(
                                search_results, metric_info
                            )
                        )
                        if value is not None:
                            metric_value = value
                            page_number = page_num
                            matched_keyword = keyword
                            extraction_method = 'keyword_context'

                    if metric_value is None:
                        value, page_num, keyword = (
                            self._extract_from_text_window(
                                text_by_page, keywords, metric_info
                            )
                        )
                        if value is not None:
                            metric_value = value
                            page_number = page_num
                            matched_keyword = keyword
                            extraction_method = 'text_window'

                    validation_start = time.perf_counter()
                    (
                        validation_status,
                        needs_review,
                        validation_note
                    ) = self._validate_metric_value(
                        metric_name, metric_info, metric_value
                    )
                    validation_total += (
                        time.perf_counter() - validation_start
                    )

                    confidence_score = self._confidence_from_method(
                        extraction_method, needs_review
                    )

                    if metric_value is None:
                        status = 'Not found'
                        notes = 'Not found in PDF. Check manually.'
                        company_not_found += 1
                    elif needs_review:
                        status = 'Auto-extracted (Needs Review)'
                        notes = (
                            f"{validation_note}; "
                            f"Method: {extraction_method}; "
                            f"Keyword: {matched_keyword}"
                        )
                        company_extracted += 1
                    else:
                        status = 'Auto-extracted'
                        notes = (
                            f"Method: {extraction_method}; "
                            f"Keyword: {matched_keyword}; "
                            f"{validation_note}"
                        )
                        company_extracted += 1

                    self.extracted_data.append({
                        'Company_Code': company_code,
                        'Company_Name': self.companies[
                            company_code
                        ]['full_name'],
                        'Metric_Category': self._get_metric_category(
                            metric_name
                        ),
                        'Metric_Name': metric_name,
                        'Metric_Value': metric_value,
                        'Unit': metric_info['unit'],
                        'Page_Number': page_number,
                        'Verified': status,
                        'Extraction_Method': extraction_method,
                        'Confidence_Score': confidence_score,
                        'Validation_Status': validation_status,
                        'Needs_Manual_Review': needs_review,
                        'Extraction_Date': datetime.now().strftime(
                            '%Y-%m-%d'
                        ),
                        'Notes': notes
                    })

            metric_seconds = time.perf_counter() - metric_stage
            company_seconds = time.perf_counter() - company_start

            print(f"Metric extraction: {metric_seconds:.2f} sec")
            print(f"Validation time: {validation_total:.2f} sec")
            print(
                f"Metrics extracted: "
                f"{company_extracted}/{metrics_total}"
            )
            print(
                f"Metrics not found: "
                f"{company_not_found}/{metrics_total}"
            )
            print(f"Company total: {company_seconds:.2f} sec")

            self.timing_data.append({
                "Company_Code": company_code,
                "Company_Name": company_info["full_name"],
                "PDF_Pages": pdf_pages,
                "PDF_Size_MB": round(pdf_size_mb, 3),
                "Text_Extraction_Seconds": round(text_seconds, 3),
                "Keyword_Indexing_Seconds": round(keyword_seconds, 3),
                "Candidate_Page_Seconds": round(candidate_seconds, 3),
                "Table_Extraction_Seconds": round(table_seconds, 3),
                "Metric_Extraction_Seconds": round(metric_seconds, 3),
                "Validation_Seconds": round(validation_total, 3),
                "Company_Total_Seconds": round(company_seconds, 3),
                "Metrics_Total": metrics_total,
                "Metrics_Extracted": company_extracted,
                "Metrics_Not_Found": company_not_found,
                "Status": "COMPLETED",
            })

        overall_seconds = time.perf_counter() - overall_start

        print("\n" + "=" * 70)
        print("AGENT 1 OVERALL PERFORMANCE")
        print("=" * 70)
        print(
            f"Companies processed : "
            f"{len(self.companies)}/{len(self.companies)}"
        )
        print(f"Total time          : {overall_seconds:.2f} sec")
        print(
            f"Total time          : "
            f"{overall_seconds / 60:.2f} minutes"
        )
        if self.companies:
            print(
                f"Average/company    : "
                f"{overall_seconds / len(self.companies):.2f} sec"
            )
        print("=" * 70)

        return pd.DataFrame(self.extracted_data)

    def save_timing_csv(
        self,
        filename: str = "agent1_extraction_timing.csv"
    ) -> Path:
        """Save measured per-company Agent 1 performance."""
        output_path = self.output_dir / filename

        columns = [
            "Company_Code",
            "Company_Name",
            "PDF_Pages",
            "PDF_Size_MB",
            "Text_Extraction_Seconds",
            "Keyword_Indexing_Seconds",
            "Candidate_Page_Seconds",
            "Table_Extraction_Seconds",
            "Metric_Extraction_Seconds",
            "Validation_Seconds",
            "Company_Total_Seconds",
            "Metrics_Total",
            "Metrics_Extracted",
            "Metrics_Not_Found",
            "Status",
        ]

        timing_df = pd.DataFrame(self.timing_data)

        if timing_df.empty:
            timing_df = pd.DataFrame(columns=columns)
        else:
            for column in columns:
                if column not in timing_df.columns:
                    timing_df[column] = None
            timing_df = timing_df[columns]

        timing_df.to_csv(output_path, index=False)
        return output_path

    def save_to_csv(self, df: pd.DataFrame, filename: str = None) -> Path:
        """
        Save the template to a CSV file.
        This CSV will have all the structure but empty values that need filling.
        """
        if filename is None:
            filename = OUTPUT_FILES['brsr_metrics']
            
        output_path = self.output_dir / filename
        # Save without index column
        df.to_csv(output_path, index=False)
        return output_path
    
    def display_summary(self, df: pd.DataFrame) -> None:
        """
        Show extraction statistics.
        Shows how many metrics were successfully extracted vs not found.
        """
        total = len(df)
        extracted = len(df[df['Metric_Value'].notna()])
        not_found = total - extracted
        extraction_rate = (extracted / total * 100) if total > 0 else 0
        review_needed = len(df[df['Needs_Manual_Review'] == True]) if 'Needs_Manual_Review' in df.columns else 0
        
        print(f"\nExtraction Results:")
        print(f"  Successfully extracted: {extracted}/{total} ({extraction_rate:.1f}%)")
        print(f"  Not found: {not_found}/{total}")
        print(f"  Needs manual review: {review_needed}/{total}")


def main():
    """
    Main function that runs when you execute this script.
    Creates the template and guide for manual data entry.
    """
    print("\nAGENT 1: BRSR EXTRACTION AGENT")
    
    # Create agent instance
    agent = BRSRExtractionAgent()
    
    # Process all companies and extract data automatically
    df = agent.process_all_companies(mode='auto')
    
    if not df.empty:
        # Save the template as CSV
        output_path = agent.save_to_csv(df)
        timing_path = agent.save_timing_csv()
        
        # Show only file creation info
        print(f"\nMetrics file created: {output_path}")
        print(f"Timing file created : {timing_path}")
        print(f"Rows: {len(df)} | Columns: {len(df.columns)}\n")
    else:
        print("\nError: No data extracted.\n")


if __name__ == "__main__":
    main()
