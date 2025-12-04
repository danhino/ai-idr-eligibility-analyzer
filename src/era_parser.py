"""
ERA parser for extracting CLP, SVC, CAS, LQ segments and building structured models.
"""
import re
from decimal import Decimal
from typing import List, Optional, Dict
from datetime import date

from src.models import Claim, ServiceLine, CPTCode, CASAdjustment, RemarkCode, ERAFile
from src.era_tokenizer import ERATokenizer, Delimiters
from src.normalize import normalize_cpt, parse_amount
from src.utils.time import parse_date as parse_date_util
from src.utils.logging import logger


class ERAParser:
    """Parser for ANSI 835 ERA files."""
    
    def __init__(self, delimiters: Optional[Delimiters] = None):
        self.tokenizer = ERATokenizer(delimiters)
        self.current_claim: Optional[Claim] = None
        self.current_service_line: Optional[ServiceLine] = None
        self.claims: List[Claim] = []
        self.file_metadata: Dict = {}
    
    def parse_file(self, text: str, filename: str, file_type: str = "835") -> ERAFile:
        """
        Parse ERA file text into structured ERAFile model.
        
        Args:
            text: Raw file text
            filename: Source filename
            file_type: "835" or "pdf"
        
        Returns:
            ERAFile model
        """
        self.claims = []
        self.file_metadata = {"filename": filename, "file_type": file_type}
        
        # Detect delimiters if not set
        if file_type == "835":
            self.tokenizer.delimiters = ERATokenizer.detect_delimiters(text)
            segments = self.tokenizer.tokenize_segments(text)
            
            for segment in segments:
                self._parse_segment(segment)
        else:
            # PDF mode: use heuristic tokenization
            pseudo_segments = self.tokenizer.tokenize_pdf_text(text)
            for seg_dict in pseudo_segments:
                self._parse_pdf_segment(seg_dict)
        
        # Finalize last claim if exists
        self._finalize_current_claim()
        
        return ERAFile(
            filename=filename,
            file_type=file_type,
            payer_name=self.file_metadata.get("payer_name"),
            payer_id=self.file_metadata.get("payer_id"),
            check_eft_number=self.file_metadata.get("check_eft_number"),
            payment_date=self.file_metadata.get("payment_date"),
            claims=self.claims
        )
    
    def _parse_segment(self, segment: str):
        """Parse a single EDI segment."""
        seg_id, elements = self.tokenizer.parse_segment(segment)
        
        if seg_id == "CLP":
            self._parse_clp(elements)
        elif seg_id == "LX":
            self._parse_lx(elements)
        elif seg_id == "SVC":
            self._parse_svc(elements)
        elif seg_id == "CAS":
            self._parse_cas(elements)
        elif seg_id == "LQ":
            self._parse_lq(elements)
        elif seg_id == "DTM":
            self._parse_dtm(elements)
        elif seg_id == "NM1":
            self._parse_nm1(elements)
        elif seg_id == "AMT":
            self._parse_amt(elements)
        elif seg_id in ["ISA", "GS", "ST", "SE", "GE", "IEA"]:
            # Header/trailer segments - extract metadata if needed
            pass
    
    def _parse_pdf_segment(self, seg_dict: dict):
        """Parse a pseudo-segment from PDF text."""
        seg_id = seg_dict.get("segment_id", "UNK")
        elements = seg_dict.get("elements", [])
        
        # Combine elements into text for pattern matching
        text = " ".join(elements)
        
        # More aggressive parsing - check for codes in any line
        # First check for claim-level info
        if seg_id == "CLP" or "claim" in text.lower() or "icn" in text.lower():
            self._parse_clp_from_text(text)
        
        # Check for service line info - look for CPT codes (5 digits) or PROC column
        if seg_id == "SVC" or any(kw in text.lower() for kw in ["cpt", "procedure", "service", "proc"]) or re.search(r'\b\d{5}\b', text):
            self._parse_svc_from_text(text)
        
        # Check for CAS codes - look for patterns like "CO-45", "OA-209", "PR-1", etc.
        cas_pattern = r'\b(CO|PR|PI|OA|OI|CR)[-\s]*(\d{1,3})\b'
        if seg_id == "CAS" or any(kw in text.lower() for kw in ["adjustment", "denial", "reduction", "grp/rc"]) or re.search(cas_pattern, text, re.IGNORECASE):
            self._parse_cas_from_text(text)
        
        # Check for remark codes - REM: can appear on same line or separate line after service line
        # Always check for REM: pattern regardless of segment ID
        if "rem:" in text.lower() or re.search(r'REM:\s*[A-Z]{1,2}\d{1,4}', text, re.IGNORECASE):
            self._parse_lq_from_text(text)
        # Also check if this is explicitly a remark segment
        elif seg_id == "LQ" or any(kw in text.lower() for kw in ["remark", "rarc", "note"]):
            self._parse_lq_from_text(text)
        
        # Check for dates
        if seg_id == "DTM" or "date" in text.lower() or re.search(r'\d{4}-\d{2}-\d{2}', text):
            self._parse_dtm_from_text(text)
    
    def _parse_clp(self, elements: List[str]):
        """Parse CLP (Claim Payment Information) segment."""
        if len(elements) < 4:
            return
        
        self._finalize_current_claim()
        
        claim_id = elements[0] if elements[0] else "UNKNOWN"
        claim_status = elements[1] if len(elements) > 1 else "1"
        total_charge = parse_amount(elements[2]) if len(elements) > 2 else Decimal("0")
        total_paid = parse_amount(elements[3]) if len(elements) > 3 else Decimal("0")
        patient_responsibility = parse_amount(elements[4]) if len(elements) > 4 else Decimal("0")
        claim_filing_indicator = elements[5] if len(elements) > 5 else None
        payer_claim_control = elements[6] if len(elements) > 6 else None
        
        self.current_claim = Claim(
            claim_id=claim_id,
            claim_status=claim_status,
            total_charge=total_charge,
            total_paid=total_paid,
            patient_responsibility=patient_responsibility,
            claim_filing_indicator=claim_filing_indicator,
            payer_claim_control_number=payer_claim_control,
            raw_segments={"CLP": "*".join(elements)}
        )
    
    def _parse_clp_from_text(self, text: str):
        """Parse CLP information from PDF text using patterns."""
        # Look for claim ID patterns (ICN)
        claim_id_match = re.search(r'(?:icn|claim\s*(?:id|#|number)?)[:\s]*([A-Z0-9-]{10,})', text, re.IGNORECASE)
        if not claim_id_match:
            claim_id_match = re.search(r'(?:claim\s*(?:id|#|number)?[:\s]*)?([A-Z0-9-]{5,})', text, re.IGNORECASE)
        claim_id = claim_id_match.group(1) if claim_id_match else "UNKNOWN"
        
        # Extract ACNT (Patient Account Number) - pattern: ACNT followed by alphanumeric
        # Examples: "ACNT FFATP59269239-3", "ACNT FFATF70000476-5"
        acnt_pattern = r'\bACNT\s+([A-Z0-9-]+)\b'
        acnt_match = re.search(acnt_pattern, text, re.IGNORECASE)
        acnt_number = acnt_match.group(1) if acnt_match else None
        
        # Also look for ACNT in other formats (without explicit ACNT label)
        if not acnt_number:
            # Pattern: Look for account-like patterns near patient info
            acnt_pattern2 = r'(?:account|acnt)[:\s]*([A-Z0-9-]{8,})'
            acnt_match2 = re.search(acnt_pattern2, text, re.IGNORECASE)
            acnt_number = acnt_match2.group(1) if acnt_match2 else None
        
        # Look for amounts
        amount_pattern = r'\$?([\d,]+\.?\d{0,2})'
        amounts = [parse_amount(m.group(1)) for m in re.finditer(amount_pattern, text)]
        
        total_charge = amounts[0] if amounts else Decimal("0")
        total_paid = amounts[1] if len(amounts) > 1 else Decimal("0")
        patient_resp = amounts[2] if len(amounts) > 2 else Decimal("0")
        
        self._finalize_current_claim()
        self.current_claim = Claim(
            claim_id=claim_id,
            patient_id=acnt_number,  # Store ACNT as patient_id
            claim_status="1",
            total_charge=total_charge,
            total_paid=total_paid,
            patient_responsibility=patient_resp
        )
    
    def _parse_lx(self, elements: List[str]):
        """Parse LX (Service Line Number) segment."""
        if self.current_claim and elements:
            line_number = int(elements[0]) if elements[0].isdigit() else len(self.current_claim.service_lines) + 1
            self.current_service_line = ServiceLine(line_number=line_number)
    
    def _parse_svc(self, elements: List[str]):
        """Parse SVC (Service Line) segment."""
        if not self.current_claim:
            return
        
        if not self.current_service_line:
            line_num = len(self.current_claim.service_lines) + 1
            self.current_service_line = ServiceLine(line_number=line_num)
        
        # SVC01: Composite of procedure code
        if elements:
            proc_composite = elements[0]
            subelements = self.tokenizer.parse_element(proc_composite)
            
            # Format: HC:99283:25 or similar
            if len(subelements) >= 2:
                qualifier = subelements[0]  # HC, etc.
                cpt_code = subelements[1]
                modifiers = subelements[2:] if len(subelements) > 2 else []
            else:
                # Try to extract CPT from text
                cpt_match = re.search(r'\b(\d{5})\b', proc_composite)
                if cpt_match:
                    cpt_code = cpt_match.group(1)
                    modifiers = []
                else:
                    cpt_code = None
                    modifiers = []
            
            if cpt_code:
                normalized = normalize_cpt(cpt_code, modifiers)
                self.current_service_line.cpt = CPTCode(
                    code=normalized["code"],
                    modifiers=normalized["modifiers"]
                )
        
        # SVC02: Line charge amount
        if len(elements) > 1:
            self.current_service_line.charge_amount = parse_amount(elements[1])
        
        # SVC03: Line paid amount
        if len(elements) > 2:
            self.current_service_line.paid_amount = parse_amount(elements[2])
        
        self.current_service_line.raw_segment = "*".join(elements)
    
    def _parse_svc_from_text(self, text: str):
        """Parse SVC information from PDF text."""
        if not self.current_claim:
            return
        
        # Extract CPT code - look for 5-digit codes (CPT codes)
        cpt_pattern = r'\b(\d{5})\b'
        cpt_matches = list(re.finditer(cpt_pattern, text))
        
        if cpt_matches:
            # Use the first CPT code found
            cpt_code = cpt_matches[0].group(1)
            
            # Look for modifiers - could be in MODS column or after CPT code
            # Pattern: CPT code followed by optional modifier (2 chars)
            modifier_pattern = r'\b\d{5}\s+([A-Z0-9]{2})\b'
            modifier_match = re.search(modifier_pattern, text)
            modifiers = []
            if modifier_match:
                modifiers.append(modifier_match.group(1))
            else:
                # Also check for "MOD" or "MODS" column
                mod_col_pattern = r'(?:mod|mods)[:\s]*([A-Z0-9]{2})'
                mod_col_match = re.search(mod_col_pattern, text, re.IGNORECASE)
                if mod_col_match:
                    modifiers.append(mod_col_match.group(1))
            
            # Create or update service line
            if not self.current_service_line:
                line_num = len(self.current_claim.service_lines) + 1
                self.current_service_line = ServiceLine(line_number=line_num)
            
            normalized = normalize_cpt(cpt_code, modifiers)
            self.current_service_line.cpt = CPTCode(
                code=normalized["code"],
                modifiers=normalized["modifiers"]
            )
            
            # Extract amounts - look for patterns like "8443.37" or "$8443.37"
            amount_pattern = r'\$?([\d,]+\.?\d{2})'
            amounts = [parse_amount(m.group(1)) for m in re.finditer(amount_pattern, text)]
            if amounts:
                # Typically: billed, allowed, deduct, coins, prov paid
                self.current_service_line.charge_amount = amounts[0]  # Billed
                if len(amounts) > 1:
                    self.current_service_line.paid_amount = amounts[-1]  # Last amount is often paid
    
    def _parse_cas(self, elements: List[str]):
        """Parse CAS (Claim Adjustment) segment."""
        if not self.current_claim:
            return
        
        # CAS format: CAS*{GROUP}*{REASON}*{AMOUNT}*{QUANTITY} (repeating triplets)
        group_code = elements[0] if elements else None
        
        i = 1
        while i < len(elements):
            if i + 1 < len(elements):
                reason_code = elements[i]
                amount = parse_amount(elements[i + 1]) if elements[i + 1] else Decimal("0")
                quantity = parse_amount(elements[i + 2]) if i + 2 < len(elements) and elements[i + 2] else None
                
                adjustment = CASAdjustment(
                    group_code=group_code or "",
                    reason_code=reason_code,
                    amount=amount,
                    quantity=quantity
                )
                
                if self.current_service_line:
                    self.current_service_line.cas_adjustments.append(adjustment)
                else:
                    # Claim-level adjustment
                    if not hasattr(self.current_claim, 'claim_adjustments'):
                        self.current_claim.claim_adjustments = []
                    self.current_claim.claim_adjustments.append(adjustment)
                
                i += 3
            else:
                break
    
    def _parse_cas_from_text(self, text: str):
        """Parse CAS information from PDF text."""
        if not self.current_claim:
            return
        
        # Look for CAS patterns: "CO-45", "OA-209", "PR-1", "GRP/RC-AMT" format, etc.
        # Pattern 1: Group-Reason format (e.g., "OA-209", "CO-45")
        cas_pattern1 = r'\b(CO|PR|PI|OA|OI|CR)[-\s]+(\d{1,3})\b'
        cas_matches1 = list(re.finditer(cas_pattern1, text, re.IGNORECASE))
        
        # Pattern 2: Look for "GRP/RC" column format
        # Pattern 3: Separate group and reason codes nearby
        group_pattern = r'\b(CO|PR|PI|OA|OI|CR)\b'
        reason_pattern = r'\b(\d{1,3})\b'
        
        # First try pattern 1 (combined format)
        for match in cas_matches1:
            group_code = match.group(1).upper()
            reason_code = match.group(2)
            
            # Try to find associated amount nearby
            # Look for amount after the CAS code
            text_after = text[match.end():match.end()+50]  # Check 50 chars after
            amount_pattern = r'\$?([\d,]+\.?\d{2})'
            amount_match = re.search(amount_pattern, text_after)
            amount = parse_amount(amount_match.group(1)) if amount_match else Decimal("0")
            
            adjustment = CASAdjustment(
                group_code=group_code,
                reason_code=reason_code,
                amount=amount
            )
            
            # Add to service line if exists, otherwise create one
            if not self.current_service_line:
                line_num = len(self.current_claim.service_lines) + 1
                self.current_service_line = ServiceLine(line_number=line_num)
            
            self.current_service_line.cas_adjustments.append(adjustment)
        
        # If no combined matches, try separate group and reason codes
        if not cas_matches1:
            group_match = re.search(group_pattern, text, re.IGNORECASE)
            if group_match:
                group_code = group_match.group(1).upper()
                # Look for reason code nearby (within 20 chars)
                text_around = text[max(0, group_match.start()-10):group_match.end()+20]
                reason_match = re.search(reason_pattern, text_around)
                if reason_match:
                    reason_code = reason_match.group(1)
                    
                    # Find amount
                    amount_pattern = r'\$?([\d,]+\.?\d{2})'
                    amount_match = re.search(amount_pattern, text)
                    amount = parse_amount(amount_match.group(1)) if amount_match else Decimal("0")
                    
                    adjustment = CASAdjustment(
                        group_code=group_code,
                        reason_code=reason_code,
                        amount=amount
                    )
                    
                    if not self.current_service_line:
                        line_num = len(self.current_claim.service_lines) + 1
                        self.current_service_line = ServiceLine(line_number=line_num)
                    
                    self.current_service_line.cas_adjustments.append(adjustment)
    
    def _parse_lq(self, elements: List[str]):
        """Parse LQ (Remark Code) segment."""
        if not self.current_claim:
            return
        
        # LQ format: LQ*{QUALIFIER}*{RARC}
        qualifier = elements[0] if elements else None
        rarc = elements[1] if len(elements) > 1 else None
        
        if rarc:
            remark = RemarkCode(code=rarc, qualifier=qualifier)
            if self.current_service_line:
                self.current_service_line.remark_codes.append(remark)
    
    def _parse_lq_from_text(self, text: str):
        """Parse LQ information from PDF text."""
        if not self.current_claim:
            return
        
        # First, look for explicit "REM:" pattern (e.g., "REM: N130")
        rem_pattern = r'REM:\s*([A-Z]{1,2}\d{1,4})'
        rem_matches = list(re.finditer(rem_pattern, text, re.IGNORECASE))
        
        found_rem_codes = False
        for match in rem_matches:
            rarc_code = match.group(1).upper()
            remark = RemarkCode(code=rarc_code)
            # Ensure we have a service line - if REM: is on a separate line, 
            # associate it with the most recent service line
            if not self.current_service_line:
                # If no current service line, create one or use the last one
                if self.current_claim.service_lines:
                    # Use the last service line
                    self.current_service_line = self.current_claim.service_lines[-1]
                else:
                    # Create a new service line
                    line_num = len(self.current_claim.service_lines) + 1
                    self.current_service_line = ServiceLine(line_number=line_num)
            self.current_service_line.remark_codes.append(remark)
            found_rem_codes = True
        
        # Also look for RARC patterns without REM: prefix (1-2 letters + 1-4 digits, e.g., MA130, N130)
        # But only if we haven't already found codes via REM: pattern
        if not found_rem_codes:
            rarc_pattern = r'\b([A-Z]{1,2}\d{1,4})\b'
            rarc_matches = re.finditer(rarc_pattern, text, re.IGNORECASE)
            
            for match in rarc_matches:
                rarc_code = match.group(1).upper()
                # Skip if it looks like a date or other number (e.g., "2025", "1011")
                if len(rarc_code) >= 4 and rarc_code[1:].isdigit():
                    try:
                        if int(rarc_code[1:]) > 1900:  # Likely a year
                            continue
                    except ValueError:
                        pass
                # Skip common non-RARC patterns
                if rarc_code in ["ICN", "NPI", "EFT", "ACNT", "ASG", "MOA"]:
                    continue
                remark = RemarkCode(code=rarc_code)
                # Ensure we have a service line
                if not self.current_service_line:
                    if self.current_claim.service_lines:
                        self.current_service_line = self.current_claim.service_lines[-1]
                    else:
                        line_num = len(self.current_claim.service_lines) + 1
                        self.current_service_line = ServiceLine(line_number=line_num)
                self.current_service_line.remark_codes.append(remark)
    
    def _parse_dtm(self, elements: List[str]):
        """Parse DTM (Date/Time) segment."""
        if len(elements) < 2:
            return
        
        qualifier = elements[0]
        date_str = elements[1]
        
        parsed_date = parse_date_util(date_str)
        
        if parsed_date:
            if qualifier == "405":  # Payment date
                self.file_metadata["payment_date"] = parsed_date
                if self.current_claim:
                    self.current_claim.payment_date = parsed_date
    
    def _parse_dtm_from_text(self, text: str):
        """Parse date information from PDF text."""
        # Look for date patterns
        date_patterns = [
            r'\b(\d{8})\b',  # YYYYMMDD
            r'\b(\d{1,2})/(\d{1,2})/(\d{4})\b',  # MM/DD/YYYY
            r'\b(\d{4})-(\d{1,2})-(\d{1,2})\b',  # YYYY-MM-DD
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                if len(match.groups()) == 1:
                    date_str = match.group(1)
                elif len(match.groups()) == 3:
                    # Reconstruct date string
                    parts = match.groups()
                    if len(parts[2]) == 4:  # YYYY format
                        date_str = f"{parts[2]}{parts[0].zfill(2)}{parts[1].zfill(2)}"
                    else:
                        date_str = f"{parts[0]}{parts[1].zfill(2)}{parts[2].zfill(2)}"
                else:
                    continue
                
                parsed_date = parse_date_util(date_str)
                if parsed_date:
                    if "payment" in text.lower() or "paid" in text.lower():
                        self.file_metadata["payment_date"] = parsed_date
                        if self.current_claim:
                            self.current_claim.payment_date = parsed_date
                    break
    
    def _parse_nm1(self, elements: List[str]):
        """Parse NM1 (Name) segment."""
        if len(elements) < 2:
            return
        
        entity_type = elements[0]
        name_type = elements[1]
        
        if entity_type == "QC" and name_type == "1":  # Patient
            last_name = elements[2] if len(elements) > 2 else None
            first_name = elements[3] if len(elements) > 3 else None
            if last_name and first_name:
                patient_name = f"{first_name} {last_name}"
                if self.current_claim:
                    self.current_claim.patient_name = patient_name
    
    def _parse_amt(self, elements: List[str]):
        """Parse AMT (Amount) segment."""
        if len(elements) < 2:
            return
        
        qualifier = elements[0]
        amount = parse_amount(elements[1]) if len(elements) > 1 else Decimal("0")
        
        # Store in metadata if needed
        if qualifier == "T" and self.current_claim:  # Total claim charge
            pass  # Already captured in CLP
    
    def _finalize_current_claim(self):
        """Finalize and add current claim to list."""
        if self.current_service_line:
            if self.current_claim:
                self.current_claim.service_lines.append(self.current_service_line)
            self.current_service_line = None
        
        if self.current_claim:
            self.claims.append(self.current_claim)
            self.current_claim = None

