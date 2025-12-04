"""
OCR utilities for extracting text from scanned PDFs.
"""
from pathlib import Path
from typing import Optional
from pdf2image import convert_from_path
import pytesseract
from PIL import Image

from src.config import OCR_LANGUAGE
from src.utils.logging import logger


def extract_text_with_ocr(pdf_path: Path, page_num: Optional[int] = None) -> str:
    """
    Extract text from PDF using OCR.
    
    Args:
        pdf_path: Path to PDF file
        page_num: Specific page to extract (None for all pages)
    
    Returns:
        Extracted text
    """
    try:
        if page_num is not None:
            pages = convert_from_path(str(pdf_path), first_page=page_num, last_page=page_num)
        else:
            pages = convert_from_path(str(pdf_path))
        
        text_parts = []
        for page in pages:
            text = pytesseract.image_to_string(page, lang=OCR_LANGUAGE)
            text_parts.append(text)
        
        return "\n".join(text_parts)
    
    except Exception as e:
        logger.error(f"OCR extraction failed for {pdf_path}: {e}")
        raise


def needs_ocr(pdf_path: Path, min_text_length: int = 100) -> bool:
    """
    Check if PDF needs OCR (has insufficient extractable text).
    
    Args:
        pdf_path: Path to PDF file
        min_text_length: Minimum text length to consider as having extractable text
    
    Returns:
        True if OCR is needed
    """
    try:
        from PyPDF2 import PdfReader
        with open(pdf_path, 'rb') as pdf_file:
            reader = PdfReader(pdf_file)
            total_text = ""
            for page in reader.pages[:3]:  # Check first 3 pages
                total_text += page.extract_text() or ""
                if len(total_text) >= min_text_length:
                    return False
            return len(total_text) < min_text_length
    except Exception as e:
        logger.warning(f"Could not check if OCR needed for {pdf_path}: {e}")
        return True  # Assume OCR needed if check fails

