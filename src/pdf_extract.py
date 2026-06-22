"""
PDF text extraction with OCR fallback and glossary stripping.
"""
import re
from pathlib import Path
from typing import Optional, Tuple
from PyPDF2 import PdfReader
import spacy

from src.ocr import extract_text_with_ocr, needs_ocr
from src.utils.logging import logger


# Matches the glossary header found in Claim.MD ERA PDFs.
# Variations observed: "GLOSSARY : GROUP, REASON, MOA, REMARK AND REASON CODES"
_GLOSSARY_PATTERN = re.compile(
    r'^GLOSSARY\s*:\s*GROUP,?\s*REASON,?\s*MOA,?\s*REMARK\s+AND\s+REASON\s+CODES',
    re.IGNORECASE | re.MULTILINE,
)

# Load spaCy model (will be initialized on first use)
_nlp = None


def get_nlp():
    """Lazy load spaCy model."""
    global _nlp
    if _nlp is None:
        try:
            _nlp = spacy.load("en_core_web_sm")
        except OSError:
            logger.warning("spaCy model 'en_core_web_sm' not found. Run: python -m spacy download en_core_web_sm")
            _nlp = None
    return _nlp


def strip_glossary(text: str) -> Tuple[str, Optional[str]]:
    """
    Remove the glossary/definitions section from ERA PDF text.

    The glossary always appears after the TOTALS summary and contains
    code definitions (e.g. "CO-45  Charge exceeds fee schedule...").
    These codes must not be parsed as claim data.

    Args:
        text: Full extracted PDF text

    Returns:
        Tuple of (body text without glossary, glossary text or None)
    """
    match = _GLOSSARY_PATTERN.search(text)
    if not match:
        return text, None

    body = text[:match.start()].rstrip()
    glossary = text[match.start():]
    logger.info(f"Glossary section detected and excluded ({len(glossary)} chars)")
    return body, glossary


def is_in_glossary(text: str, code: str, code_position: int) -> bool:
    """
    Check whether a code occurrence falls within the glossary section.

    Args:
        text: Full (unstripped) PDF text
        code: The code string (e.g. "CO-45", "N877")
        code_position: Character offset of the code in `text`

    Returns:
        True if the code is inside the glossary boundary
    """
    match = _GLOSSARY_PATTERN.search(text)
    if not match:
        return False
    return code_position >= match.start()


def extract_text_from_pdf(pdf_path: Path, use_ocr_fallback: bool = True) -> str:
    """
    Extract text from PDF, using OCR if needed.
    Glossary sections are automatically stripped so downstream parsers
    never see code definitions as claim data.

    Args:
        pdf_path: Path to PDF file
        use_ocr_fallback: Whether to use OCR if direct extraction fails

    Returns:
        Extracted text (glossary removed)
    """
    try:
        # Try direct text extraction first
        with open(pdf_path, 'rb') as pdf_file:
            reader = PdfReader(pdf_file)
            text_parts = []

            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)

            extracted_text = "\n".join(text_parts)

        # Check if we got sufficient text
        if len(extracted_text.strip()) < 100 and use_ocr_fallback:
            logger.info(f"Insufficient text extracted from {pdf_path}, attempting OCR...")
            if needs_ocr(pdf_path):
                extracted_text = extract_text_with_ocr(pdf_path)

        body, _glossary = strip_glossary(extracted_text)
        return body

    except Exception as e:
        logger.error(f"PDF extraction failed for {pdf_path}: {e}")
        if use_ocr_fallback:
            try:
                logger.info(f"Attempting OCR fallback for {pdf_path}...")
                ocr_text = extract_text_with_ocr(pdf_path)
                body, _glossary = strip_glossary(ocr_text)
                return body
            except Exception as ocr_error:
                logger.error(f"OCR fallback also failed for {pdf_path}: {ocr_error}")
                raise
        raise


def segment_text_with_spacy(text: str) -> list[str]:
    """
    Use spaCy to help segment text into logical sections.
    
    Args:
        text: Raw extracted text
    
    Returns:
        List of text segments
    """
    nlp = get_nlp()
    if nlp is None:
        # Fallback to simple line-based segmentation
        return [line.strip() for line in text.split("\n") if line.strip()]
    
    doc = nlp(text)
    segments = []
    current_segment = []
    
    for sent in doc.sents:
        # Detect headings (short sentences, often all caps or title case)
        is_heading = len(sent.text.strip()) < 50 and (
            sent.text.isupper() or sent.text.istitle()
        )
        
        if is_heading and current_segment:
            segments.append(" ".join(current_segment))
            current_segment = [sent.text]
        else:
            current_segment.append(sent.text)
    
    if current_segment:
        segments.append(" ".join(current_segment))
    
    return segments if segments else [text]

