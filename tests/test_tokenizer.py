"""
Tests for ERA tokenizer.
"""
import pytest
from src.era_tokenizer import ERATokenizer, Delimiters


def test_detect_delimiters():
    """Test delimiter detection from ISA segment."""
    text = "ISA*00*          *00*          *ZZ*PAYERID*ZZ*PROVIDERID*240101*1200*^*00501*000000001*0*P*:~"
    delimiters = ERATokenizer.detect_delimiters(text)
    assert delimiters.element == "*"
    assert delimiters.subelement == "^"


def test_tokenize_segments():
    """Test segment tokenization."""
    tokenizer = ERATokenizer()
    text = "CLP*12345*1*100.00*50.00~\nSVC*HC:99283*150.00*100.00~"
    segments = tokenizer.tokenize_segments(text)
    assert len(segments) == 2
    assert segments[0].startswith("CLP")
    assert segments[1].startswith("SVC")


def test_parse_segment():
    """Test segment parsing."""
    tokenizer = ERATokenizer()
    segment = "CLP*12345*1*100.00*50.00"
    seg_id, elements = tokenizer.parse_segment(segment)
    assert seg_id == "CLP"
    assert len(elements) == 4
    assert elements[0] == "12345"


def test_parse_element():
    """Test element parsing with subelements."""
    tokenizer = ERATokenizer()
    element = "HC:99283:25"
    subelements = tokenizer.parse_element(element)
    assert len(subelements) == 3
    assert subelements[0] == "HC"
    assert subelements[1] == "99283"
    assert subelements[2] == "25"


