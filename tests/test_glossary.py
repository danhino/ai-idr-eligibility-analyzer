"""
Tests for glossary detection and stripping in PDF ERA files.
"""
import pytest
from src.pdf_extract import strip_glossary, is_in_glossary


SAMPLE_TEXT = """NAME CRAFT, CAMILLE R HIC XXP967553767 ACNT FFATP59269239-3 ICN 02025301502J8400X00 ASG Y MOA
1265627186 1023 102325 23 1 99284 8443.37 0.00 0.00 0.00 OA-209 8443.37 0.00
 REM: N877
PT RESP 0.00 CLAIM TOTALS 8443.37 0.00 0.00 0.00 8443.37 0.00
TOTALS: # OF BILLED ALLOWED DEDUCT COINS TOTAL PROV PD PROV CHECK
 CLAIMS AMT AMT AMT AMT RC-AMT AMT ADJ AMT AMT
 4 33773.48 17123.31 0.00 34.18 25093.54 8645.76 0.00 8645.76
GLOSSARY : GROUP, REASON, MOA, REMARK AND REASON CODES
CO-45 Charge exceeds fee schedule / maximum allowable or contracted / legislated fee arrangement.
N130 Consult plan benefit documents/guidelines for information about restrictions for this service.
N877 Alert: This initial payment is provided in accordance with the No Surprises Act.
OA-209 Per regulatory or other agreement.
PR-2 Coinsurance Amount
PR-96 Non-covered charge(s)."""


def test_strip_glossary_removes_glossary():
    body, glossary = strip_glossary(SAMPLE_TEXT)
    assert "GLOSSARY" not in body
    assert "CO-45" not in body
    assert "N130" not in body
    assert "Coinsurance Amount" not in body


def test_strip_glossary_preserves_claim_data():
    body, glossary = strip_glossary(SAMPLE_TEXT)
    assert "CRAFT, CAMILLE" in body
    assert "99284" in body
    assert "OA-209" in body
    assert "REM: N877" in body
    assert "TOTALS:" in body


def test_strip_glossary_returns_glossary_text():
    body, glossary = strip_glossary(SAMPLE_TEXT)
    assert glossary is not None
    assert "GLOSSARY" in glossary
    assert "CO-45" in glossary
    assert "Coinsurance Amount" in glossary


def test_strip_glossary_no_glossary():
    text = "NAME SMITH, JOHN\n99284 8443.37\nREM: N877"
    body, glossary = strip_glossary(text)
    assert body == text
    assert glossary is None


def test_is_in_glossary_body_code():
    pos = SAMPLE_TEXT.index("OA-209 8443.37")
    assert is_in_glossary(SAMPLE_TEXT, "OA-209", pos) is False


def test_is_in_glossary_glossary_code():
    glossary_start = SAMPLE_TEXT.index("GLOSSARY")
    pos = SAMPLE_TEXT.index("CO-45 Charge exceeds")
    assert pos > glossary_start
    assert is_in_glossary(SAMPLE_TEXT, "CO-45", pos) is True


def test_is_in_glossary_no_glossary():
    text = "NAME SMITH, JOHN\nCO-45 100.00"
    assert is_in_glossary(text, "CO-45", text.index("CO-45")) is False


def test_multipage_glossary():
    """Simulates era 3.pdf where glossary spans pages 4-5."""
    text = """TOTALS: # OF BILLED
 CLAIMS AMT
 11 63328.63
GLOSSARY : GROUP, REASON, MOA, REMARK AND REASON CODES
CO-45 Charge exceeds fee schedule.
M127 Missing patient medical record.
N130 Consult plan benefit documents.
N875 Alert: This final payment equals the amount.
N877 Alert: This initial payment is provided.
OA-209 Per regulatory or other agreement.
PI-252 An attachment is required.
PR-1 Deductible Amount
PR-2 Coinsurance Amount
PR-45 Charge exceeds fee schedule.
PR-96 Non-covered charge(s)."""
    body, glossary = strip_glossary(text)
    assert "CO-45" not in body
    assert "PR-96" not in body
    assert "M127" not in body
    assert "TOTALS:" in body
    assert glossary is not None
    assert glossary.count("CO-45") == 1
