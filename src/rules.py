"""
Eligibility rules evaluation and IDR timeline computation.
"""
from datetime import date
from decimal import Decimal
from typing import List, Optional, Dict
from sqlalchemy.orm import Session

from src.models import ServiceLine, Claim, EligibilityResult, CPTCode, CASAdjustment, RemarkCode
from src.db import get_session, CPTCode as DBCPTCode, CASCode, RemarkCode as DBRemarkCode
from src.utils.time import calculate_open_negotiation_end, calculate_idr_initiation_window_end
from src.utils.logging import logger


class EligibilityEvaluator:
    """Evaluates IDR eligibility for claims and service lines."""
    
    def __init__(self, session: Optional[Session] = None):
        self.session = session or get_session()
    
    def evaluate_claim(self, claim: Claim, filename: str) -> List[EligibilityResult]:
        """
        Evaluate eligibility for all service lines in a claim.
        
        Args:
            claim: Claim model
            filename: Source filename
        
        Returns:
            List of EligibilityResult objects (one per CAS adjustment, or one per service line if no CAS adjustments)
        """
        results = []
        
        for idx, service_line in enumerate(claim.service_lines):
            line_results = self.evaluate_service_line(
                service_line=service_line,
                claim=claim,
                filename=filename,
                svc_index=idx + 1
            )
            results.extend(line_results)
        
        return results
    
    def evaluate_service_line(
        self,
        service_line: ServiceLine,
        claim: Claim,
        filename: str,
        svc_index: int
    ) -> List[EligibilityResult]:
        """
        Evaluate eligibility for a single service line.
        Creates one result per CAS adjustment to show all amounts.
        
        Args:
            service_line: ServiceLine model
            claim: Parent Claim model
            filename: Source filename
            svc_index: Service line index (1-based)
        
        Returns:
            List of EligibilityResult objects (one per CAS adjustment, or one if no CAS adjustments)
        """
        results = []
        errors_warnings = []
        
        # Check CPT code eligibility
        cpt_eligible = False
        if service_line.cpt:
            cpt_eligible = self._check_cpt(service_line.cpt.code)
        
        # Check all CAS adjustments for eligibility
        cas_eligibility = {}
        for cas in service_line.cas_adjustments:
            cas_key = (cas.group_code, cas.reason_code)
            cas_eligibility[cas_key] = self._check_cas(cas.group_code, cas.reason_code)
        
        # Check Remark codes eligibility
        rarc_eligibility = {}
        for remark in service_line.remark_codes:
            rarc_eligibility[remark.code] = self._check_rarc(remark.code)
        
        # Compute timeline dates (same for all results from this service line)
        payment_date = claim.payment_date
        open_neg_end = None
        idr_window_end = None
        
        if payment_date:
            try:
                open_neg_end = calculate_open_negotiation_end(payment_date)
                idr_window_end = calculate_idr_initiation_window_end(payment_date)
            except Exception as e:
                errors_warnings.append(f"Timeline calculation error: {e}")
                logger.warning(f"Timeline calculation failed: {e}")
        else:
            errors_warnings.append("Payment date missing - timeline cannot be computed")
        
        # Extract RARC list (same for all results from this service line)
        rarc_list = [r.code for r in service_line.remark_codes]
        
        # Create one result per CAS adjustment
        if service_line.cas_adjustments:
            for cas in service_line.cas_adjustments:
                # Build eligibility basis for this specific CAS
                basis_parts = []
                eligible = False
                
                # Include CPT if eligible
                if cpt_eligible and service_line.cpt:
                    eligible = True
                    basis_parts.append(f"CPT {service_line.cpt.code}")
                
                # Include this CAS if eligible
                cas_key = (cas.group_code, cas.reason_code)
                if cas_eligibility.get(cas_key, False):
                    eligible = True
                    basis_parts.append(f"CAS {cas.group_code}-{cas.reason_code}")
                
                # Include RARC codes if eligible
                for rarc_code in rarc_list:
                    if rarc_eligibility.get(rarc_code, False):
                        eligible = True
                        basis_parts.append(f"RARC {rarc_code}")
                
                eligibility_basis = "; ".join(basis_parts) if basis_parts else "No matching codes found"
                
                result = EligibilityResult(
                    file=filename,
                    claim_id=claim.claim_id,
                    patient_id=claim.patient_id,
                    svc_index=svc_index,
                    cpt=service_line.cpt.code if service_line.cpt else None,
                    modifiers=service_line.cpt.modifiers if service_line.cpt else [],
                    cas_group=cas.group_code,
                    cas_reason=cas.reason_code,
                    cas_amount=cas.amount,
                    rarc_list=rarc_list,
                    eligible_flag=eligible,
                    eligibility_basis=eligibility_basis,
                    payment_date=payment_date,
                    check_eft=claim.check_eft_number,
                    open_negotiation_end=open_neg_end,
                    idr_initiation_window_end=idr_window_end,
                    errors_warnings=errors_warnings.copy()
                )
                results.append(result)
        else:
            # No CAS adjustments - create one result for the service line
            basis_parts = []
            eligible = False
            
            # Include CPT if eligible
            if cpt_eligible and service_line.cpt:
                eligible = True
                basis_parts.append(f"CPT {service_line.cpt.code}")
            
            # Include RARC codes if eligible
            for rarc_code in rarc_list:
                if rarc_eligibility.get(rarc_code, False):
                    eligible = True
                    basis_parts.append(f"RARC {rarc_code}")
            
            eligibility_basis = "; ".join(basis_parts) if basis_parts else "No matching codes found"
            
            result = EligibilityResult(
                file=filename,
                claim_id=claim.claim_id,
                patient_id=claim.patient_id,
                svc_index=svc_index,
                cpt=service_line.cpt.code if service_line.cpt else None,
                modifiers=service_line.cpt.modifiers if service_line.cpt else [],
                cas_group=None,
                cas_reason=None,
                cas_amount=None,
                rarc_list=rarc_list,
                eligible_flag=eligible,
                eligibility_basis=eligibility_basis,
                payment_date=payment_date,
                check_eft=claim.check_eft_number,
                open_negotiation_end=open_neg_end,
                idr_initiation_window_end=idr_window_end,
                errors_warnings=errors_warnings
            )
            results.append(result)
        
        return results
    
    def _check_cpt(self, cpt_code: str) -> bool:
        """Check if CPT code is eligible."""
        try:
            db_code = self.session.query(DBCPTCode).filter_by(
                code=cpt_code,
                active=True
            ).first()
            return db_code is not None
        except Exception as e:
            logger.error(f"Error checking CPT code {cpt_code}: {e}")
            return False
    
    def _check_cas(self, group_code: str, reason_code: str) -> bool:
        """Check if CAS code is eligible."""
        try:
            # Only check certain group codes (CO, PR, PI, OA are common for IDR)
            eligible_groups = {"CO", "PR", "PI", "OA"}
            if group_code.upper() not in eligible_groups:
                return False
            
            db_code = self.session.query(CASCode).filter_by(
                group_code=group_code.upper(),
                reason_code=reason_code,
                active=True
            ).first()
            return db_code is not None
        except Exception as e:
            logger.error(f"Error checking CAS code {group_code}-{reason_code}: {e}")
            return False
    
    def _check_rarc(self, rarc_code: str) -> bool:
        """Check if RARC code is eligible."""
        try:
            db_code = self.session.query(DBRemarkCode).filter_by(
                rarc=rarc_code.upper(),
                active=True
            ).first()
            return db_code is not None
        except Exception as e:
            logger.error(f"Error checking RARC code {rarc_code}: {e}")
            return False

