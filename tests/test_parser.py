"""
Tests for ERA parser.
"""
import pytest
from decimal import Decimal
from src.era_parser import ERAParser
from src.models import Claim, ServiceLine


def test_parse_clp():
    """Test CLP segment parsing."""
    parser = ERAParser()
    text = "CLP*CLAIM001*1*150.00*100.00*50.00*11*123456789~"
    segments = parser.tokenizer.tokenize_segments(text)
    parser._parse_segment(segments[0])
    assert parser.current_claim is not None
    assert parser.current_claim.claim_id == "CLAIM001"
    assert parser.current_claim.total_charge == Decimal("150.00")


def test_parse_svc():
    """Test SVC segment parsing."""
    parser = ERAParser()
    # Set up claim first
    parser._parse_clp(["CLAIM001", "1", "150.00", "100.00", "50.00"])
    parser._parse_lx(["1"])
    parser._parse_svc(["HC:99283:25", "150.00", "100.00"])
    
    assert parser.current_service_line is not None
    assert parser.current_service_line.cpt is not None
    assert parser.current_service_line.cpt.code == "99283"
    assert "25" in parser.current_service_line.cpt.modifiers


def test_parse_cas():
    """Test CAS segment parsing."""
    parser = ERAParser()
    parser._parse_clp(["CLAIM001", "1", "150.00", "100.00", "50.00"])
    parser._parse_lx(["1"])
    parser._parse_svc(["HC:99283", "150.00", "100.00"])
    parser._parse_cas(["CO", "45", "50.00"])
    
    assert len(parser.current_service_line.cas_adjustments) == 1
    cas = parser.current_service_line.cas_adjustments[0]
    assert cas.group_code == "CO"
    assert cas.reason_code == "45"
    assert cas.amount == Decimal("50.00")


def test_parse_lq():
    """Test LQ segment parsing."""
    parser = ERAParser()
    parser._parse_clp(["CLAIM001", "1", "150.00", "100.00", "50.00"])
    parser._parse_lx(["1"])
    parser._parse_svc(["HC:99283", "150.00", "100.00"])
    parser._parse_lq(["HE", "MA130"])
    
    assert len(parser.current_service_line.remark_codes) == 1
    remark = parser.current_service_line.remark_codes[0]
    assert remark.code == "MA130"
    assert remark.qualifier == "HE"


