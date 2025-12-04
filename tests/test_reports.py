"""
Tests for report generation.
"""
import pytest
from datetime import date
from pathlib import Path
from decimal import Decimal
from src.models import EligibilityResult, ERAFile
from src.reporter.csv_report import generate_csv_report
from src.reporter.json_report import generate_json_report
from src.reporter.audit_report import generate_audit_report


@pytest.fixture
def sample_results():
    """Create sample eligibility results."""
    return [
        EligibilityResult(
            file="test1.txt",
            claim_id="CLAIM001",
            patient_id="PAT001",
            svc_index=1,
            cpt="99283",
            modifiers=["25"],
            cas_group="CO",
            cas_reason="45",
            cas_amount=Decimal("50.00"),
            rarc_list=["MA130"],
            eligible_flag=True,
            eligibility_basis="CPT 99283; CAS CO-45",
            payment_date=date(2024, 1, 1),
            check_eft="CHK001",
            open_negotiation_end=date(2024, 2, 10),
            idr_initiation_window_end=date(2024, 2, 14)
        )
    ]


@pytest.fixture
def sample_era_files():
    """Create sample ERA files."""
    return [
        ERAFile(
            filename="test1.txt",
            file_type="835",
            payment_date=date(2024, 1, 1),
            claims=[]
        )
    ]


def test_csv_report(sample_results, tmp_path):
    """Test CSV report generation."""
    output_path = tmp_path / "test.csv"
    df = generate_csv_report(sample_results, output_path)
    
    assert len(df) == 1
    assert df.iloc[0]["cpt"] == "99283"
    assert output_path.exists()


def test_json_report(sample_results, tmp_path):
    """Test JSON report generation."""
    output_path = tmp_path / "test.json"
    report = generate_json_report(sample_results, output_path)
    
    assert "files" in report
    assert "summary" in report
    assert report["summary"]["total_files"] == 1
    assert output_path.exists()


def test_audit_report(sample_results, sample_era_files):
    """Test audit report generation."""
    report = generate_audit_report(sample_results, sample_era_files)
    
    assert "ERA IDR Eligibility Audit Report" in report
    assert "CLAIM001" in report
    assert "99283" in report


