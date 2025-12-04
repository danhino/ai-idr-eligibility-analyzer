"""
Normalization utilities for CPT codes, modifiers, amounts, and dates.
"""
import re
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional

from src.utils.time import parse_date
from src.utils.logging import logger


def normalize_cpt(code: str, modifiers: Optional[List[str]] = None) -> Dict[str, any]:
    """
    Normalize CPT code and modifiers.
    
    Handles formats like:
    - 99283-25
    - 99283 25
    - HC:99283:25
    - 99283
    
    Args:
        code: CPT code string (may include modifiers)
        modifiers: Optional list of modifiers
    
    Returns:
        Dict with 'code' and 'modifiers' keys
    """
    if not code:
        return {"code": "", "modifiers": []}
    
    code = str(code).strip()
    mods = modifiers or []
    
    # Remove common prefixes
    code = re.sub(r'^(HC|HCPCS)[:\s]*', '', code, flags=re.IGNORECASE)
    
    # Try to split code and modifiers if combined
    # Pattern: 5 digits followed by optional separator and modifier(s)
    combined_pattern = r'^(\d{5})(?:[-\s:]+([A-Z0-9]{2}(?:[-\s:]+[A-Z0-9]{2})*))?$'
    match = re.match(combined_pattern, code)
    
    if match:
        base_code = match.group(1)
        if match.group(2):
            # Extract modifiers from combined string
            mods_str = match.group(2)
            mods.extend(re.findall(r'[A-Z0-9]{2}', mods_str))
    else:
        # Try to extract just the 5-digit code
        code_match = re.search(r'\b(\d{5})\b', code)
        if code_match:
            base_code = code_match.group(1)
        else:
            base_code = code
    
    # Normalize modifiers: uppercase, remove duplicates, keep order
    normalized_mods = []
    seen = set()
    for mod in mods:
        mod_upper = str(mod).strip().upper()
        if mod_upper and mod_upper not in seen and len(mod_upper) == 2:
            normalized_mods.append(mod_upper)
            seen.add(mod_upper)
    
    return {
        "code": base_code,
        "modifiers": normalized_mods
    }


def parse_amount(amount_str: Optional[str]) -> Decimal:
    """
    Parse amount string to Decimal.
    
    Handles formats like:
    - "100.00"
    - "$100.00"
    - "1,000.50"
    - "100"
    
    Args:
        amount_str: Amount string
    
    Returns:
        Decimal amount (0 if parsing fails)
    """
    if not amount_str:
        return Decimal("0")
    
    # Remove currency symbols and whitespace
    cleaned = str(amount_str).strip().replace("$", "").replace(",", "").strip()
    
    if not cleaned:
        return Decimal("0")
    
    try:
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        logger.warning(f"Could not parse amount: {amount_str}")
        return Decimal("0")


def normalize_date(date_str: Optional[str]) -> Optional[str]:
    """
    Normalize date string to YYYYMMDD format.
    
    Args:
        date_str: Date string in various formats
    
    Returns:
        Normalized date string or None
    """
    if not date_str:
        return None
    
    parsed = parse_date(date_str)
    if parsed:
        return parsed.strftime("%Y%m%d")
    
    return None


def extract_cpt_from_text(text: str) -> List[Dict[str, str]]:
    """
    Extract CPT codes from free text.
    
    Args:
        text: Text to search
    
    Returns:
        List of dicts with 'code' and 'modifiers'
    """
    results = []
    
    # Pattern for CPT with optional modifiers
    pattern = r'\b(\d{5})(?:[-\s:]+([A-Z0-9]{2}(?:[-\s:]+[A-Z0-9]{2})*))?\b'
    
    for match in re.finditer(pattern, text):
        code = match.group(1)
        mods_str = match.group(2)
        modifiers = re.findall(r'[A-Z0-9]{2}', mods_str) if mods_str else []
        
        normalized = normalize_cpt(code, modifiers)
        results.append(normalized)
    
    return results


def extract_hcpcs_from_text(text: str) -> List[str]:
    """
    Extract HCPCS codes from text.
    
    Args:
        text: Text to search
    
    Returns:
        List of HCPCS codes
    """
    # HCPCS pattern: Letter followed by 4 digits
    pattern = r'\b([A-Z]\d{4})\b'
    return [match.group(1) for match in re.finditer(pattern, text)]

