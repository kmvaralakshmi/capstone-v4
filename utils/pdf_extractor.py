"""Optimized Phase 3 PDF extraction utilities."""
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import re

try:
    import pypdfium2 as pdfium
except ImportError:
    pdfium = None

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

try:
    import pdfplumber
except ImportError:
    pdfplumber = None


def _pages(page_numbers, total_pages):
    if page_numbers is None:
        return range(1, total_pages + 1)
    seen, result = set(), []
    for p in page_numbers:
        if 1 <= p <= total_pages and p not in seen:
            result.append(p)
            seen.add(p)
    return result


def extract_text_from_pdf(
    pdf_path: Path,
    page_numbers: Optional[List[int]] = None,
) -> Dict[int, str]:
    """Extract page text with pypdfium2 first, PyPDF2 fallback."""
    pdf_path = Path(pdf_path)
    result: Dict[int, str] = {}

    if pdfium is not None:
        pdf = None
        try:
            pdf = pdfium.PdfDocument(str(pdf_path))
            for page_number in _pages(page_numbers, len(pdf)):
                page = text_page = None
                try:
                    page = pdf[page_number - 1]
                    text_page = page.get_textpage()
                    result[page_number] = text_page.get_text_range() or ""
                except Exception as exc:
                    print(
                        f"Text extraction failed on page {page_number}: "
                        f"{type(exc).__name__}: {exc}"
                    )
                    result[page_number] = ""
                finally:
                    if text_page is not None:
                        try: text_page.close()
                        except Exception: pass
                    if page is not None:
                        try: page.close()
                        except Exception: pass
            return result
        except Exception as exc:
            print(
                "pypdfium2 failed; falling back to PyPDF2: "
                f"{type(exc).__name__}: {exc}"
            )
        finally:
            if pdf is not None:
                try: pdf.close()
                except Exception: pass

    if PyPDF2 is None:
        raise RuntimeError("Neither pypdfium2 nor PyPDF2 is available.")

    with open(pdf_path, "rb") as file:
        reader = PyPDF2.PdfReader(file)
        for page_number in _pages(page_numbers, len(reader.pages)):
            try:
                result[page_number] = (
                    reader.pages[page_number - 1].extract_text() or ""
                )
            except Exception as exc:
                print(
                    f"Text extraction failed on page {page_number}: "
                    f"{type(exc).__name__}: {exc}"
                )
                result[page_number] = ""
    return result


def extract_tables_from_pdf(
    pdf_path: Path,
    page_numbers: Optional[List[int]] = None,
) -> Dict[int, List]:
    """Extract tables only from requested pages using pdfplumber."""
    if pdfplumber is None:
        raise RuntimeError("pdfplumber is not installed.")

    result: Dict[int, List] = {}
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page_number in _pages(page_numbers, len(pdf.pages)):
            page = pdf.pages[page_number - 1]
            try:
                tables = page.extract_tables()
            except Exception as exc:
                print(
                    f"Table extraction failed on page {page_number}: "
                    f"{type(exc).__name__}: {exc}"
                )
                tables = []
            if tables:
                result[page_number] = tables
    return result


def get_pdf_metadata(pdf_path: Path) -> Dict:
    """Return basic PDF metadata."""
    pdf_path = Path(pdf_path)
    if pdfium is not None:
        pdf = None
        try:
            pdf = pdfium.PdfDocument(str(pdf_path))
            return {"pages": len(pdf)}
        except Exception:
            pass
        finally:
            if pdf is not None:
                try: pdf.close()
                except Exception: pass

    if PyPDF2 is not None:
        with open(pdf_path, "rb") as file:
            return {"pages": len(PyPDF2.PdfReader(file).pages)}
    raise RuntimeError("No supported PDF library is available.")


def search_pdf_for_terms(
    pdf_path: Path,
    search_terms: List[str],
    page_numbers: Optional[List[int]] = None,
) -> Dict[str, List[Tuple[int, str]]]:
    """Search PDF text and return page/context matches."""
    text_by_page = extract_text_from_pdf(pdf_path, page_numbers)
    results = {term: [] for term in search_terms}

    for page_number, text in text_by_page.items():
        lower_text = text.lower()
        for term in search_terms:
            if not term:
                continue
            position = lower_text.find(term.lower())
            if position == -1:
                continue
            start = max(0, position - 250)
            end = min(len(text), position + len(term) + 350)
            context = re.sub(r"\s+", " ", text[start:end]).strip()
            results[term].append((page_number, context))
    return results


def pdf_contains_text(
    pdf_path: Path,
    search_terms: List[str],
    page_numbers: Optional[List[int]] = None,
) -> bool:
    """Return True if any requested term occurs in selected pages."""
    results = search_pdf_for_terms(pdf_path, search_terms, page_numbers)
    return any(matches for matches in results.values())


def search_text_in_pdf(
    pdf_path: Path,
    search_terms: List[str],
    page_numbers: Optional[List[int]] = None,
) -> Dict[str, List[Tuple[int, str]]]:
    """Backwards-compatible alias for the PDF search helper."""
    return search_pdf_for_terms(pdf_path, search_terms, page_numbers)


def extract_numbers_from_text(text: str) -> List[float]:
    """Extract numeric values from text, including comma-formatted values."""
    if not text:
        return []

    values: List[float] = []
    for match in re.findall(r"[-+]?\d[\d,]*\.?\d*(?:e[-+]?\d+)?", str(text), flags=re.IGNORECASE):
        cleaned = match.replace(",", "")
        try:
            values.append(float(cleaned))
        except ValueError:
            continue
    return values


def extract_percentage_from_text(text: str) -> Optional[float]:
    """Extract the first percentage value from text, such as 12.5% or 12,5%."""
    if not text:
        return None

    match = re.search(r"([-+]?\d[\d,]*\.?\d*)\s*%", str(text), flags=re.IGNORECASE)
    if not match:
        return None

    try:
        return float(match.group(1).replace(",", ""))
    except ValueError:
        return None
