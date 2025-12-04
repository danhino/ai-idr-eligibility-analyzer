"""
Tests for eligibility rules.
"""
import pytest
from datetime import date
from decimal import Decimal
from src.models import Claim, ServiceLine, CPTCode, CASAdjustment, RemarkCode
from src.rules import EligibilityEvaluator
from src.db import init_db, get_session, CPTCode as DBCPTCode, CASCode, RemarkCode as DBRemarkCode


@pytest.fixture
def db_session():
    """Create test database session."""
    init_db()
    session = get_session()
    yield session
    session.close()


@pytest.fixture
def seed_test_data(db_session):
    """Seed test data."""
    # Add test CPT code
    cpt = DBCPTCode(code="99283", description="Test CPT", active=True)
    db_session.add(cpt)
    
    # Add test CAS code
    cas = CASCode(group_code="CO", reason_code="45", description="Test CAS", active=True)
    db_session.add(cas)
    
    # Add test RARC
    rarc = DBRemarkCode(rarc="MA130", description="Test RARC", active=True)
    db_session.add(rarc)
    
    db_session.commit()


def test_check_cpt(db_session, seed_test_data):
    """Test CPT code checking."""
    evaluator = EligibilityEvaluator(session=db_session)
    assert evaluator._check_cpt("99283") is True
    assert evaluator._check_cpt("99999") is False


def test_check_cas(db_session, seed_test_data):
    """Test CAS code checking."""
    evaluator = EligibilityEvaluator(session=db_session)
    assert evaluator._check_cas("CO", "45") is True
    assert evaluator._check_cas("CO", "99") is False


def test_check_rarc(db_session, seed_test_data):
    """Test RARC code checking."""
    evaluator = EligibilityEvaluator(session=db_session)
    assert evaluator._check_rarc("MA130") is True
    assert evaluator._check_rarc("XX999") is False


def test_evaluate_service_line(db_session, seed_test_data):
    """Test service line evaluation."""
    evaluator = EligibilityEvaluator(session=db_session)
    
    # Create test service line with eligible CPT
    service_line = ServiceLine(
        line_number=1,
        cpt=CPTCode(code="99283", modifiers=[])
    )
    
    claim = Claim(
        claim_id="TEST001",
        claim_status="1",
        total_charge=Decimal("100.00"),
        total_paid=Decimal("80.00"),
        patient_responsibility=Decimal("20.00"),
        payment_date=date(2024, 1, 1)
    )
    
    result = evaluator.evaluate_service_line(service_line, claim, "test.txt", 1)
    
    assert result.eligible_flag is True
    assert "CPT 99283" in result.eligibility_basis
    assert result.open_negotiation_end is not None
    assert result.idr_initiation_window_end is not None


