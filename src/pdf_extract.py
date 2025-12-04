"""
PDF text extraction with OCR fallback.
"""
from pathlib import Path
from typing import Optional
from PyPDF2 import PdfReader
import spacy

from src.ocr import extract_text_with_ocr, needs_ocr
from src.utils.logging import logger


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


def extract_text_from_pdf(pdf_path: Path, use_ocr_fallback: bool = True) -> str:
    """
    Extract text from PDF, using OCR if needed.
    
    Args:
        pdf_path: Path to PDF file
        use_ocr_fallback: Whether to use OCR if direct extraction fails
    
    Returns:
        Extracted text
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
        
        return extracted_text
    
    except Exception as e:
        logger.error(f"PDF extraction failed for {pdf_path}: {e}")
        if use_ocr_fallback:
            try:
                logger.info(f"Attempting OCR fallback for {pdf_path}...")
                return extract_text_with_ocr(pdf_path)
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

