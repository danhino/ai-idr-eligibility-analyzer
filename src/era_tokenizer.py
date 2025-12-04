"""
ERA tokenizer for parsing ANSI 835 segment and element delimiters.
"""
import re
from typing import List, Tuple, Optional
from dataclasses import dataclass

from src.config import (
    DEFAULT_SEGMENT_DELIMITER,
    DEFAULT_ELEMENT_DELIMITER,
    DEFAULT_SUBELEMENT_DELIMITER
)
from src.utils.logging import logger


@dataclass
class Delimiters:
    """ERA delimiter configuration."""
    segment: str = DEFAULT_SEGMENT_DELIMITER
    element: str = DEFAULT_ELEMENT_DELIMITER
    subelement: str = DEFAULT_SUBELEMENT_DELIMITER


class ERATokenizer:
    """Tokenizer for ANSI 835 EDI files."""
    
    def __init__(self, delimiters: Optional[Delimiters] = None):
        self.delimiters = delimiters or Delimiters()
    
    @classmethod
    def detect_delimiters(cls, text: str) -> Delimiters:
        """
        Detect delimiters from ISA or GS segment if present.
        
        Args:
            text: Raw EDI text
        
        Returns:
            Delimiters object
        """
        # Look for ISA segment (first line typically)
        isa_match = re.search(r'^ISA\*([^*]{1})\*([^*]{1})', text[:200], re.MULTILINE)
        if isa_match:
            element_delim = isa_match.group(1)
            subelement_delim = isa_match.group(2)
            # Segment delimiter is typically ~ or newline
            segment_delim = "~" if "~" in text[:200] else "\n"
            return Delimiters(
                segment=segment_delim,
                element=element_delim,
                subelement=subelement_delim
            )
        
        # Look for GS segment
        gs_match = re.search(r'^GS\*([^*]{1})', text[:200], re.MULTILINE)
        if gs_match:
            element_delim = gs_match.group(1)
            segment_delim = "~" if "~" in text[:200] else "\n"
            return Delimiters(
                segment=segment_delim,
                element=element_delim,
                subelement=":"
            )
        
        # Default delimiters
        return Delimiters()
    
    def tokenize_segments(self, text: str) -> List[str]:
        """
        Split text into segments.
        
        Args:
            text: Raw EDI text
        
        Returns:
            List of segment strings
        """
        # Normalize line endings
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        
        # Split by segment delimiter
        if self.delimiters.segment == "\n":
            segments = text.split("\n")
        else:
            segments = text.split(self.delimiters.segment)
        
        # Filter empty segments
        return [s.strip() for s in segments if s.strip()]
    
    def parse_segment(self, segment: str) -> Tuple[str, List[str]]:
        """
        Parse a segment into segment ID and elements.
        
        Args:
            segment: Segment string (e.g., "CLP*12345*1*100.00*50.00")
        
        Returns:
            Tuple of (segment_id, elements)
        """
        if not segment:
            return "", []
        
        # Split by element delimiter
        parts = segment.split(self.delimiters.element)
        
        if not parts:
            return "", []
        
        segment_id = parts[0].strip()
        elements = [p.strip() for p in parts[1:]] if len(parts) > 1 else []
        
        return segment_id, elements
    
    def parse_element(self, element: str) -> List[str]:
        """
        Parse an element into subelements.
        
        Args:
            element: Element string (e.g., "HC:99283:25")
        
        Returns:
            List of subelements
        """
        if not element:
            return []
        
        return [s.strip() for s in element.split(self.delimiters.subelement) if s.strip()]
    
    def tokenize_pdf_text(self, text: str) -> List[dict]:
        """
        Tokenize PDF-extracted text into pseudo-segments using heuristics.
        
        Args:
            text: Extracted PDF text
        
        Returns:
            List of dicts with 'segment_id' and 'elements'
        """
        segments = []
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        
        current_segment = None
        current_elements = []
        
        # Patterns for common segment indicators
        segment_patterns = {
            "CLP": r"(?i)(?:claim|clp|patient|claim\s+id|icn|acnt)",
            "SVC": r"(?i)(?:service|svc|cpt|procedure|proc|rend\s+prov)",
            "CAS": r"(?i)(?:adjustment|cas|denial|reduction|grp/rc)",
            "LQ": r"(?i)(?:remark|note|rarc|lq|rem:)",
            "DTM": r"(?i)(?:date|payment\s+date|dtm|serv\s+date)",
        }
        
        for line in lines:
            # Try to identify segment type
            segment_id = None
            for seg_id, pattern in segment_patterns.items():
                if re.search(pattern, line):
                    segment_id = seg_id
                    break
            
            if segment_id:
                # Save previous segment if exists
                if current_segment:
                    segments.append({
                        "segment_id": current_segment,
                        "elements": current_elements
                    })
                current_segment = segment_id
                current_elements = [line]
            elif current_segment:
                current_elements.append(line)
            else:
                # Unknown segment, create generic one
                segments.append({
                    "segment_id": "UNK",
                    "elements": [line]
                })
        
        # Add last segment
        if current_segment:
            segments.append({
                "segment_id": current_segment,
                "elements": current_elements
            })
        
        return segments


def tokenize_pdf_text(text: str) -> List[dict]:
    """
    Tokenize PDF-extracted text into pseudo-segments using heuristics.
    
    Args:
        text: Extracted PDF text
    
    Returns:
        List of dicts with 'segment_id' and 'elements'
    """
    segments = []
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    
    current_segment = None
    current_elements = []
    
    # Patterns for common segment indicators
    segment_patterns = {
        "CLP": r"(?i)(?:claim|clp|patient|claim\s+id|icn|acnt)",
        "SVC": r"(?i)(?:service|svc|cpt|procedure|proc|rend\s+prov)",
        "CAS": r"(?i)(?:adjustment|cas|denial|reduction|grp/rc)",
        "LQ": r"(?i)(?:remark|note|rarc|lq|rem:)",
        "DTM": r"(?i)(?:date|payment\s+date|dtm|serv\s+date)",
    }
    
    for line in lines:
        # Try to identify segment type
        segment_id = None
        for seg_id, pattern in segment_patterns.items():
            if re.search(pattern, line):
                segment_id = seg_id
                break
        
        if segment_id:
            # Save previous segment if exists
            if current_segment:
                segments.append({
                    "segment_id": current_segment,
                    "elements": current_elements
                })
            current_segment = segment_id
            current_elements = [line]
        elif current_segment:
            current_elements.append(line)
        else:
            # Unknown segment, create generic one
            segments.append({
                "segment_id": "UNK",
                "elements": [line]
            })
    
    # Add last segment
    if current_segment:
        segments.append({
            "segment_id": current_segment,
            "elements": current_elements
        })
    
    return segments

