"""
Redaction utilities for masking PHI in reports.
"""
import re
from typing import Optional


def redact_name(name: Optional[str]) -> str:
    """Redact a person's name, keeping only first initial and last initial."""
    if not name:
        return "[REDACTED]"
    
    parts = name.strip().split()
    if len(parts) >= 2:
        return f"{parts[0][0]}. {parts[-1][0]}."
    elif len(parts) == 1:
        return f"{parts[0][0]}."
    return "[REDACTED]"


def redact_id(identifier: Optional[str], keep_last: int = 4) -> str:
    """Redact an identifier, keeping only last N digits."""
    if not identifier:
        return "[REDACTED]"
    
    identifier = str(identifier).strip()
    if len(identifier) <= keep_last:
        return "*" * len(identifier)
    
    return "*" * (len(identifier) - keep_last) + identifier[-keep_last:]


def redact_text(text: str, redact_names: bool = True, redact_ids: bool = True) -> str:
    """Redact PHI from text."""
    if not text:
        return text
    
    result = text
    
    if redact_names:
        # Pattern for names (capitalized words, 2+ chars, not all caps acronyms)
        name_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b'
        result = re.sub(name_pattern, lambda m: redact_name(m.group(1)), result)
    
    if redact_ids:
        # Pattern for IDs (long alphanumeric sequences)
        id_pattern = r'\b([A-Z0-9]{8,})\b'
        result = re.sub(id_pattern, lambda m: redact_id(m.group(1)), result)
    
    return result


