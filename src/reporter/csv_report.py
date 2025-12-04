"""
CSV report generation.
"""
import pandas as pd
from typing import List, Optional
from pathlib import Path

from src.models import EligibilityResult
from src.utils.logging import logger


def generate_csv_report(results: List[EligibilityResult], output_path: Optional[Path] = None) -> pd.DataFrame:
    """
    Generate CSV report from eligibility results.
    
    Args:
        results: List of EligibilityResult objects
        output_path: Optional path to save CSV file
    
    Returns:
        DataFrame with results
    """
    rows = []
    
    for result in results:
        row = {
            "file": result.file,
            "check_eft": result.check_eft or "",
            "payment_date": result.payment_date.strftime("%Y-%m-%d") if result.payment_date else "",
            "claim_id": result.claim_id,
            "patient_id": result.patient_id or "",
            "svc_index": result.svc_index,
            "cpt": result.cpt or "",
            "modifiers": ",".join(result.modifiers) if result.modifiers else "",
            "cas_group": result.cas_group or "",
            "cas_reason": result.cas_reason or "",
            "cas_amount": str(result.cas_amount) if result.cas_amount else "",
            "rarc_list": ",".join(result.rarc_list) if result.rarc_list else "",
            "eligible_flag": "Yes" if result.eligible_flag else "No",
            "eligibility_basis": result.eligibility_basis,
            "open_negotiation_end": result.open_negotiation_end.strftime("%Y-%m-%d") if result.open_negotiation_end else "",
            "idr_initiation_window_end": result.idr_initiation_window_end.strftime("%Y-%m-%d") if result.idr_initiation_window_end else "",
            "errors_warnings": "; ".join(result.errors_warnings) if result.errors_warnings else ""
        }
        rows.append(row)
    
    df = pd.DataFrame(rows)
    
    if output_path:
        try:
            df.to_csv(output_path, index=False)
            logger.info(f"CSV report saved to {output_path}")
        except Exception as e:
            logger.error(f"Failed to save CSV report: {e}")
    
    return df

