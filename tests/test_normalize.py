"""
Tests for normalization utilities.
"""
import pytest
from decimal import Decimal
from src.normalize import normalize_cpt, parse_amount, extract_cpt_from_text


def test_normalize_cpt():
    """Test CPT code normalization."""
    # Test with modifier
    result = normalize_cpt("99283-25")
    assert result["code"] == "99283"
    assert "25" in result["modifiers"]
    
    # Test with space
    result = normalize_cpt("99283 25")
    assert result["code"] == "99283"
    assert "25" in result["modifiers"]
    
    # Test with colon format
    result = normalize_cpt("HC:99283:25")
    assert result["code"] == "99283"
    assert "25" in result["modifiers"]
    
    # Test simple code
    result = normalize_cpt("99283")
    assert result["code"] == "99283"
    assert len(result["modifiers"]) == 0


def test_parse_amount():
    """Test amount parsing."""
    assert parse_amount("100.00") == Decimal("100.00")
    assert parse_amount("$100.00") == Decimal("100.00")
    assert parse_amount("1,000.50") == Decimal("1000.50")
    assert parse_amount("100") == Decimal("100")
    assert parse_amount("") == Decimal("0")
    assert parse_amount(None) == Decimal("0")


def test_extract_cpt_from_text():
    """Test CPT extraction from text."""
    text = "Procedure code 99283 with modifier 25 was billed."
    results = extract_cpt_from_text(text)
    assert len(results) >= 1
    assert any(r["code"] == "99283" for r in results)


