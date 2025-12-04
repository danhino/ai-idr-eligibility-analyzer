"""
Pydantic models for ERA data structures.
"""
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class CPTCode(BaseModel):
    """CPT code with optional modifiers."""
    code: str
    modifiers: List[str] = Field(default_factory=list)
    
    def __str__(self) -> str:
        if self.modifiers:
            return f"{self.code}-{'-'.join(self.modifiers)}"
        return self.code


class CASAdjustment(BaseModel):
    """Claim Adjustment Segment."""
    group_code: str  # CO, PR, PI, OA, etc.
    reason_code: str
    amount: Decimal
    quantity: Optional[Decimal] = None


class RemarkCode(BaseModel):
    """Remark Code (RARC)."""
    code: str  # e.g., MA130, N130
    qualifier: Optional[str] = None  # e.g., HE


class ServiceLine(BaseModel):
    """Service line item from ERA."""
    line_number: int
    cpt: Optional[CPTCode] = None
    description: Optional[str] = None
    charge_amount: Optional[Decimal] = None
    paid_amount: Optional[Decimal] = None
    cas_adjustments: List[CASAdjustment] = Field(default_factory=list)
    remark_codes: List[RemarkCode] = Field(default_factory=list)
    raw_segment: Optional[str] = None


class Claim(BaseModel):
    """Claim-level information from ERA."""
    claim_id: str
    patient_id: Optional[str] = None
    patient_name: Optional[str] = None
    claim_status: str  # 1=Processed, 19=Processed as Primary, 20=Processed as Secondary, etc.
    total_charge: Decimal
    total_paid: Decimal
    patient_responsibility: Decimal
    claim_filing_indicator: Optional[str] = None
    payer_claim_control_number: Optional[str] = None
    service_lines: List[ServiceLine] = Field(default_factory=list)
    payment_date: Optional[date] = None
    check_eft_number: Optional[str] = None
    raw_segments: Dict[str, str] = Field(default_factory=dict)


class ERAFile(BaseModel):
    """Complete ERA file structure."""
    filename: str
    file_type: str  # "835" or "pdf"
    payer_name: Optional[str] = None
    payer_id: Optional[str] = None
    check_eft_number: Optional[str] = None
    payment_date: Optional[date] = None
    claims: List[Claim] = Field(default_factory=list)
    processing_errors: List[str] = Field(default_factory=list)
    processing_warnings: List[str] = Field(default_factory=list)


class EligibilityResult(BaseModel):
    """IDR eligibility result for a service line."""
    file: str
    claim_id: str
    patient_id: Optional[str]
    svc_index: int
    cpt: Optional[str]
    modifiers: List[str] = Field(default_factory=list)
    cas_group: Optional[str] = None
    cas_reason: Optional[str] = None
    cas_amount: Optional[Decimal] = None
    rarc_list: List[str] = Field(default_factory=list)
    eligible_flag: bool = False
    eligibility_basis: str = ""  # e.g., "CPT match", "CAS match", "RARC match"
    payment_date: Optional[date] = None
    check_eft: Optional[str] = None
    open_negotiation_end: Optional[date] = None
    idr_initiation_window_end: Optional[date] = None
    errors_warnings: List[str] = Field(default_factory=list)


class CodeEntry(BaseModel):
    """Database code entry."""
    code: str
    description: str
    active: bool = True


